#!/usr/bin/env python3
"""Replay a RoboDK intermediate program file against a post processor.

RoboDK writes a `PostProg<Name>.py` next to every generated program. It is ordinary
runnable Python that calls the post exactly the way RoboDK does -- same call order, same
argument shapes, same Nones. Replaying it is the most faithful test available offline.

This script copies the post to a temp directory, rewrites the intermediate file's sys.path
line, its `from <Post> import *`, and its final `ProgSave(...)` call so that output lands in
a directory you choose without opening a save dialog or an editor, runs it, prints the
generated program, and optionally unified-diffs it against a known-good reference.

Use it as a regression test around every edit: run it before changing anything (a clean
diff confirms the harness reproduces reality), make the change, run it again, and check that
every line in the diff is a change you intended.

Requires the `robodk` package:  pip install robodk

Examples
--------
  python replay_intermediate.py PostProg2.py --post Siasun.py --out ./out
  python replay_intermediate.py PostProg2.py --post Siasun.py --out ./out --expect Prog2.spf
"""

import argparse
import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile

# `from X import *` for the post module. robodk's own imports are left alone.
IMPORT_RE = re.compile(r'^from\s+([A-Za-z_]\w*)\s+import\s+\*\s*$', re.MULTILINE)
# Matches the whole line, including RoboDK's trailing "# temporarily add path" comment.
SYSPATH_RE = re.compile(r'^sys\.path\.append\(.*$', re.MULTILINE)
# ProgSave(folder, progname, ask_user, show_result) -- folder and progname are r"""..."""
PROGSAVE_RE = re.compile(
    r'^(?P<indent>\s*)(?P<obj>\w+)\.ProgSave\(\s*r?"""(?P<folder>.*?)"""\s*,'
    r'\s*r?"""(?P<name>.*?)"""(?P<rest>.*?)\)\s*$',
    re.MULTILINE | re.DOTALL)


def sanitize_module_name(stem):
    """Make a post file name importable, preserving it where possible."""
    name = re.sub(r'\W', '_', stem)
    if not name or name[0].isdigit():
        name = 'post_' + name
    return name


def rewrite(source, module_name, post_dir, out_dir):
    """Point the intermediate file at our post copy and our output directory."""
    problems = []

    source, n = SYSPATH_RE.subn(
        'sys.path.insert(0, os.path.abspath(r"""%s"""))' % post_dir, source, count=1)
    if n == 0:
        # Older intermediates may not have the line; add one after the imports.
        source = 'import os, sys\nsys.path.insert(0, os.path.abspath(r"""%s"""))\n' % post_dir + source

    def swap_import(match):
        if match.group(1).startswith('robodk'):
            return match.group(0)
        return 'from %s import *' % module_name

    source, n = IMPORT_RE.subn(swap_import, source)
    if n == 0:
        problems.append('no "from <Post> import *" line found -- the post may not be loaded')

    match = PROGSAVE_RE.search(source)
    if not match:
        problems.append('no ProgSave(...) call found -- nothing will be written')
        prog_name = None
    else:
        prog_name = match.group('name')
        replacement = '%s%s.ProgSave(r"""%s""", r"""%s""", False, False)' % (
            match.group('indent'), match.group('obj'), out_dir, prog_name)
        source = source[:match.start()] + replacement + source[match.end():]

    return source, prog_name, problems


def snapshot(directory):
    """name -> (mtime, size) for every file, so overwrites are detected as well as
    creations. Regenerating in place over an existing reference is a normal thing to do."""
    snap = {}
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            stat = os.stat(path)
            snap[name] = (stat.st_mtime_ns, stat.st_size)
    return snap


def written_files(out_dir, before, after):
    """Files the run created or modified."""
    return sorted(name for name, meta in after.items() if before.get(name) != meta)


def pick_generated(out_dir, expect_path, prog_name, candidates=None):
    """Choose which generated file to diff against the reference.

    `candidates` restricts the search to files this run actually wrote, which matters when
    the output directory also holds the post, the intermediate file and the reference.
    """
    names = candidates if candidates else sorted(os.listdir(out_dir))
    files = [os.path.join(out_dir, n) for n in names
             if os.path.isfile(os.path.join(out_dir, n))]
    if not files:
        return None, files
    by_name = {os.path.basename(f).lower(): f for f in files}
    target = by_name.get(os.path.basename(expect_path).lower())
    if target is None and prog_name:
        for f in files:
            if os.path.splitext(os.path.basename(f))[0].lower() == prog_name.lower():
                target = f
                break
    if target is None and len(files) == 1:
        target = files[0]
    return target, files


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('intermediate', help='RoboDK intermediate file, e.g. PostProg2.py')
    parser.add_argument('--post', required=True, help='post processor .py to test')
    parser.add_argument('--out', default='./replay_out', help='output directory for generated programs')
    parser.add_argument('--expect', help='known-good controller program to diff against')
    parser.add_argument('--quiet', action='store_true', help='do not print the generated program')
    parser.add_argument('--keep', action='store_true', help='keep the temp directory and print its path')
    args = parser.parse_args()

    intermediate = os.path.abspath(args.intermediate)
    post = os.path.abspath(args.post)
    out_dir = os.path.abspath(args.out)
    # Forward slashes throughout: these paths get embedded in raw triple-quoted string
    # literals, which cannot end in a backslash.
    out_dir_literal = out_dir.replace('\\', '/')

    for path, label in ((intermediate, 'intermediate file'), (post, 'post processor')):
        if not os.path.isfile(path):
            print('ERROR: %s not found: %s' % (label, path), file=sys.stderr)
            return 2

    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='robodk_replay_')
    try:
        module_name = sanitize_module_name(os.path.splitext(os.path.basename(post))[0])
        shutil.copyfile(post, os.path.join(tmp, module_name + '.py'))

        with open(intermediate, 'r', encoding='utf-8', errors='replace') as fid:
            source = fid.read()

        source, prog_name, problems = rewrite(
            source, module_name, tmp.replace('\\', '/'), out_dir_literal)
        for problem in problems:
            print('WARNING: %s' % problem, file=sys.stderr)

        replay_path = os.path.join(tmp, 'replay_' + os.path.basename(intermediate))
        with open(replay_path, 'w', encoding='utf-8') as fid:
            fid.write(source)

        before = snapshot(out_dir)
        result = subprocess.run([sys.executable, replay_path], cwd=tmp,
                                capture_output=True, text=True)

        if result.stdout.strip():
            print(result.stdout.rstrip())
        if result.returncode != 0:
            print('\nERROR: generation failed (exit %d)' % result.returncode, file=sys.stderr)
            print(result.stderr.rstrip(), file=sys.stderr)
            if 'No module named' in result.stderr and 'robodk' in result.stderr:
                print('\nThe robodk package is required:  pip install robodk', file=sys.stderr)
            return result.returncode
        if result.stderr.strip():
            print(result.stderr.rstrip(), file=sys.stderr)

        written = written_files(out_dir, before, snapshot(out_dir))
        if not written:
            print('\nWARNING: no files were written or modified in %s' % out_dir,
                  file=sys.stderr)
        else:
            print('\nGenerated in %s: %s' % (out_dir, ', '.join(written)))

        target, files = pick_generated(out_dir, args.expect or '', prog_name, written)

        if not args.quiet and target:
            with open(target, 'r', encoding='utf-8', errors='replace') as fid:
                print('\n--- %s ---' % os.path.basename(target))
                print(fid.read().rstrip())

        status = 0
        if args.expect:
            expect_path = os.path.abspath(args.expect)
            if not os.path.isfile(expect_path):
                print('\nERROR: reference not found: %s' % expect_path, file=sys.stderr)
                return 2
            if target is None:
                print('\nERROR: could not decide which generated file to compare '
                      '(found: %s)' % (', '.join(os.path.basename(f) for f in files) or 'none'),
                      file=sys.stderr)
                return 2
            with open(expect_path, 'r', encoding='utf-8', errors='replace') as fid:
                expected = fid.read().splitlines()
            with open(target, 'r', encoding='utf-8', errors='replace') as fid:
                actual = fid.read().splitlines()
            diff = list(difflib.unified_diff(
                expected, actual,
                fromfile=os.path.basename(expect_path),
                tofile=os.path.basename(target), lineterm=''))
            if diff:
                print('\n--- diff vs %s ---' % os.path.basename(expect_path))
                print('\n'.join(diff))
                print('\n%d differing line(s).' % sum(
                    1 for line in diff
                    if line[:1] in '+-' and not line.startswith(('+++', '---'))))
                status = 1
            else:
                print('\nOutput matches %s exactly.' % os.path.basename(expect_path))
        return status
    finally:
        if args.keep:
            print('\nTemp directory kept: %s' % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
