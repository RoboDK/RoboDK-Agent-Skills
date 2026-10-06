#!/usr/bin/env python3
"""
robodk_addin.py - scaffold, validate, package, inspect and extract RoboDK Add-ins (Apps).

A RoboDK Add-in is a folder of Python action scripts plus an AppConfig.ini
manifest that tells the Add-in Manager how to expose them in the UI. This tool
handles the mechanical parts that are easy to get subtly wrong:

  new      Scaffold a complete, runnable Add-in folder.
  check    Validate an Add-in folder against the AppLoader's discovery rules.
  sync     Reconcile AppConfig.ini, manifest.xml and core_properties.xml with disk.
  package  Zip the folder into a distributable, installable .rdkp package.
  inspect  Show a .rdkp package's metadata and layout without extracting it.
  extract  Unzip a .rdkp package to a folder.

inspect/extract only handle plain-ZIP .rdkp packages -- the format every
openly-sourced and Marketplace Add-in uses. Some commercially distributed
packages are wrapped in RoboDK's own lightweight package obfuscation; this
tool detects that (a 4-byte 'RDKE' signature at the start of the file) and
refuses rather than guessing at reversing it.

Run any subcommand with -h for its options. Pure standard library, Python 3.7+.
"""

import argparse
import configparser
import datetime
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# Constants mirroring the AppLoader's behaviour (see references/appconfig.md)
# ---------------------------------------------------------------------------

#: Files matching these are never packaged and never treated as actions.
EXCLUDE_DIRS = {'__pycache__', '.git', '.svn', '.idea', '.vscode', 'env', 'venv', '.venv'}
EXCLUDE_FILE_PATTERNS = ('.pyc', '.pyo', '.rdkp', '.code-workspace', '.DS_Store')

#: Section keys the AppLoader reads for each action, with its own defaults.
ACTION_DEFAULTS = [
    ('DisplayName', ''),
    ('Description', ''),
    ('Visible', 'true'),
    ('Shortcut', ''),
    ('Checkable', 'false'),
    ('CheckableGroup', '-1'),
    ('AddToMenu', 'true'),
    ('AddToToolbar', 'true'),
    ('Priority', '50'),
    ('TypeOnContextMenu', ''),
    ('TypeOnDoubleClick', ''),
    ('DeveloperOnly', 'false'),
]

GENERAL_DEFAULTS = [
    ('MenuName', ''),
    ('MenuParent', ''),
    ('MenuPriority', '50'),
    ('MenuVisible', 'true'),
    ('ToolbarArea', '2'),
    ('ToolbarSizeRatio', '1.5'),
    ('RunCommands', ''),
    ('Version', '1.0.0'),
]

ACTION_TYPES = ('momentary', 'checkable', 'option', 'option-group', 'context', 'doubleclick')

#: A .rdkp package is an OPC (Open Packaging Convention) ZIP: the same container
#: format used by .docx/.xlsx. RoboDK's Add-in Manager finds the manifest and
#: core-properties parts by following these relationship types out of
#: _rels/.rels -- a package without that file is not recognized as installable,
#: even if it otherwise contains a manifest.xml.
CORE_PROPS_NS = {
    '': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}
MANIFEST_NS = {'': 'http://schemas.robodk.com/package/2022/manifest'}
RELS_NS = {'': 'http://schemas.openxmlformats.org/package/2006/relationships'}
CONTENT_TYPES_NS = {'': 'http://schemas.openxmlformats.org/package/2006/content-types'}

CORE_PROPS_REL = 'http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties'
MANIFEST_REL = 'http://schemas.robodk.com/package/2022/relationships/manifest'
APPCONFIG_REL = 'http://schemas.robodk.com/package/2022/relationships/appconfig'
CORE_PROPS_CONTENT_TYPE = 'application/vnd.openxmlformats-package.core-properties+xml'
RELS_CONTENT_TYPE = 'application/vnd.openxmlformats-package.relationships+xml'

EXTENSION_CONTENT_TYPES = {
    'xml': 'application/xml', 'rels': RELS_CONTENT_TYPE, 'svg': 'image/svg+xml',
    'ini': 'text/plain', 'md': 'text/markdown', 'py': 'text/x-python',
    'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'ico': 'image/x-icon', 'txt': 'text/plain', 'json': 'application/json',
}

#: 4-byte marker at the start of a package wrapped in RoboDK's proprietary
#: obfuscation layer. This tool only detects it (to refuse cleanly) -- it does
#: not implement that layer, which is out of scope for a public skill and
#: unnecessary for the plain-ZIP packages this tool creates and reads.
RDKE_SIGNATURE = b'RDKE'

#: Top-level OPC container parts, not App content -- excluded when judging
#: whether a package wraps its files in a single App folder.
OPC_INFRA = {'_rels', '[Content_Types].xml'}

METADATA_TAGS = {
    'category': 'category', 'creator': 'author', 'description': 'description',
    'identifier': 'identifier', 'keywords': 'keywords', 'title': 'title',
    'version': 'version', 'revision': 'revision', 'created': 'created',
    'website': 'website', 'documentation': 'documentation',
    'repository': 'repository', 'company': 'company', 'email': 'email',
    'icon': 'icon',
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def new_config():
    """configparser that preserves key case (RoboDK reads these with QSettings)."""
    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    return cfg


def read_config(app_dir):
    path = os.path.join(app_dir, 'AppConfig.ini')
    cfg = new_config()
    if os.path.isfile(path):
        cfg.read(path, encoding='utf-8')
    return cfg, path


def write_config(cfg, path):
    with open(path, 'w', encoding='utf-8') as fid:
        cfg.write(fid, space_around_delimiters=False)


def is_excluded(name):
    return name in EXCLUDE_DIRS or name.lower().endswith(EXCLUDE_FILE_PATTERNS)


def action_files(app_dir):
    """Root-level scripts the AppLoader turns into actions, in on-disk order.

    Only the folder root is scanned (the loader is not recursive) and only .py
    and .exe count. A leading underscore means 'shared module, not an action'.
    """
    out = []
    for name in sorted(os.listdir(app_dir)):
        full = os.path.join(app_dir, name)
        if not os.path.isfile(full) or name.startswith('_'):
            continue
        if name.lower().endswith(('.py', '.exe')):
            out.append(name)
    return out


def action_key(filename):
    """AppConfig.ini section name for an action file (extension stripped)."""
    return os.path.splitext(filename)[0]


def iter_files(app_dir):
    """All packageable files, as paths relative to app_dir, POSIX separators."""
    for root, dirs, files in os.walk(app_dir):
        dirs[:] = sorted(d for d in dirs if not is_excluded(d))
        for name in sorted(files):
            if is_excluded(name):
                continue
            rel = os.path.relpath(os.path.join(root, name), app_dir)
            yield rel.replace(os.sep, '/')


def code_only(src):
    """Source with comments and docstrings removed.

    The action templates document the other action shapes in their runmain()
    docstring, so a plain substring search would report every script as using
    every helper. Only real calls should count.
    """
    import io
    import tokenize
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return src

    # Blank the removed spans in place so line/column layout - and therefore every
    # substring search below - still works on the result.
    lines = [list(line) for line in src.splitlines(keepends=True)]

    def blank(start, end):
        srow, scol = start
        erow, ecol = end
        for row in range(srow, erow + 1):
            line = lines[row - 1]
            first = scol if row == srow else 0
            last = ecol if row == erow else len(line)
            for col in range(first, min(last, len(line))):
                if line[col] != '\n':
                    line[col] = ' '

    at_line_start = True
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            blank(tok.start, tok.end)
        elif tok.type == tokenize.STRING and at_line_start:
            # A string that is the whole statement is a docstring, not a value
            blank(tok.start, tok.end)

        if tok.type in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT):
            at_line_start = True
        elif tok.type != tokenize.COMMENT:
            at_line_start = False

    return ''.join(''.join(line) for line in lines)


def pretty_name(key):
    """'ExportToCsv' or 'export_to_csv' -> 'Export To Csv' for a default label."""
    spaced = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', key.replace('_', ' '))
    return ' '.join(w for w in spaced.split() if w) or key


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

HEADER = '''# --------------------------------------------
# --------------- DESCRIPTION ----------------
#
# {summary}
#
# More information about the RoboDK API for Python here:
#     https://robodk.com/doc/en/RoboDK-API.html
#     https://robodk.com/doc/en/PythonAPI/index.html
#
# More information on RoboDK Apps here:
#     https://github.com/RoboDK/Plug-In-Interface/tree/master/PluginAppLoader
#
# --------------------------------------------
'''

RUNMAIN_DOC = '''    """
    Entrypoint of this action when it is executed on its own or interacted with in RoboDK.
    Important: Use the function name 'runmain()' if you want to compile this action.
    """
'''

TPL_MOMENTARY = '''
from robodk import robolink, roboapps
from _AppUtilities import ShowMessage
import os

ACTION_NAME = os.path.basename(__file__)


def {func}():
    """Action to perform when the action is clicked in RoboDK."""

    RDK = robolink.Robolink()

    # TODO: implement the action here.
    ShowMessage(RDK, ACTION_NAME, "Clicked!", True)


def runmain():
{doc}
    if roboapps.Unchecked():
        roboapps.Exit()
    else:
        {func}()


if __name__ == '__main__':
    runmain()
'''

TPL_CHECKABLE = '''
from robodk import robolink, robomath, roboapps
from _AppUtilities import ShowMessage
import os

ACTION_NAME = os.path.basename(__file__)


def ActionChecked():
    """Action to perform while the action is checked in RoboDK."""

    RDK = robolink.Robolink()
    APP = roboapps.RunApplication()

    # RunApplication.Run() returns False as soon as RoboDK asks this action to stop
    # (the user unchecked the button, or RoboDK is closing).
    while APP.Run():
        # TODO: one iteration of the background loop.
        robomath.pause(0.25)

    ShowMessage(RDK, ACTION_NAME, "Stopped.", False)


def ActionUnchecked():
    """Action to perform when the action is unchecked in RoboDK.

    This runs in a *separate* process from ActionChecked, so do not use
    roboapps.RunApplication() here; keep it short.
    """
    return


def runmain():
{doc}
    if roboapps.Unchecked():
        ActionUnchecked()
    else:
        roboapps.SkipKill()  # Remove to let RoboDK kill this process 2 s after the stop request
        ActionChecked()


if __name__ == '__main__':
    runmain()
'''

TPL_OPTION = '''
from robodk import robolink, roboapps
from _AppUtilities import ShowMessage
import os

ACTION_NAME = os.path.basename(__file__)


def ActionChecked():
    """Turn the option on. The state lives in the station so every other action can read it."""

    RDK = robolink.Robolink()
    RDK.setParam('{key}', 1.0)
    ShowMessage(RDK, ACTION_NAME, "Enabled", False)


def ActionUnchecked():
    """Turn the option off."""

    RDK = robolink.Robolink()
    RDK.setParam('{key}', 0.0)
    ShowMessage(RDK, ACTION_NAME, "Disabled", False)


def runmain():
{doc}
    if roboapps.Unchecked():
        ActionUnchecked()
    else:
        roboapps.KeepChecked()  # Required, or RoboDK unchecks the button when the script exits
        ActionChecked()


if __name__ == '__main__':
    runmain()
'''

TPL_SELECTION = '''
from robodk import robolink, roboapps
from _AppUtilities import ShowMessage
import os

ACTION_NAME = os.path.basename(__file__)


def {func}():
    """Action to perform on the item(s) the user {verb}."""

    RDK = robolink.Robolink()

    selected_items = RDK.Selection()
    if not selected_items:
        ShowMessage(RDK, ACTION_NAME, "Nothing selected!", True)
        return

    # TODO: implement the action here.
    names = [x.Name() for x in selected_items]
    ShowMessage(RDK, ACTION_NAME, 'User selected ' + ', '.join(names) + '.', True)


def runmain():
{doc}
    if roboapps.Unchecked():
        roboapps.Exit()
    else:
        {func}()


if __name__ == '__main__':
    runmain()
'''

TPL_UTILITIES = HEADER.format(summary="Shared module. The leading underscore keeps the AppLoader from turning it\n# into an action, so it needs no AppConfig.ini section.") + '''
from robodk import robolink


def ShowMessage(RDK, action_name, message, popup=False):
    """Prefix a message with the action name and forward it to RoboDK."""
    s = '\\n\\n' if popup else ' '
    RDK.ShowMessage(f"{action_name}:{s}{message}", popup)


if __name__ == '__main__':
    pass
'''

TPL_INIT = '''# Adding a __init__.py file to your App makes it importable from other Apps and
# RoboDK scripts: RoboDK adds the parent Apps folder to PYTHONPATH when it finds
# this file, so `from {app} import SomeAction` works from anywhere.
#
# This file can be left empty.
'''

TPL_SETTINGS = HEADER.format(summary="Settings for this App. roboapps.AppSettings builds the dialog from the\n# attributes below and stores the values in the RoboDK station.") + '''
from robodk import roboapps


class Settings(roboapps.AppSettings):
    """{title} settings.

    Every public attribute becomes a saved setting and a widget in the dialog.
    Attributes starting with an underscore are not saved. _FIELDS_UI is optional
    but gives each field a readable label and controls the display order;
    a label wrapped in dollar signs ($Like this$) renders as a section header.
    """

    def __init__(self, settings_param='{param}'):
        super().__init__(settings_param)

        from collections import OrderedDict
        self._FIELDS_UI = OrderedDict()

        self._FIELDS_UI['SECTION_GENERAL'] = '$General$'

        self._FIELDS_UI['EXAMPLE_BOOL'] = 'Enable the example'
        self.EXAMPLE_BOOL = True

        self._FIELDS_UI['EXAMPLE_FLOAT'] = 'Example distance (mm)'
        self.EXAMPLE_FLOAT = 100.0

        # A [index, [choices]] pair renders as a dropdown
        self._FIELDS_UI['EXAMPLE_CHOICE'] = 'Example mode'
        self.EXAMPLE_CHOICE = [0, ['First', 'Second', 'Third']]


def runmain():
{doc}
    if roboapps.Unchecked():
        roboapps.Exit()
    else:
        S = Settings()
        S.Load()
        S.ShowUI('{title} Settings')


if __name__ == '__main__':
    runmain()
'''

TPL_README = '''# {title}

{description}

- More about RoboDK Add-ins: <https://robodk.com/doc/en/Add-ins.html>
- RoboDK API for Apps: <https://robodk.com/doc/en/PythonAPI/app.html>

## Actions

{actions}

## Install

Copy the `{app}` folder into RoboDK's `Apps` folder (for example `C:/RoboDK/Apps/`),
or open the packaged `{app}.rdkp` file with RoboDK. Enable it from
Tools ➔ Add-in Manager.
'''

# A neutral placeholder icon. Two tones so it stays legible in RoboDK's light and
# dark themes; replace it with real artwork before publishing.
TPL_ICON = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect x="4" y="4" width="56" height="56" rx="12" fill="#2d6cdf"/>
  <text x="32" y="42" font-family="Helvetica, Arial, sans-serif" font-size="30"
        font-weight="600" fill="#ffffff" text-anchor="middle">{letters}</text>
</svg>
'''


def script_for(key, kind):
    """Render the action script body for one action."""
    doc = RUNMAIN_DOC.rstrip('\n')
    if kind == 'checkable':
        summary = "Checkable action: runs a background loop while the button is checked."
        body = TPL_CHECKABLE.format(doc=doc)
    elif kind in ('option', 'option-group'):
        summary = "Checkable option: toggles a state that the rest of the App reads."
        body = TPL_OPTION.format(doc=doc, key=key.upper())
    elif kind == 'context':
        summary = "Contextual action: shown when the user right-clicks a station item."
        body = TPL_SELECTION.format(doc=doc, func='OnContextAction', verb='right-clicked')
    elif kind == 'doubleclick':
        summary = "Double-click action: runs when the user double-clicks a station item."
        body = TPL_SELECTION.format(doc=doc, func='OnDoubleClickAction', verb='double-clicked')
    else:
        summary = "Momentary action: runs once each time the button is clicked."
        body = TPL_MOMENTARY.format(doc=doc, func='Action' + key)
    return HEADER.format(summary=summary) + body


def config_overrides(kind, index):
    """AppConfig.ini values that differ from the defaults for a given action type."""
    over = {'Priority': str(10 * (index + 1))}
    if kind == 'checkable':
        over['Checkable'] = 'true'
    elif kind == 'option':
        over.update({'Checkable': 'true', 'AddToToolbar': 'false'})
    elif kind == 'option-group':
        over.update({'Checkable': 'true', 'CheckableGroup': '1', 'AddToToolbar': 'false'})
    elif kind == 'context':
        over.update({'TypeOnContextMenu': '-1', 'AddToToolbar': 'false'})
    elif kind == 'doubleclick':
        over.update({'TypeOnDoubleClick': '-1', 'AddToToolbar': 'false'})
    return over


# ---------------------------------------------------------------------------
# manifest.xml / core_properties.xml / _rels/.rels / [Content_Types].xml
#
# A .rdkp is an OPC package (the same container model as .docx/.xlsx): the
# metadata is split into a core-properties part (Dublin Core fields such as
# title/identifier/version) and a manifest part (RoboDK-specific extras and
# the asset list), and _rels/.rels declares which parts those are. RoboDK's
# Add-in Manager finds them exclusively through that relationships file, so a
# package that only has a manifest.xml at its root -- with no _rels/.rels --
# is not recognized as installable even though the XML itself is valid.
# ---------------------------------------------------------------------------


def manifest_icon_rel(meta):
    """Package icon path relative to the App folder, or '' if there is none."""
    return (meta.get('icon') or '').lstrip('/')


def _indent(elem, level=0):
    pad = '\n' + '  ' * level
    if len(elem):
        if not (elem.text or '').strip():
            elem.text = pad + '  '
        for child in elem:
            _indent(child, level + 1)
        if not (elem.tail or '').strip():
            elem.tail = pad
        if not (elem[-1].tail or '').strip():
            elem[-1].tail = pad
    elif level and not (elem.tail or '').strip():
        elem.tail = pad


def _xml(root):
    _indent(root)
    return "<?xml version='1.0' encoding='utf-8'?>\n" + ET.tostring(root, encoding='unicode') + '\n'


def build_core_properties(meta):
    """Return core_properties.xml text: the package's Dublin Core / OPC metadata."""
    for prefix, uri in CORE_PROPS_NS.items():
        ET.register_namespace(prefix, uri)

    def q(prefix, tag):
        return '{%s}%s' % (CORE_PROPS_NS[prefix], tag)

    root = ET.Element(q('', 'coreProperties'))

    def add(prefix, tag, text, attrib=None):
        el = ET.SubElement(root, q(prefix, tag), attrib or {})
        el.text = text
        return el

    add('', 'category', meta.get('category', 'Application'))
    add('', 'contentStatus', 'Final')
    add('dcterms', 'created', meta.get('created', utcnow()), {q('xsi', 'type'): 'dcterms:W3CDTF'})
    add('dc', 'creator', meta.get('author', ''))
    add('dc', 'description', meta.get('description', ''))
    add('dc', 'identifier', meta.get('identifier', ''))
    add('', 'keywords', meta.get('keywords', ''))
    add('dc', 'language', 'eng')
    add('', 'lastModifiedBy', meta.get('author', ''))
    add('dcterms', 'modified', utcnow(), {q('xsi', 'type'): 'dcterms:W3CDTF'})
    add('', 'revision', str(meta.get('revision', 1)))
    add('dc', 'title', meta.get('title', ''))
    add('', 'version', meta.get('version', '1.0.0'))

    return _xml(root)


def build_manifest(app_dir, app_name, meta):
    """Return manifest.xml text: extra (non-Dublin-Core) metadata plus the asset list."""
    for prefix, uri in MANIFEST_NS.items():
        ET.register_namespace(prefix, uri)

    def q(tag):
        return '{%s}%s' % (MANIFEST_NS[''], tag)

    root = ET.Element(q('packageManifest'), {'version': '1.0'})

    extra = ET.SubElement(root, q('extraProperties'))
    for tag in ('website', 'documentation', 'repository', 'company', 'email'):
        ET.SubElement(extra, q(tag)).text = meta.get(tag, '') or None
    if meta.get('icon'):
        ET.SubElement(extra, q('icon')).text = meta['icon']

    assets = ET.SubElement(root, q('assets'))
    icon_rel = manifest_icon_rel(meta)
    for rel in iter_files(app_dir):
        # manifest.xml/core_properties.xml describe the package rather than being
        # installed files, and the icon is metadata rather than an asset.
        if rel in ('manifest.xml', 'core_properties.xml', icon_rel):
            continue
        el = ET.SubElement(assets, q('asset'),
                           {'cpu': 'any', 'system': 'any', 'target': '$(SourcePath)'})
        el.text = '/%s/%s' % (app_name, rel)

    return _xml(root)


def build_rels(app_name):
    """Return _rels/.rels text pointing at the core-properties, manifest and
    AppConfig.ini parts. Required for the Add-in Manager to recognize the package."""
    for prefix, uri in RELS_NS.items():
        ET.register_namespace(prefix, uri)

    def q(tag):
        return '{%s}%s' % (RELS_NS[''], tag)

    root = ET.Element(q('Relationships'))

    def rel(rel_type, target, rid):
        ET.SubElement(root, q('Relationship'), {'Type': rel_type, 'Target': target, 'Id': rid})

    rel(CORE_PROPS_REL, '/%s/core_properties.xml' % app_name, 'rId1')
    rel(MANIFEST_REL, '/%s/manifest.xml' % app_name, 'rId2')
    rel(APPCONFIG_REL, '/%s/AppConfig.ini' % app_name, 'rId3')

    return _xml(root)


def build_content_types(app_name, rel_paths):
    """Return [Content_Types].xml text: per-extension MIME defaults plus an
    Override for the core-properties part, for a well-formed OPC package."""
    for prefix, uri in CONTENT_TYPES_NS.items():
        ET.register_namespace(prefix, uri)

    def q(tag):
        return '{%s}%s' % (CONTENT_TYPES_NS[''], tag)

    root = ET.Element(q('Types'))
    extensions = {'rels'}
    for rel in rel_paths:
        if '.' in rel:
            extensions.add(rel.rsplit('.', 1)[-1].lower())
    for ext in sorted(extensions):
        mime = EXTENSION_CONTENT_TYPES.get(ext, 'application/octet-stream')
        ET.SubElement(root, q('Default'), {'Extension': ext, 'ContentType': mime})
    ET.SubElement(root, q('Override'), {
        'PartName': '/%s/core_properties.xml' % app_name,
        'ContentType': CORE_PROPS_CONTENT_TYPE,
    })

    return _xml(root)


def read_manifest_meta(app_dir):
    """Recover metadata from an existing manifest.xml/core_properties.xml so sync preserves it."""
    meta = {}
    for filename in ('core_properties.xml', 'manifest.xml'):
        path = os.path.join(app_dir, filename)
        if not os.path.isfile(path):
            continue
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for el in root.iter():
            tag = el.tag.split('}')[-1]
            if tag in METADATA_TAGS and el.text:
                meta[METADATA_TAGS[tag]] = el.text
    return meta


# ---------------------------------------------------------------------------
# Subcommand: new
# ---------------------------------------------------------------------------


def parse_action_spec(spec):
    if '=' in spec:
        name, kind = spec.split('=', 1)
    elif ':' in spec:
        name, kind = spec.split(':', 1)
    else:
        name, kind = spec, 'momentary'
    name, kind = name.strip(), kind.strip().lower()
    if kind not in ACTION_TYPES:
        raise SystemExit('Unknown action type %r. Choose from: %s' % (kind, ', '.join(ACTION_TYPES)))
    if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', name):
        raise SystemExit('Invalid action name %r: use a Python-identifier-like name.' % name)
    return name, kind


def cmd_new(args):
    app_dir = os.path.abspath(args.path)
    app_name = os.path.basename(app_dir.rstrip(os.sep))
    if os.path.exists(app_dir) and os.listdir(app_dir) and not args.force:
        raise SystemExit('%s already exists and is not empty (use --force).' % app_dir)
    os.makedirs(app_dir, exist_ok=True)

    title = args.menu_name or pretty_name(app_name)
    actions = [parse_action_spec(s) for s in (args.action or ['RunAction=momentary'])]
    if args.settings:
        actions.append(('Settings', 'momentary'))

    cfg = new_config()
    cfg['General'] = {}
    for key, default in GENERAL_DEFAULTS:
        cfg['General'][key] = default
    cfg['General']['MenuName'] = title
    cfg['General']['MenuParent'] = args.menu_parent
    cfg['General']['Version'] = args.version

    written = []
    for index, (name, kind) in enumerate(actions):
        cfg[name] = {}
        for key, default in ACTION_DEFAULTS:
            cfg[name][key] = default
        cfg[name]['DisplayName'] = pretty_name(name)
        cfg[name]['Description'] = '%s action' % pretty_name(name)
        for key, value in config_overrides(kind, index).items():
            cfg[name][key] = value

        script_path = os.path.join(app_dir, name + '.py')
        if name == 'Settings' and args.settings:
            text = TPL_SETTINGS.format(doc=RUNMAIN_DOC.rstrip('\n'), title=title,
                                       param='%s-Settings' % app_name)
            cfg[name].update({'AddToToolbar': 'false', 'Priority': '100'})
        else:
            text = script_for(name, kind)
        if not os.path.exists(script_path) or args.force:
            with open(script_path, 'w', encoding='utf-8') as fid:
                fid.write(text)
            written.append(name + '.py')

        if not args.no_icons:
            icon_path = os.path.join(app_dir, name + '.svg')
            if not os.path.exists(icon_path):
                letters = ''.join(c for c in name if c.isupper())[:2] or name[:2].upper()
                with open(icon_path, 'w', encoding='utf-8') as fid:
                    fid.write(TPL_ICON.format(letters=letters))
                written.append(name + '.svg')

    write_config(cfg, os.path.join(app_dir, 'AppConfig.ini'))
    written.append('AppConfig.ini')

    extras = {
        '_AppUtilities.py': TPL_UTILITIES,
        '__init__.py': TPL_INIT.format(app=app_name),
        'README.md': TPL_README.format(
            title=title, app=app_name,
            description=args.description or 'A RoboDK Add-in.',
            actions='\n'.join('- **%s** (%s)' % (pretty_name(n), k) for n, k in actions)),
    }
    if not args.no_icons:
        letters = ''.join(c for c in app_name if c.isupper())[:2] or app_name[:2].upper()
        extras['icon.svg'] = TPL_ICON.format(letters=letters)
    for name, text in extras.items():
        path = os.path.join(app_dir, name)
        if not os.path.exists(path) or args.force:
            with open(path, 'w', encoding='utf-8') as fid:
                fid.write(text)
            written.append(name)

    meta = {
        'title': title,
        'description': args.description or 'A RoboDK Add-in.',
        'identifier': args.identifier or 'com.example.app.%s' % app_name.lower(),
        'author': args.author,
        'company': args.author,
        'version': args.version,
        'icon': '/icon.svg' if not args.no_icons else '',
    }
    with open(os.path.join(app_dir, 'core_properties.xml'), 'w', encoding='utf-8') as fid:
        fid.write(build_core_properties(meta))
    written.append('core_properties.xml')
    with open(os.path.join(app_dir, 'manifest.xml'), 'w', encoding='utf-8') as fid:
        fid.write(build_manifest(app_dir, app_name, meta))
    written.append('manifest.xml')

    print('Created Add-in %s in %s' % (app_name, app_dir))
    for name in sorted(set(written)):
        print('  + ' + name)
    print('\nNext: copy the folder into RoboDK/Apps (or link it from the Add-in Manager),')
    print('then Tools -> Add-in Manager -> enable it.')
    return 0


# ---------------------------------------------------------------------------
# Subcommand: check
# ---------------------------------------------------------------------------


def cmd_check(args):
    app_dir = os.path.abspath(args.path)
    app_name = os.path.basename(app_dir.rstrip(os.sep))
    errors, warnings = [], []

    if not os.path.isdir(app_dir):
        raise SystemExit('Not a directory: %s' % app_dir)
    if app_name.startswith('_'):
        errors.append('Folder name starts with "_": the AppLoader will skip this App.')

    cfg, cfg_path = read_config(app_dir)
    if not os.path.isfile(cfg_path):
        errors.append('AppConfig.ini is missing (RoboDK generates one, but ship your own).')
    elif not cfg.has_section('General'):
        errors.append('AppConfig.ini has no [General] section.')

    scripts = action_files(app_dir)
    if not scripts:
        errors.append('No action scripts found at the folder root (only root-level '
                      '.py/.exe files without a leading underscore become actions).')

    keys = {action_key(s) for s in scripts}
    for script in scripts:
        key = action_key(script)
        if not cfg.has_section(key):
            warnings.append('%s has no [%s] section in AppConfig.ini (RoboDK will '
                            'generate defaults on load).' % (script, key))
        if not any(os.path.isfile(os.path.join(app_dir, key + ext))
                   for ext in ('.svg', '.png', '.jpg', '.ico')):
            warnings.append('%s has no icon (%s.svg/.png/.jpg/.ico).' % (script, key))

        if not script.lower().endswith('.py'):
            continue
        with open(os.path.join(app_dir, script), 'r', encoding='utf-8', errors='replace') as fid:
            raw = fid.read()
        src = code_only(raw)
        if 'def runmain(' not in src:
            errors.append('%s does not define runmain(): required to be compilable and '
                          'to be callable as a module.' % script)
        if "__name__ == '__main__'" not in src and '__name__ == "__main__"' not in src:
            errors.append('%s has no __main__ guard, so RoboDK cannot run it.' % script)

        checkable = cfg.has_section(key) and cfg[key].get('Checkable', 'false').strip().lower() == 'true'
        group = cfg[key].get('CheckableGroup', '-1').strip() if cfg.has_section(key) else '-1'
        if checkable:
            # Match a call to Unchecked() but not a definition like ActionUnchecked()
            if not re.search(r'(?<![A-Za-z0-9_])Unchecked\s*\(', src):
                errors.append('%s is Checkable=true but never calls roboapps.Unchecked(): '
                              'the uncheck run would repeat the checked behaviour.' % script)
            loops = 'RunApplication' in src
            if loops and 'SkipKill()' not in src:
                warnings.append('%s runs a RunApplication loop without roboapps.SkipKill(); '
                                'RoboDK force-kills it ~2 s after the stop request.' % script)
            if not loops and 'KeepChecked()' not in src:
                warnings.append('%s is checkable with no background loop and no '
                                'roboapps.KeepChecked(); the button will pop back out when the '
                                'script exits.' % script)
        if not checkable and ('KeepChecked()' in src or 'RunApplication' in src):
            warnings.append('%s uses checkable-only helpers but Checkable is not true in '
                            'AppConfig.ini.' % script)
        if group not in ('', '-1') and not checkable:
            warnings.append('%s sets CheckableGroup=%s but Checkable is not true.' % (script, group))

    for section in cfg.sections():
        if section == 'General' or section in keys:
            continue
        warnings.append('AppConfig.ini has a [%s] section with no matching %s.py/.exe.'
                        % (section, section))

    icon_rel = manifest_icon_rel(read_manifest_meta(app_dir))
    if os.path.isfile(os.path.join(app_dir, 'manifest.xml')):
        listed = set()
        try:
            root = ET.parse(os.path.join(app_dir, 'manifest.xml')).getroot()
            for el in root.iter():
                if el.tag.split('}')[-1] == 'asset' and el.text:
                    listed.add(el.text.strip().lstrip('/').split('/', 1)[-1])
        except ET.ParseError as exc:
            errors.append('manifest.xml is not valid XML: %s' % exc)
        on_disk = {p for p in iter_files(app_dir)
                  if p not in ('manifest.xml', 'core_properties.xml', icon_rel)}
        for missing in sorted(on_disk - listed):
            warnings.append('manifest.xml does not list %s (run "sync").' % missing)
        for stale in sorted(listed - on_disk):
            warnings.append('manifest.xml lists %s which is not on disk (run "sync").' % stale)
    else:
        warnings.append('No manifest.xml: required for the Add-in Manager and the '
                        'RoboDK Marketplace (run "sync" to generate one).')

    if not os.path.isfile(os.path.join(app_dir, 'core_properties.xml')):
        warnings.append('No core_properties.xml: manifest.xml alone is not enough for a '
                        'package RoboDK will actually install (run "sync" to generate one).')

    for name in ('README.md',):
        if not os.path.isfile(os.path.join(app_dir, name)):
            warnings.append('No %s (required to publish on the Marketplace).' % name)

    for root, dirs, files in os.walk(app_dir):
        for d in list(dirs):
            if d in EXCLUDE_DIRS and d == '__pycache__':
                warnings.append('Stale %s in %s (excluded from packages, but delete it).'
                                % (d, os.path.relpath(root, app_dir)))

    for line in errors:
        print('ERROR   ' + line)
    for line in warnings:
        print('WARN    ' + line)
    if not errors and not warnings:
        print('OK      %s looks good (%d action%s).'
              % (app_name, len(scripts), '' if len(scripts) == 1 else 's'))
    else:
        print('\n%d error(s), %d warning(s) in %s' % (len(errors), len(warnings), app_name))
    return 1 if errors else 0


# ---------------------------------------------------------------------------
# Subcommand: sync
# ---------------------------------------------------------------------------


def cmd_sync(args):
    app_dir = os.path.abspath(args.path)
    app_name = os.path.basename(app_dir.rstrip(os.sep))
    if not os.path.isdir(app_dir):
        raise SystemExit('Not a directory: %s' % app_dir)

    cfg, cfg_path = read_config(app_dir)
    changed = []

    if not cfg.has_section('General'):
        cfg['General'] = {}
        changed.append('added [General]')
    for key, default in GENERAL_DEFAULTS:
        if key not in cfg['General']:
            cfg['General'][key] = default or (pretty_name(app_name) if key == 'MenuName' else '')
            changed.append('[General] %s' % key)

    scripts = action_files(app_dir)
    keys = [action_key(s) for s in scripts]
    for index, key in enumerate(keys):
        if not cfg.has_section(key):
            cfg[key] = {}
            changed.append('added [%s]' % key)
        for opt, default in ACTION_DEFAULTS:
            if opt not in cfg[key]:
                if opt == 'DisplayName':
                    default = pretty_name(key)
                elif opt == 'Description':
                    default = '%s action' % pretty_name(key)
                elif opt == 'Priority':
                    default = str(10 * (index + 1))
                cfg[key][opt] = default
                changed.append('[%s] %s' % (key, opt))

    for section in list(cfg.sections()):
        if section != 'General' and section not in keys:
            if args.prune:
                cfg.remove_section(section)
                changed.append('removed orphan [%s]' % section)
            else:
                changed.append('orphan [%s] kept (use --prune to remove)' % section)

    write_config(cfg, cfg_path)

    meta = read_manifest_meta(app_dir)
    meta.setdefault('title', cfg['General'].get('MenuName', app_name))
    meta.setdefault('identifier', 'com.example.app.%s' % app_name.lower())
    meta.setdefault('description', 'A RoboDK Add-in.')
    meta['version'] = cfg['General'].get('Version', meta.get('version', '1.0.0'))
    if not meta.get('icon'):
        for ext in ('.svg', '.png', '.jpg'):
            if os.path.isfile(os.path.join(app_dir, 'icon' + ext)):
                meta['icon'] = '/icon' + ext
                break

    with open(os.path.join(app_dir, 'core_properties.xml'), 'w', encoding='utf-8') as fid:
        fid.write(build_core_properties(meta))
    changed.append('regenerated core_properties.xml')

    with open(os.path.join(app_dir, 'manifest.xml'), 'w', encoding='utf-8') as fid:
        fid.write(build_manifest(app_dir, app_name, meta))
    changed.append('regenerated manifest.xml asset list')

    print('Synced %s' % app_name)
    for line in changed:
        print('  ~ ' + line)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: package
# ---------------------------------------------------------------------------


def cmd_package(args):
    app_dir = os.path.abspath(args.path.rstrip(os.sep))
    app_name = os.path.basename(app_dir)
    if not os.path.isdir(app_dir):
        raise SystemExit('Not a directory: %s' % app_dir)
    if not os.path.isfile(os.path.join(app_dir, 'AppConfig.ini')):
        raise SystemExit('No AppConfig.ini in %s: this is not a RoboDK Add-in folder.' % app_dir)
    if not os.path.isfile(os.path.join(app_dir, 'manifest.xml')) or \
       not os.path.isfile(os.path.join(app_dir, 'core_properties.xml')):
        raise SystemExit('manifest.xml/core_properties.xml missing in %s: run "sync" first.'
                         % app_dir)

    out = args.output or os.path.join(os.path.dirname(app_dir), app_name + '.rdkp')
    out = os.path.abspath(out)
    if os.path.abspath(os.path.dirname(out)).startswith(app_dir + os.sep):
        raise SystemExit('Refusing to write the package inside the Add-in folder: %s' % out)

    meta = read_manifest_meta(app_dir)
    icon_rel = manifest_icon_rel(meta)  # e.g. 'icon.svg', relative to app_dir

    files = list(iter_files(app_dir))
    entries = []  # (path in app_dir, path in zip)
    for rel in files:
        if rel == icon_rel:
            # The package icon is referenced from the manifest by a package-root-relative
            # path (e.g. "/icon.svg") and RoboDK extracts it to that same path relative to
            # the install folder -- a sibling of the App folder, not a file inside it. Every
            # officially distributed .rdkp places it at the zip root for that reason.
            entries.append((rel, icon_rel))
        else:
            # Everything else must stay inside the App folder itself, so RoboDK installs
            # it as .../<AppName>/... rather than dumping files loose into the install root.
            entries.append((rel, '%s/%s' % (app_name, rel)))

    # Always a plain, unencrypted ZIP -- this tool has no cryptography
    # dependency and must never grow one. RoboDK's proprietary encrypted
    # package layer (see check_not_encrypted/RDKE_SIGNATURE below) is
    # intentionally out of scope: this tool only ever detects that layer on
    # read, to refuse cleanly, never produces it.
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('_rels/.rels', build_rels(app_name))
        zf.writestr('[Content_Types].xml', build_content_types(app_name, files))
        for src_rel, zip_path in entries:
            zf.write(os.path.join(app_dir, src_rel), zip_path)

    with open(out, 'rb') as fid:
        assert fid.read(4) != RDKE_SIGNATURE, (
            'package must never produce RoboDK\'s encrypted format')

    size = os.path.getsize(out)
    print('Packaged %d file(s) -> %s (%.1f KB)' % (len(entries) + 2, out, size / 1024.0))
    if args.verbose:
        print('  _rels/.rels')
        print('  [Content_Types].xml')
        for _, zip_path in entries:
            print('  ' + zip_path)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: inspect / extract
# ---------------------------------------------------------------------------


def check_not_encrypted(path):
    with open(path, 'rb') as fid:
        header = fid.read(4)
    if header == RDKE_SIGNATURE:
        raise SystemExit(
            "%s is wrapped in RoboDK's own package obfuscation layer (it starts with the "
            "'RDKE' signature), used for some commercially distributed packages. This tool "
            "only reads and writes plain-ZIP .rdkp packages -- the format every openly-sourced "
            "and Marketplace Add-in uses -- and does not implement that layer. Install the file "
            "through RoboDK's Add-in Manager instead." % path)


def read_relationships(zf):
    """{relationship type URI: target part path} from _rels/.rels, or {} if absent."""
    try:
        data = zf.read('_rels/.rels')
    except KeyError:
        return {}
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return {}
    rels = {}
    for el in root:
        if el.tag.split('}')[-1] != 'Relationship':
            continue
        rtype, target = el.get('Type'), el.get('Target')
        if rtype and target:
            rels[rtype] = target.lstrip('/')
    return rels


def read_package_metadata(zf):
    """Merge core_properties.xml + manifest.xml (found via _rels/.rels) into one dict.

    Returns (meta, dependencies, warnings). warnings flags anything that would
    make RoboDK's Add-in Manager refuse the package even though it is a valid ZIP.
    """
    warnings = []
    rels = read_relationships(zf)
    if not rels:
        warnings.append("No _rels/.rels: RoboDK's Add-in Manager will not recognize this as "
                        "an installable package.")

    names = set(zf.namelist())

    def resolve(rel_type, filename):
        target = rels.get(rel_type)
        if target and target in names:
            return target
        fallback = next((n for n in names if n.rsplit('/', 1)[-1] == filename), None)
        if fallback:
            warnings.append('%s recovered by filename, not by relationship.' % filename)
        return fallback

    core_path = resolve(CORE_PROPS_REL, 'core_properties.xml')
    manifest_path = resolve(MANIFEST_REL, 'manifest.xml')

    meta, dependencies = {}, []
    for part in (core_path, manifest_path):
        if not part:
            continue
        try:
            root = ET.fromstring(zf.read(part))
        except (KeyError, ET.ParseError):
            continue
        for el in root.iter():
            tag = el.tag.split('}')[-1]
            if tag in METADATA_TAGS and el.text:
                meta[METADATA_TAGS[tag]] = el.text
            elif tag == 'dependency':
                dependencies.append(dict(el.attrib))

    return meta, dependencies, warnings


def cmd_inspect(args):
    path = os.path.abspath(args.path)
    if not os.path.isfile(path):
        raise SystemExit('Not a file: %s' % path)
    check_not_encrypted(path)

    with zipfile.ZipFile(path) as zf:
        meta, dependencies, warnings = read_package_metadata(zf)
        infos = zf.infolist()

    names = [i.filename for i in infos]
    total_size = sum(i.file_size for i in infos)
    icon_rel = manifest_icon_rel(meta)
    root_extras = OPC_INFRA | ({icon_rel} if icon_rel else set())
    top_levels = {n.split('/', 1)[0] for n in names if '/' in n} - root_extras
    loose = any('/' not in n and n not in root_extras for n in names)

    print('Package:     %s' % path)
    print('Title:       %s' % meta.get('title', '(unknown)'))
    print('Identifier:  %s' % meta.get('identifier', '(unknown)'))
    print('Version:     %s' % meta.get('version', '(unknown)'))
    print('Category:    %s' % meta.get('category', '(unknown)'))
    if meta.get('author'):
        print('Author:      %s' % meta['author'])
    if meta.get('description'):
        print('Description: %s' % meta['description'])
    for key, label in (('website', 'Website'), ('documentation', 'Docs'), ('repository', 'Repo')):
        if meta.get(key):
            print('%-12s %s' % (label + ':', meta[key]))
    if meta.get('icon'):
        print('Icon:        %s' % meta['icon'])
    if dependencies:
        print('Dependencies:')
        for dep in dependencies:
            print('  - ' + ', '.join('%s=%s' % kv for kv in dep.items()))
    print('Files:       %d (%.1f KB uncompressed)' % (len(names), total_size / 1024.0))
    if len(top_levels) == 1 and not loose:
        folder = next(iter(top_levels))
        print('Layout:      wrapped in a single App folder (%s), as RoboDK expects' % folder)
    elif loose:
        print('Layout:      App files sit loose at the archive root instead of inside their '
              'own folder (usually a packaging mistake; see references/packaging.md)')

    for w in warnings:
        print('WARN         ' + w)

    if args.list:
        print('\nContents:')
        for info in sorted(infos, key=lambda i: i.filename):
            print('  %8d  %s' % (info.file_size, info.filename))
    return 0


def cmd_extract(args):
    path = os.path.abspath(args.path)
    if not os.path.isfile(path):
        raise SystemExit('Not a file: %s' % path)
    check_not_encrypted(path)

    dest = os.path.abspath(args.dest) if args.dest else os.path.join(
        os.path.dirname(path), os.path.splitext(os.path.basename(path))[0])

    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        for name in names:
            # Zip-slip guard: every entry must extract to inside dest.
            target = os.path.abspath(os.path.join(dest, name))
            if target != dest and not target.startswith(dest + os.sep):
                raise SystemExit('Refusing to extract %r: escapes the destination folder.' % name)
        meta, _, _ = read_package_metadata(zf)
        os.makedirs(dest, exist_ok=True)
        zf.extractall(dest)

    print('Extracted %d file(s) -> %s' % (len(names), dest))
    icon_rel = manifest_icon_rel(meta)
    root_extras = OPC_INFRA | ({icon_rel} if icon_rel else set())
    top_levels = {n.split('/', 1)[0] for n in names if '/' in n} - root_extras
    loose = any('/' not in n and n not in root_extras for n in names)
    if len(top_levels) == 1 and not loose:
        print('App folder:  %s' % os.path.join(dest, next(iter(top_levels))))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command')

    p_new = sub.add_parser('new', help='scaffold a new Add-in folder')
    p_new.add_argument('path', help='path of the Add-in folder to create (its name is the App name)')
    p_new.add_argument('--menu-name', default='', help='menu label (default: derived from folder name)')
    p_new.add_argument('--menu-parent', default='', help='parent menu, e.g. menu-Utilities (default: own top-level menu)')
    p_new.add_argument('--action', action='append', metavar='Name=type',
                       help='action to create; type is one of: %s (repeatable)' % ', '.join(ACTION_TYPES))
    p_new.add_argument('--settings', action='store_true', help='add a Settings action using roboapps.AppSettings')
    p_new.add_argument('--description', default='', help='one-line description for README and manifest')
    p_new.add_argument('--author', default='', help='author/company for the manifest')
    p_new.add_argument('--identifier', default='', help='manifest identifier, e.g. com.company.app.name')
    p_new.add_argument('--version', default='1.0.0', help='App version (default 1.0.0)')
    p_new.add_argument('--no-icons', action='store_true', help='do not generate placeholder SVG icons')
    p_new.add_argument('--force', action='store_true', help='overwrite existing files')
    p_new.set_defaults(func=cmd_new)

    p_check = sub.add_parser('check', help='validate an Add-in folder')
    p_check.add_argument('path')
    p_check.set_defaults(func=cmd_check)

    p_sync = sub.add_parser('sync', help='reconcile AppConfig.ini, manifest.xml and core_properties.xml with files on disk')
    p_sync.add_argument('path')
    p_sync.add_argument('--prune', action='store_true', help='remove config sections with no matching script')
    p_sync.set_defaults(func=cmd_sync)

    p_pkg = sub.add_parser('package', help='build a distributable, installable .rdkp file')
    p_pkg.add_argument('path')
    p_pkg.add_argument('-o', '--output', help='output .rdkp path (default: alongside the folder)')
    p_pkg.add_argument('-v', '--verbose', action='store_true')
    p_pkg.set_defaults(func=cmd_package)

    p_inspect = sub.add_parser('inspect', help="show a plain-ZIP .rdkp package's metadata without extracting it")
    p_inspect.add_argument('path', help='.rdkp file to inspect')
    p_inspect.add_argument('-l', '--list', action='store_true', help='also list every file in the archive')
    p_inspect.set_defaults(func=cmd_inspect)

    p_extract = sub.add_parser('extract', help='unzip a plain-ZIP .rdkp package to a folder')
    p_extract.add_argument('path', help='.rdkp file to extract')
    p_extract.add_argument('dest', nargs='?', help='destination folder (default: alongside the file, named after it)')
    p_extract.set_defaults(func=cmd_extract)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
