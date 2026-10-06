#!/usr/bin/env python3
"""Extract searchable text from a vendor PDF manual using only the standard library.

Vendor programming manuals are the ground truth for a post processor, but reaching them is
often the hard part: the built-in PDF reader needs poppler installed, and pypdf/fitz are
usually absent from the Python that ships with RoboDK. This script needs neither. It
decompresses the content streams with zlib, harvests every ToUnicode CMap in the file into
one code->character map, and decodes the text-showing operators.

Merging all fonts' CMaps is not strictly correct -- codes can collide between fonts, so an
occasional glyph comes out wrong (a Chinese manual rendered 与 as 且 in testing). That is
fine for the job at hand, which is finding *which page* documents an instruction so you can
read it properly. Do not quote decoded prose back to the user as if it were verbatim.

Usage
-----
  # dump everything, one line per content stream, ready for grep
  python pdf_text.py manual.pdf > manual.txt

  # search directly, with surrounding context
  python pdf_text.py manual.pdf --find J_VEL "AO[" 圆弧

  # widen the context window around each hit
  python pdf_text.py manual.pdf --find CR --context 400

Output lines are prefixed [S<n>] with the stream index, which usually tracks page order in
manuals produced by Word. Manuals normally print their own page number in the running
header, so a hit's real page number is generally visible in the decoded text itself.
"""

import argparse
import io
import re
import sys
import zlib

BFCHAR = re.compile(rb'beginbfchar(.*?)endbfchar', re.S)
BFRANGE = re.compile(rb'beginbfrange(.*?)endbfrange', re.S)
PAIR = re.compile(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>')
TRIPLE = re.compile(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>')
TOKEN = re.compile(rb'<([0-9A-Fa-f\s]+)>\s*Tj'
                   rb'|\(((?:[^()\\]|\\.)*)\)\s*Tj'
                   rb'|\[((?:[^\[\]\\]|\\.)*)\]\s*TJ'
                   rb'|(TD|Td|T\*|ET)')
PIECE = re.compile(rb'<([0-9A-Fa-f\s]+)>|\(((?:[^()\\]|\\.)*)\)')


def build_cmap(blob, cmap):
    """Add every bfchar/bfrange mapping found in blob to cmap."""
    for m in BFCHAR.finditer(blob):
        for src, dst in PAIR.findall(m.group(1)):
            try:
                cmap[int(src, 16)] = chr(int(dst[:4], 16))
            except ValueError:
                pass
    for m in BFRANGE.finditer(blob):
        for lo, hi, dst in TRIPLE.findall(m.group(1)):
            try:
                lo_i, hi_i, dst_i = int(lo, 16), int(hi, 16), int(dst[:4], 16)
            except ValueError:
                continue
            if hi_i < lo_i or hi_i - lo_i > 65535:
                continue
            for k in range(lo_i, hi_i + 1):
                cmap[k] = chr(dst_i + k - lo_i)


def extract_streams(data, cmap):
    """Decompress every FlateDecode stream, collecting CMaps as we go."""
    streams = []
    for m in re.finditer(rb'stream\r?\n', data):
        start = m.end()
        end = data.find(b'endstream', start)
        if end < 0:
            continue
        try:
            out = zlib.decompressobj().decompress(data[start:end])
        except zlib.error:
            continue
        streams.append(out)
        if b'beginbfchar' in out or b'beginbfrange' in out:
            build_cmap(out, cmap)
    build_cmap(data, cmap)          # uncompressed CMaps
    return streams


def decode_hex(h, cmap):
    h = re.sub(rb'\s', b'', h)
    if len(h) % 4:
        return ''
    return ''.join(cmap.get(int(h[i:i + 4], 16), '') for i in range(0, len(h), 4))


def decode_literal(s, cmap):
    s = re.sub(rb'\\([()\\])', rb'\1', s)
    return ''.join(cmap.get(c, chr(c)) for c in s)


def stream_text(blob, cmap):
    parts = []
    for m in TOKEN.finditer(blob):
        if m.group(1) is not None:
            parts.append(decode_hex(m.group(1), cmap))
        elif m.group(2) is not None:
            parts.append(decode_literal(m.group(2), cmap))
        elif m.group(3) is not None:
            for sub in PIECE.finditer(m.group(3)):
                if sub.group(1) is not None:
                    parts.append(decode_hex(sub.group(1), cmap))
                else:
                    parts.append(decode_literal(sub.group(2), cmap))
    # Each operator is one glyph in many manuals, so join without separators.
    return ''.join(parts)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('pdf')
    parser.add_argument('--find', nargs='+', metavar='TERM',
                        help='print only regions containing these terms')
    parser.add_argument('--context', type=int, default=220,
                        help='characters of context around each hit (default 220)')
    parser.add_argument('--wrap', type=int, default=150,
                        help='wrap long lines at this width, 0 to disable (default 150)')
    args = parser.parse_args()

    # Manual text is rarely ASCII; force UTF-8 out regardless of console codepage.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    with open(args.pdf, 'rb') as fid:
        data = fid.read()

    cmap = {}
    streams = extract_streams(data, cmap)
    sys.stderr.write('streams=%d cmap_entries=%d\n' % (len(streams), len(cmap)))
    if not cmap:
        sys.stderr.write('WARNING: no ToUnicode CMaps found; text may be unreadable.\n')

    def wrap(text):
        if args.wrap > 0:
            return re.sub(r'(.{%d})' % args.wrap, r'\1\n', text)
        return text

    pages = [(i, stream_text(s, cmap)) for i, s in enumerate(streams)]
    pages = [(i, t) for i, t in pages if t.strip()]

    if not args.find:
        for idx, text in pages:
            print('[S%d] %s' % (idx, wrap(text)))
        return 0

    hits = 0
    for term in args.find:
        print('=' * 8 + ' %s ' % term + '=' * 8)
        for idx, text in pages:
            for m in re.finditer(re.escape(term), text):
                lo = max(0, m.start() - args.context)
                hi = min(len(text), m.end() + args.context)
                print('[S%d] ...%s...' % (idx, wrap(text[lo:hi])))
                print()
                hits += 1
        print()
    sys.stderr.write('hits=%d\n' % hits)
    return 0 if hits else 1


if __name__ == '__main__':
    sys.exit(main())
