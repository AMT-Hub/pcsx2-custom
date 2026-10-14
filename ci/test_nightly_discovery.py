import json
import unittest
from unittest.mock import patch

import discover_nightlies as discovery


BASE = 'a' * 40
NEW = 'b' * 40
NOW = '2026-10-15T06:23:00+00:00'


def reviewed():
    return {'tag': 'v2.9.127', 'commit': BASE, 'policy_fingerprint': 'c' * 64,
            'integration_hashes': {'pcsx2/VMManager.cpp': discovery.sha256(b'old\n')}}


def release(tag='v2.9.128', *, nightly=True, draft=False):
    return {'id': 123, 'tag_name': tag, 'prerelease': nightly, 'draft': draft,
            'published_at': NOW, 'assets': [
                {'id': 234, 'name': f'pcsx2-{tag}-windows-x64-Qt.7z', 'size': 100,
                 'state': 'uploaded', 'updated_at': NOW, 'digest': 'sha256:' + 'd' * 64}]}


class FakeAPI:
    def __init__(self, releases=None):
        self.releases = releases if releases is not None else [release(), release('v2.9.127')]
        self.calls = []
        self.commit = NEW
        self.raw = b'old\r\n'
        self.comparison = {'status': 'ahead', 'ahead_by': 1, 'behind_by': 0,
                           'files': [{'filename': 'pcsx2/GS/Renderers/Vulkan/GSDeviceVK.cpp', 'status': 'modified'}]}

    def get(self, path, **kwargs):
        self.calls.append(path)
        if '/commits/v2.9.127' in path:
            return {'sha': BASE}
        if '/commits/' in path:
            return {'sha': self.commit}
        if '/releases?' in path:
            return self.releases
        if '/compare/' in path:
            return self.comparison
        raise AssertionError(path)

    def source(self, commit, name):
        self.calls.append(('source', commit, name))
        return self.raw


def empty():
    return {'schema': 1, 'entries': {}}


class DiscoveryTests(unittest.TestCase):
    def test_numeric_order_and_only_published_nightlies(self):
        api = FakeAPI([release('v2.9.99'), release('v2.9.130'), release('v2.9.129'),
                       release('v2.10.0', nightly=False), release('v2.9.131', draft=True),
                       release('nightly'), release('v2.9.132;bad'), release('v2.9.127')])
        self.assertEqual([r['tag_name'] for r in discovery.list_candidates(api, reviewed())], ['v2.9.130', 'v2.9.129'])

    def test_pages_through_baseline_and_whole_boundary_page(self):
        api = FakeAPI()
        page1 = [release('v2.9.130')] * 100
        page2 = [release('v2.9.127'), release('v2.9.129')]
        with patch.object(api, 'get', side_effect=[page1, page2]) as get:
            found = discovery.list_candidates(api, reviewed())
        self.assertEqual([r['tag_name'] for r in found], ['v2.9.130', 'v2.9.129'])
        self.assertIn('page=2', get.call_args[0][0])

    def test_future_major_nightly_is_reported_but_not_approved(self):
        api = FakeAPI([release('v3.0.1'), release('v2.9.127')])
        summary, files = discovery.discover(api, reviewed(), empty(), NOW)
        self.assertEqual(summary['new_reports'], ['v3.0.1'])
        report = json.loads(next(v for k, v in files.items() if k.startswith('reports/') and k.endswith('.json')))
        self.assertFalse(report['build_permitted'])
        self.assertFalse(report['release_approved'])

    def test_page_limit_fails_instead_of_claiming_complete(self):
        api = FakeAPI([release('v2.9.128')] * 100)
        with patch.object(discovery, 'MAX_PAGES', 2), self.assertRaisesRegex(RuntimeError, 'page limit'):
            discovery.list_candidates(api, reviewed())

    def test_empty_release_list_is_successful_no_new_result(self):
        summary, files = discovery.discover(FakeAPI([]), reviewed(), empty(), NOW)
        self.assertEqual(summary['new_reports'], [])
        self.assertIn('No newer official nightly', files['README.md'])

    def test_no_new_release_creates_index_once(self):
        api = FakeAPI([release('v2.9.127')])
        first, files = discovery.discover(api, reviewed(), empty(), NOW)
        second, repeated = discovery.discover(api, reviewed(), json.loads(files['state.json']), NOW)
        self.assertEqual(repeated, {})
        self.assertEqual(first['new_reports'], second['new_reports'])

    def test_new_candidate_reports_never_permit_build_or_release(self):
        report = discovery.assess_release(FakeAPI(), release(), NEW, reviewed(), NOW)
        self.assertEqual(report['status'], 'review-required')
        self.assertFalse(report['build_permitted'])
        self.assertFalse(report['release_approved'])
        self.assertEqual(report['integration_checks'][0]['status'], 'unchanged')
        self.assertIn('ShaderGlass', report['changed_files'][0]['areas'][0])
        self.assertTrue(report['windows_asset_available'])

    def test_same_candidate_skips_source_and_compare_reads(self):
        api = FakeAPI()
        _, files = discovery.discover(api, reviewed(), empty(), NOW)
        api.calls.clear()
        summary, repeated = discovery.discover(api, reviewed(), json.loads(files['state.json']), NOW)
        self.assertEqual(repeated, {})
        self.assertEqual(summary['already_reported'], 1)
        self.assertFalse(any(isinstance(c, tuple) or '/compare/' in c for c in api.calls))

    def test_retag_asset_change_and_policy_change_are_reassessed(self):
        _, files = discovery.discover(FakeAPI(), reviewed(), empty(), NOW)
        state = json.loads(files['state.json'])
        for change in ('retag', 'asset', 'policy'):
            with self.subTest(change=change):
                api = FakeAPI()
                base = reviewed()
                if change == 'retag':
                    api.commit = 'e' * 40
                elif change == 'asset':
                    api.releases[0]['assets'][0]['size'] += 1
                else:
                    base['policy_fingerprint'] = 'f' * 64
                result, updated = discovery.discover(api, base, state, NOW)
                self.assertEqual(result['new_reports'], ['v2.9.128'])
                self.assertEqual(len(json.loads(updated['state.json'])['entries']), 2)
                self.assertEqual(len(state['entries']), 1)

    def test_retagged_baseline_fails(self):
        api = FakeAPI()
        with patch.object(api, 'get', return_value={'sha': NEW}), self.assertRaisesRegex(RuntimeError, 'pinned commit'):
            discovery.discover(api, reviewed(), empty(), NOW)

    def test_missing_and_changed_integration_file(self):
        for raw, expected in [(None, 'missing'), (b'new\n', 'changed')]:
            with self.subTest(raw=raw):
                api = FakeAPI()
                api.raw = raw
                result = discovery.assess_release(api, release(), NEW, reviewed(), NOW)
                self.assertEqual(result['integration_checks'][0]['status'], expected)

    def test_api_failure_does_not_advance_state(self):
        state = empty()
        api = FakeAPI()
        with patch.object(api, 'source', side_effect=RuntimeError('HTTP 429')):
            with self.assertRaisesRegex(RuntimeError, '429'):
                discovery.discover(api, reviewed(), state, NOW)
        self.assertEqual(state, empty())

    def test_missing_windows_asset_does_not_hide_release(self):
        api = FakeAPI()
        api.releases[0]['assets'] = []
        _, files = discovery.discover(api, reviewed(), empty(), NOW)
        report = json.loads(next(v for k, v in files.items() if k.startswith('reports/') and k.endswith('.json')))
        self.assertFalse(report['windows_asset_available'])
        self.assertTrue(any('archive' in warning for warning in report['warnings']))

    def test_truncated_comparison_and_diverged_history_warn(self):
        api = FakeAPI()
        api.comparison['files'] *= 300
        api.comparison['status'] = 'diverged'
        report = discovery.assess_release(api, release(), NEW, reviewed(), NOW)
        self.assertFalse(report['changed_file_list_complete'])
        self.assertEqual(len(report['warnings']), 2)

    def test_missing_comparison_files_fails(self):
        api = FakeAPI()
        del api.comparison['files']
        with self.assertRaisesRegex(ValueError, 'changed-file'):
            discovery.assess_release(api, release(), NEW, reviewed(), NOW)

    def test_renamed_file_reports_both_feature_areas(self):
        api = FakeAPI()
        api.comparison['files'] = [{'filename': 'new/file.cpp', 'previous_filename': 'pcsx2/ps2/BiosTools.cpp', 'status': 'renamed'}]
        report = discovery.assess_release(api, release(), NEW, reviewed(), NOW)
        self.assertIn('BIOS / boot / disc handling', report['changed_files'][0]['areas'])

    def test_backlog_is_explicit_and_drains_next_run(self):
        api = FakeAPI([release('v2.9.130'), release('v2.9.129'), release('v2.9.128'), release('v2.9.127')])
        with patch.object(discovery, 'MAX_NEW_REPORTS', 2):
            summary, files = discovery.discover(api, reviewed(), empty(), NOW)
            self.assertEqual(summary['new_reports'], ['v2.9.130', 'v2.9.129'])
            self.assertEqual(summary['pending_reports'], 1)
            self.assertFalse(summary['discovery_complete'])
            second, _ = discovery.discover(api, reviewed(), json.loads(files['state.json']), NOW)
            self.assertEqual(second['new_reports'], ['v2.9.128'])
            self.assertTrue(second['discovery_complete'])

    def test_render_treats_upstream_names_as_data(self):
        api = FakeAPI()
        api.comparison['files'] = [{'filename': '<img src=x>|`@everyone\n::error::oops', 'status': 'modified'}]
        text = discovery.markdown(discovery.assess_release(api, release(), NEW, reviewed(), NOW))
        self.assertNotIn('<img', text)
        self.assertNotIn('@everyone', text)
        self.assertNotIn('\n::error::', text)

    def test_coverage_hints_include_build_input_and_settings(self):
        for name, expected in [('cmake/SearchForStuff.cmake', 'Build / dependencies'),
                               ('pcsx2/PAD/Host/SDLInputSource.cpp', 'Controller input / hotkeys'),
                               ('pcsx2-qt/Settings/BIOSSettingsWidget.cpp', 'Portable settings / launch / updater integration')]:
            self.assertIn(expected, discovery.areas(name))

    def test_existing_gate_pins_are_loaded_without_executing_build(self):
        baseline = discovery.baseline()
        self.assertRegex(baseline['commit'], r'^[0-9a-f]{40}$')
        self.assertEqual(len(baseline['integration_hashes']), 13)
        self.assertRegex(baseline['policy_fingerprint'], r'^[0-9a-f]{64}$')


class PublishingAPI:
    def __init__(self, head=None):
        self.head = head
        self.writes = []

    def get(self, path, **kwargs):
        if '/git/ref/heads/' in path:
            return {'object': {'sha': self.head}} if self.head else None
        if '/git/commits/' in path:
            return {'tree': {'sha': 'd' * 40}}
        raise AssertionError(path)

    def request(self, method, path, data):
        self.writes.append((method, path, data))
        return {'sha': 'e' * 40}


class PublishingTests(unittest.TestCase):
    def test_noop_makes_no_api_writes(self):
        api = PublishingAPI()
        self.assertIsNone(discovery.publish(api, 'AMT-Hub/pcsx2-custom', None, {}))
        self.assertEqual(api.writes, [])

    def test_new_branch_is_orphan_and_only_report_branch_is_written(self):
        api = PublishingAPI()
        discovery.publish(api, 'AMT-Hub/pcsx2-custom', None, {'README.md': 'report', 'state.json': '{}'})
        self.assertEqual(api.writes[1][2]['parents'], [])
        self.assertEqual(api.writes[2][2]['ref'], 'refs/heads/nightly-discovery-reports')
        self.assertNotIn('base_tree', api.writes[0][2])

    def test_existing_branch_preserves_tree_and_updates_without_force(self):
        api = PublishingAPI(BASE)
        discovery.publish(api, 'AMT-Hub/pcsx2-custom', BASE, {'state.json': '{}'})
        self.assertEqual(api.writes[0][2]['base_tree'], 'd' * 40)
        self.assertEqual(api.writes[1][2]['parents'], [BASE])
        self.assertIs(api.writes[2][2]['force'], False)
        self.assertTrue(api.writes[2][1].endswith('/heads/nightly-discovery-reports'))

    def test_concurrent_branch_change_is_rejected_before_writes(self):
        api = PublishingAPI(NEW)
        with self.assertRaisesRegex(RuntimeError, 'changed during discovery'):
            discovery.publish(api, 'AMT-Hub/pcsx2-custom', BASE, {'state.json': '{}'})
        self.assertEqual(api.writes, [])

    def test_reject_non_report_paths(self):
        for path in ('approved-feed.json', 'emulator/build.py', '../state.json', '.github/workflows/x.yml'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'destination'):
                discovery.publish(PublishingAPI(), 'AMT-Hub/pcsx2-custom', None, {path: 'bad'})

    def test_publish_failure_propagates(self):
        api = PublishingAPI()
        with patch.object(api, 'request', side_effect=RuntimeError('HTTP 403')):
            with self.assertRaisesRegex(RuntimeError, '403'):
                discovery.publish(api, 'AMT-Hub/pcsx2-custom', None, {'state.json': '{}'})


if __name__ == '__main__':
    unittest.main()
