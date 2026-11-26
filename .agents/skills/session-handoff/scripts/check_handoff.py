#!/usr/bin/env python3
"""Read-only local consistency checks; no semantic or remote verification."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def check(manifest: Path) -> dict:
    manifest = manifest.resolve()
    issues: list[dict] = []
    checked = 0
    external = 0
    links = 0

    def issue(level: str, code: str, path: str = '') -> None:
        issues.append({'level': level, 'code': code, 'path': path})

    def result() -> dict:
        errors = sum(i['level'] == 'error' for i in issues)
        return {
            'passed': errors == 0,
            'status': 'error' if errors else 'warning' if issues else 'ok',
            'files_checked': checked,
            'local_links_checked': links,
            'external_links_not_checked': external,
            'semantic_validation': 'NOT_PERFORMED',
            'remote_validation': 'NOT_PERFORMED',
            'issues': issues,
        }

    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError):
        issue('error', 'manifest_unreadable_or_invalid_json', str(manifest))
        return result()
    if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
        issue('error', 'unsupported_manifest_version', str(manifest))
        return result()
    if not isinstance(data.get('entry'), str) or not data['entry'].strip():
        issue('error', 'entry_path_required', str(manifest))
        return result()
    if not isinstance(data.get('files'), list) or not data['files']:
        issue('error', 'nonempty_files_list_required', str(manifest))
        return result()

    base = manifest.parent
    entry = (base / data['entry']).resolve()
    records: dict[Path, dict] = {}
    for row in data['files']:
        if not isinstance(row, dict) or not isinstance(row.get('path'), str) or not row['path'].strip():
            issue('error', 'invalid_file_record', str(manifest))
            continue
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', row['path']):
            issue('error', 'manifest_requires_local_file_paths')
            continue
        path = (base / row['path']).resolve()
        if path == manifest:
            issue('error', 'manifest_self_reference', str(path))
            continue
        if path in records:
            issue('error', 'duplicate_file_record', str(path))
            continue
        records[path] = row
        kind = row.get('kind')
        if kind not in {'artifact', 'snapshot', 'live'} or type(row.get('required', True)) is not bool:
            issue('error', 'invalid_kind_or_required_flag', str(path))
            continue
        expected = row.get('sha256')
        if expected is not None and (not isinstance(expected, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', expected)):
            issue('error', 'invalid_sha256', str(path))
            continue
        if kind in {'artifact', 'snapshot'} and expected is None:
            issue('error', 'frozen_file_hash_required', str(path))
            continue
        if not path.is_file():
            issue('error' if row.get('required', True) else 'warning', 'file_missing', str(path))
            continue
        try:
            actual = digest(path)
        except OSError:
            issue('error', 'file_unreadable', str(path))
            continue
        checked += 1
        if expected is not None and actual != expected.lower():
            issue('warning' if kind == 'live' else 'error', 'live_source_changed_reread' if kind == 'live' else 'frozen_file_changed', str(path))
        if kind == 'live' and expected is None:
            issue('warning', 'live_source_has_no_freshness_baseline', str(path))
        if kind != 'artifact' or path.suffix.lower() not in {'.md', '.markdown'}:
            continue
        try:
            body = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            issue('error', 'artifact_text_unreadable', str(path))
            continue
        # The checker follows local Markdown destinations, never their contents.
        for raw in re.findall(r'\]\(([^)\n]+)\)', body):
            target = raw.strip()
            if target.startswith('<') and '>' in target:
                target = target[1:target.index('>')]
            else:
                target = re.split(r'\s+["\']', target, maxsplit=1)[0]
            if target.startswith('#'):
                continue
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) and not re.match(r'^[a-zA-Z]:[/\\]', target):
                external += 1
                continue
            destination = unquote(re.split(r'[#?]', target, maxsplit=1)[0])
            destination = re.sub(r':\d+(?::\d+)?$', '', destination)
            if not destination:
                continue
            links += 1
            if not (path.parent / destination).exists():
                issue('error', 'local_link_missing', str(path.parent / destination))

    if entry not in records or records[entry].get('kind') != 'artifact' or not records[entry].get('required', True):
        issue('error', 'entry_must_be_required_artifact', str(entry))
    return result()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path, help='version 1 state.json')
    args = parser.parse_args()
    report = check(args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
