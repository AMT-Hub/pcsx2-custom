"""Discover official nightlies and report source changes; never build or approve them.

Only repository-owned Python is executed. Upstream files are read as bytes at an
immutable commit. Reports are deduplicated against a separate, durable branch.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

from assess_candidate import literal, REPO

UPSTREAM = 'PCSX2/pcsx2'
REPORT_BRANCH = 'nightly-discovery-reports'
POLICY_VERSION = 1
MAX_PAGES = 20
MAX_NEW_REPORTS = 10
SHA = re.compile(r'[0-9a-f]{40}')
TAG_PATTERN = r'v[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,6}'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n'


def version(tag):
    if not re.fullmatch(TAG_PATTERN, tag):
        raise ValueError('Expected an official numeric version tag.')
    return tuple(int(part) for part in tag[1:].split('.'))


class GitHub:
    def __init__(self, token=None):
        self.token = token

    def get(self, path, *, missing_ok=False):
        return self.request('GET', path, missing_ok=missing_ok)

    def request(self, method, path, data=None, *, missing_ok=False):
        if not path.startswith('/repos/') or '\n' in path:
            raise ValueError('Expected a repository API path.')
        headers = {'Accept': 'application/vnd.github+json',
                   'User-Agent': 'pcsx2-custom-nightly-discovery/1',
                   'X-GitHub-Api-Version': '2022-11-28'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        body = None if data is None else encoded(data).encode()
        request = urllib.request.Request('https://api.github.com' + path,
                                         data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404 and missing_ok:
                return None
            # Do not print response bodies or headers (which may contain secrets).
            raise RuntimeError(f'GitHub API {method} failed with HTTP {error.code}: {path}') from None

    def source(self, commit, name):
        if not SHA.fullmatch(commit) or name.startswith('/') or '..' in name.split('/'):
            raise ValueError('Unsafe source identity.')
        url = f'https://raw.githubusercontent.com/{UPSTREAM}/{commit}/{urllib.parse.quote(name, safe="/")}'
        request = urllib.request.Request(url, headers={'User-Agent': 'pcsx2-custom-nightly-discovery/1'})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise RuntimeError(f'Upstream source read failed with HTTP {error.code}: {name}') from None


def baseline():
    archive = literal(REPO / 'emulator/assemble.py', 'NIGHTLY')
    tag = archive.removeprefix('pcsx2-').removesuffix('-windows-x64-Qt.7z')
    version(tag)
    expected = json.loads((REPO / 'emulator/nightly-upstream-sha256.json').read_text())
    commit = literal(REPO / 'emulator/build.py', 'COMMIT')
    if not SHA.fullmatch(commit):
        raise ValueError('Invalid reviewed commit.')
    # Policy/source changes also invalidate old assessments, without changing pins.
    inputs = ['ci/discover_nightlies.py', 'ci/assess_candidate.py', 'emulator/build.py',
              'emulator/assemble.py', 'emulator/nightly-upstream-sha256.json',
              'experiments/automatic-sorting/apply-automatic-sorting.py',
              'experiments/automatic-sorting/AutoSortTitle.h',
              'experiments/automatic-sorting/automatic-sorting.ini']
    fingerprint = sha256(encoded({p: sha256((REPO / p).read_bytes()) for p in inputs}).encode())
    return {'tag': tag, 'commit': commit, 'integration_hashes': expected,
            'policy_fingerprint': fingerprint}


def resolve_tag(api, tag):
    version(tag)
    result = api.get(f'/repos/{UPSTREAM}/commits/{tag}')
    commit = result['sha']
    if not SHA.fullmatch(commit):
        raise ValueError('Invalid upstream commit identity.')
    return commit


def list_candidates(api, reviewed):
    """Scan release pages through our baseline; fail visibly if coverage is limited.

    GitHub lists recent releases first. We process the entire boundary page, then
    sort versions numerically. Do not use /releases/latest: nightlies are prereleases.
    """
    found = {}
    for page in range(1, MAX_PAGES + 1):
        releases = api.get(f'/repos/{UPSTREAM}/releases?per_page=100&page={page}')
        boundary = False
        for release in releases:
            tag = release.get('tag_name', '')
            if tag == reviewed['tag'] and not release.get('draft'):
                boundary = True
            try:
                newer = version(tag) > version(reviewed['tag'])
            except ValueError:
                continue
            if newer and release.get('prerelease') is True and release.get('draft') is False:
                if not release.get('published_at'):
                    raise ValueError('Published release has no publication date.')
                found[tag] = release
        if boundary or len(releases) < 100:
            return sorted(found.values(), key=lambda r: version(r['tag_name']), reverse=True)
    raise RuntimeError('Release scan exceeded its page limit before reaching the reviewed baseline. No complete discovery result was recorded.')


def release_identity(release, commit, reviewed):
    # Download metadata is descriptive; it is never accepted as a trusted hash.
    assets = sorted(({'id': a['id'], 'name': a['name'], 'size': a['size'],
                     'updated_at': a.get('updated_at'), 'digest': a.get('digest'),
                     'state': a.get('state')} for a in release.get('assets', [])),
                    key=lambda a: (a['name'], a['id']))
    return {'tag': release['tag_name'], 'commit': commit,
            'release_id': release['id'], 'published_at': release['published_at'],
            'assets': assets, 'baseline_tag': reviewed['tag'],
            'baseline_commit': reviewed['commit'],
            'policy_fingerprint': reviewed['policy_fingerprint'],
            'policy_version': POLICY_VERSION}


def areas(name):
    """Conservative path hints, not a claim of semantic compatibility."""
    result = []
    lower = name.lower()
    if name.startswith(('pcsx2/ps2/', 'pcsx2/CDVD/')) or name == 'pcsx2/VMManager.cpp':
        result.append('BIOS / boot / disc handling')
    if name.startswith(('pcsx2/GS/', 'common/Vulkan/', 'common/D3D', 'common/GL/')) or any(
            part in lower for part in ('displaywidget', 'qthost', 'mainwindow', 'imgui', 'windowinfo')):
        result.append('ShaderGlass / graphics / fullscreen / pause UI')
    if 'gamelist' in lower or 'gamesummary' in lower:
        result.append('Sorting Titles / game list')
    if any(part in lower for part in ('input', 'pad/', 'hotkey', 'controller')):
        result.append('Controller input / hotkeys')
    if any(part in lower for part in ('config', 'settings', 'host.cpp', 'mainwindow', 'autoupdat', 'main.cpp')):
        result.append('Portable settings / launch / updater integration')
    if (name.startswith(('.github/', '3rdparty/', 'cmake/', 'scripts/')) or
            'cmake' in lower or name.endswith(('.vcxproj', '.sln')) or name == '.gitmodules'):
        result.append('Build / dependencies')
    return result or ['Other upstream code / data (review still required)']


def assess_release(api, release, commit, reviewed, now):
    identity = release_identity(release, commit, reviewed)
    checks = []
    for name, expected in sorted(reviewed['integration_hashes'].items()):
        raw = api.source(commit, name)
        actual = None if raw is None else sha256(raw.replace(b'\r\n', b'\n'))
        checks.append({'file': name, 'expected': expected, 'actual': actual,
                       'status': 'missing' if actual is None else 'unchanged' if actual == expected else 'changed'})
    comparison = api.get(f'/repos/{UPSTREAM}/compare/{reviewed["commit"]}...{commit}?per_page=1')
    # API lists at most 300 files, on the first page only. At the boundary we
    # conservatively mark coverage incomplete, even if exactly 300 changed.
    files = comparison.get('files')
    if not isinstance(files, list):
        raise ValueError('Comparison did not include a changed-file list.')
    changed = []
    for item in files:
        name = item['filename']
        previous = item.get('previous_filename')
        changed.append({'file': name, 'previous_file': previous, 'status': item['status'],
                        'areas': sorted(set(areas(name) + (areas(previous) if previous else [])))})
    expected_asset = f'pcsx2-{release["tag_name"]}-windows-x64-Qt.7z'
    windows_assets = [a for a in identity['assets'] if a['name'] == expected_asset and
                      a['size'] > 0 and a['state'] == 'uploaded']
    warnings = []
    if len(files) >= 300:
        warnings.append('GitHub limits this comparison to 300 files; the full change list needs a local source review.')
    if comparison.get('status') not in ('ahead', 'identical'):
        warnings.append('Candidate history is not a simple continuation of the reviewed baseline; inspect its ancestry.')
    if len(windows_assets) != 1:
        warnings.append('The expected Windows x64 Qt archive is missing, incomplete or ambiguous; recheck release packaging.')
    if commit == reviewed['commit']:
        warnings.append('New version tag points to the already reviewed commit; verify upstream release identity.')
    report = {'schema': 1, 'identity': identity, 'assessed_at': now,
              'status': 'review-required', 'build_permitted': False, 'release_approved': False,
              'integration_checks': checks, 'changed_files': changed,
              'comparison_status': comparison.get('status'),
              'ahead_by': comparison.get('ahead_by'), 'behind_by': comparison.get('behind_by'),
              'changed_file_list_complete': len(files) < 300,
              'expected_windows_asset': expected_asset, 'windows_asset_available': len(windows_assets) == 1,
              'warnings': warnings,
              'limitations': ['Path-based hints and file hashes are not behavioural compatibility tests.',
                             'Dependency binaries, official archives and release asset hashes are not verified here.',
                             'Human source review, custom build and Windows acceptance are still required.']}
    return report


def safe(value):
    # Treat upstream names as data, not Markdown/HTML, mentions or workflow commands.
    return html.escape(str(value), quote=True).replace('|', '&#124;').replace('`', '&#96;').replace('@', '&#64;').replace('\n', ' ').replace('\r', ' ')


def markdown(report):
    info = report['identity']
    changes = [x for x in report['integration_checks'] if x['status'] != 'unchanged']
    lines = [f'# Nightly {info["tag"]}: review required', '',
             '**Discovery report only — not approved for building, installation or publication.**', '',
             f'Assessed: {report["assessed_at"]}', '',
             f'Baseline: `{info["baseline_tag"]}` / `{info["baseline_commit"]}`', '',
             f'Candidate: `{info["tag"]}` / `{info["commit"]}`', '',
             f'[Official release](https://github.com/{UPSTREAM}/releases/tag/{info["tag"]}) · '
             f'[Full source comparison](https://github.com/{UPSTREAM}/compare/{info["baseline_commit"]}...{info["commit"]})', '',
             f'Integration files: {len(changes)} changed or missing out of {len(report["integration_checks"])}.', '',
             f'Expected Windows archive: `{report["expected_windows_asset"]}` — '
             + ('present (not downloaded or verified).' if report['windows_asset_available'] else 'not ready.'), '',
             '## Integration checks', '', '| File | Result |', '| --- | --- |']
    lines += [f'| {safe(x["file"])} | {x["status"]} |' for x in report['integration_checks']]
    lines += ['', '## Wider upstream changes', '',
              f'History: {safe(report["comparison_status"])}; ahead by {report["ahead_by"]} commit(s).', '',
              '| File | Change | Areas to review |', '| --- | --- | --- |']
    lines += [f'| {safe(x["file"])}' + (f' (was {safe(x["previous_file"])})' if x['previous_file'] else '') +
              f' | {safe(x["status"])} | {safe("; ".join(x["areas"]))} |' for x in report['changed_files']]
    if not report['changed_files']:
        lines += ['| No changed files returned | — | Review still required |']
    lines += ['', '## Limits and required follow-up', '']
    lines += ['- ' + x for x in report['warnings'] + report['limitations']]
    lines += ['', 'Review source and dependency changes, port patches if necessary, then use the existing reviewed candidate build workflow. '
              'Test BIOS selection/fallback, shaders in windowed/fullscreen/pause, cursor and shortcuts, controller hotkeys, Sorting Titles, '
              'launcher/version/taskbar and update/rollback before separate signing and publication.', '']
    return '\n'.join(lines)


def load_state(api, repository):
    head = api.get(f'/repos/{repository}/git/ref/heads/{REPORT_BRANCH}', missing_ok=True)
    if head is None:
        return None, {'schema': 1, 'entries': {}}
    sha = head['object']['sha']
    response = api.get(f'/repos/{repository}/contents/state.json?ref={sha}')
    import base64
    state = json.loads(base64.b64decode(response['content'], validate=False))
    if state.get('schema') != 1 or not isinstance(state.get('entries'), dict):
        raise ValueError('Unrecognised discovery state; refusing to overwrite it.')
    return sha, state


def discover(api, reviewed, state, now):
    if resolve_tag(api, reviewed['tag']) != reviewed['commit']:
        raise RuntimeError('Reviewed upstream tag no longer matches the pinned commit. Review the upstream identity before discovery continues.')
    releases = list_candidates(api, reviewed)
    entries = dict(state['entries'])
    generated = {}
    seen = 0
    pending = 0
    changed_tags = []
    for release in releases:
        tag = release['tag_name']
        commit = resolve_tag(api, tag)
        identity = release_identity(release, commit, reviewed)
        key = sha256(encoded(identity).encode())
        if key in entries:
            seen += 1
            continue
        if len(changed_tags) >= MAX_NEW_REPORTS:
            pending += 1
            continue
        report = assess_release(api, release, commit, reviewed, now)
        stem = f'reports/{tag}/{key}'
        generated[stem + '.json'] = encoded(report)
        generated[stem + '.md'] = markdown(report)
        entries[key] = {'tag': tag, 'commit': commit, 'baseline_tag': reviewed['tag'],
                        'baseline_commit': reviewed['commit'], 'policy_fingerprint': reviewed['policy_fingerprint'],
                        'report': stem + '.md', 'assessed_at': now}
        changed_tags.append(tag)
    new_state = {'schema': 1, 'entries': entries}
    summary = {'schema': 1, 'checked_at': now, 'baseline_tag': reviewed['tag'],
               'baseline_commit': reviewed['commit'],
               'latest_nightly_in_scan': releases[0]['tag_name'] if releases else reviewed['tag'],
               'new_reports': changed_tags, 'already_reported': seen,
               'pending_reports': pending, 'discovery_complete': pending == 0,
               'build_permitted': False, 'release_approved': False}
    # Candidate records remain deduplicated. The publishing entry point adds a
    # separate successful-check record even when there is no new candidate.
    previous_baseline = state.get('baseline')
    current_baseline = {k: reviewed[k] for k in ('tag', 'commit', 'policy_fingerprint')}
    if generated or previous_baseline != current_baseline:
        new_state['baseline'] = current_baseline
        generated['state.json'] = encoded(new_state)
        generated['README.md'] = render_index(new_state)
    return summary, generated


def render_index(state):
    reviewed = state['baseline']
    current = [entry for entry in state['entries'].values() if entry['baseline_commit'] == reviewed['commit']
               and entry['policy_fingerprint'] == reviewed['policy_fingerprint']]
    current.sort(key=lambda e: (version(e['tag']), e['assessed_at']), reverse=True)
    index = ['# PCSX2 nightly discovery reports', '',
             '**These are review requests, not approved updates.**', '',
             f'Reviewed baseline: **{reviewed["tag"]}** (`{reviewed["commit"]}`).', '',
             'Discovery is scheduled hourly at **:53 UTC**. GitHub may delay or drop scheduled events; '
             'the next hour provides another opportunity. '
             'See the [workflow](https://github.com/AMT-Hub/pcsx2-custom/actions/workflows/nightly-discovery.yml) '
             'for runs, failures and manual checks.', '', '## Check history', '']
    for key, label in [('last_successful_check', 'Last successful check'),
                       ('last_successful_scheduled_check', 'Last successful scheduled check')]:
        check = state.get(key)
        if check:
            stamp = safe(check['completed_at'])
            if check.get('run_url'):
                stamp = f'[{stamp}]({check["run_url"]})'
            index += [f'- **{label}:** {stamp} — event `{safe(check["event"])}`.']
        else:
            index += [f'- **{label}: not yet recorded.**']
    index += ['', 'Push/manual checks do not verify the scheduled trigger. If the scheduled timestamp is missing '
              'or more than three hours old, investigate scheduling in Actions. '
              'These are fixed timestamps, not a live health badge. '
              '[Machine-readable last check](last-check.json).', '',
              '## Reports against the current baseline', '']
    index += [f'- [{e["tag"]} / {e["commit"][:12]}]({e["report"]}) — {e["assessed_at"]}' for e in current]
    if not current:
        index += ['No newer official nightly has been reported against this baseline.']
    index += ['', 'Older assessments remain under `reports/`; their baseline and source identity are recorded in each report. '
              'Unchanged candidates are not reported twice. Retagged releases, changed assets or changed review inputs '
              'produce a new candidate record. Each run assesses at most 10 unseen candidates, newest first; '
              'any backlog is stated in its summary. Successful-check timestamps update independently of candidate reports.', '',
              'Reports do not modify the custom emulator, launcher, updater, reviewed pins, releases or signed feed.', '']
    return '\n'.join(index)


def execution_context(environment):
    event = environment.get('GITHUB_EVENT_NAME', 'local')
    if event not in ('schedule', 'push', 'workflow_dispatch', 'pull_request', 'local'):
        raise ValueError('Unrecognised discovery trigger.')
    run_id = environment.get('GITHUB_RUN_ID')
    if run_id is not None and not re.fullmatch(r'[0-9]{1,30}', run_id):
        raise ValueError('Invalid workflow run identity.')
    attempt = environment.get('GITHUB_RUN_ATTEMPT', '1')
    if not re.fullmatch(r'[1-9][0-9]{0,5}', attempt):
        raise ValueError('Invalid workflow attempt.')
    commit = environment.get('GITHUB_SHA')
    if commit is not None and not SHA.fullmatch(commit):
        raise ValueError('Invalid workflow source identity.')
    if event == 'schedule' and (not run_id or not commit):
        raise ValueError('Scheduled checks require a workflow run and source identity.')
    url = f'https://github.com/AMT-Hub/pcsx2-custom/actions/runs/{run_id}/attempts/{attempt}' if run_id else None
    return {'event': event, 'run_attempt': int(attempt), 'run_url': url, 'source_commit': commit}


def record_success(summary, previous_state, generated, context, completed_at):
    """Stage health and candidate state together; only publish() persists them.

    A failed discovery never calls this function. A failed final ref update leaves
    both the previous reports and their successful-check timestamp in place.
    """
    files = dict(generated)
    state = json.loads(files['state.json']) if 'state.json' in files else dict(previous_state)
    check = {**context, 'completed_at': completed_at, 'scan_started_at': summary['checked_at'],
             'baseline_tag': summary['baseline_tag'], 'latest_nightly_in_scan': summary['latest_nightly_in_scan'],
             'new_reports': list(summary['new_reports']), 'pending_reports': summary['pending_reports'],
             'discovery_complete': summary['discovery_complete']}
    # A manual rerun keeps the original event name. It must not make an old
    # scheduled event look like a new, successful clock-triggered execution.
    fresh_schedule = context['event'] == 'schedule' and context['run_attempt'] == 1
    scheduled = check if fresh_schedule else previous_state.get('last_successful_scheduled_check')
    state['last_successful_check'] = check
    state['last_successful_scheduled_check'] = scheduled
    files['state.json'] = encoded(state)
    files['last-check.json'] = encoded({'schema': 1, 'last_successful_check': check,
                                       'last_successful_scheduled_check': scheduled})
    files['README.md'] = render_index(state)
    return files


def publish(api, repository, expected_head, files):
    """One non-forced branch update; a failed/concurrent write never marks work done."""
    if not files:
        return None
    for name in files:
        if name not in ('README.md', 'state.json', 'last-check.json') and not re.fullmatch(
                rf'reports/{TAG_PATTERN}/[0-9a-f]{{64}}\.(json|md)', name):
            raise ValueError('Unexpected report destination.')
    base = f'/repos/{repository}'
    observed = api.get(base + f'/git/ref/heads/{REPORT_BRANCH}', missing_ok=True)
    observed_sha = observed['object']['sha'] if observed else None
    if observed_sha != expected_head:
        raise RuntimeError('Report branch changed during discovery; rerun to preserve concurrent reports.')
    tree_data = {'tree': [{'path': p, 'mode': '100644', 'type': 'blob', 'content': content}
                          for p, content in sorted(files.items())]}
    if expected_head:
        parent = api.get(base + f'/git/commits/{expected_head}')
        tree_data['base_tree'] = parent['tree']['sha']
    tree = api.request('POST', base + '/git/trees', tree_data)
    commit = api.request('POST', base + '/git/commits', {
        'message': 'Record nightly discovery assessment', 'tree': tree['sha'],
        'parents': [expected_head] if expected_head else []})
    if expected_head:
        api.request('PATCH', base + f'/git/refs/heads/{REPORT_BRANCH}', {'sha': commit['sha'], 'force': False})
    else:
        api.request('POST', base + '/git/refs', {'ref': f'refs/heads/{REPORT_BRANCH}', 'sha': commit['sha']})
    return commit['sha']


def run_summary(summary, published, dry_run):
    return ('## Official nightly discovery\n\n'
            f'- Reviewed baseline: **{summary["baseline_tag"]}**\n'
            f'- Latest nightly in scan: **{summary["latest_nightly_in_scan"]}**\n'
            f'- New reports: **{len(summary["new_reports"])}**'
            + (': ' + ', '.join(summary['new_reports']) if summary['new_reports'] else '') + '\n'
            f'- Previously reported candidates: {summary["already_reported"]}\n'
            f'- Remaining backlog: {summary["pending_reports"]}\n'
            f'- Report storage: {"dry run; no branch writes" if dry_run else "updated " + published if published else "already current"}\n\n'
            'No candidate was built, approved, signed or published to the updater feed.\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY', 'AMT-Hub/pcsx2-custom'))
    parser.add_argument('--output', type=Path, default=Path('discovery-output'))
    parser.add_argument('--publish', action='store_true', help='Commit reports to the dedicated report branch only.')
    args = parser.parse_args()
    if args.repository != 'AMT-Hub/pcsx2-custom':
        raise ValueError('Discovery publication is scoped to AMT-Hub/pcsx2-custom.')
    api = GitHub(os.environ.get('GH_TOKEN'))
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        head, state = load_state(api, args.repository)
        summary, files = discover(api, baseline(), state, datetime.now(timezone.utc).isoformat())
        if args.publish:
            files = record_success(summary, state, files, execution_context(os.environ),
                                   datetime.now(timezone.utc).isoformat())
        for name, content in files.items():
            dest = args.output / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding='utf-8')
        published = publish(api, args.repository, head, files) if args.publish else None
        summary['report_commit'] = published
        summary['dry_run'] = not args.publish
        (args.output / 'run.json').write_text(encoded(summary), encoding='utf-8')
        text = run_summary(summary, published, not args.publish)
    except Exception as error:
        text = '## Nightly discovery failed\n\n' + safe(str(error)) + '\n\n'
        text += 'Discovery did not finish successfully. Check the report branch before retrying a failed write. The approved updater feed was not changed.\n'
        (args.output / 'failure.json').write_text(encoded({'error': str(error)}), encoding='utf-8')
        raise
    finally:
        if 'text' in locals():
            (args.output / 'run.md').write_text(text, encoding='utf-8')
            if os.environ.get('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
                    stream.write(text)
            print(text)


if __name__ == '__main__':
    main()
