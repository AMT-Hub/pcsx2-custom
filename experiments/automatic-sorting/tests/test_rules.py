import gzip
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rules import compile_defaults, normalise_title, retail


def disc(serial, title, date=None, region='NTSC-U', developer='Studio'):
    r = {'serial': serial, 'name': title, 'region': region}
    if date:
        r['facts'] = {'date': date, 'developer': developer}
    return r


class RuleTests(unittest.TestCase):
    def test_unlisted_numbered_series_does_not_need_catalogue_entries(self):
        records = [disc('TEST-1', 'Invented Adventure'), disc('TEST-2', 'Invented Adventure II')]
        out, reasons, _ = compile_defaults(records, {}, {})
        self.assertEqual(out, {'TEST-1': 'Invented Adventure 1', 'TEST-2': 'Invented Adventure 2'})
        self.assertEqual(reasons['TEST-1'], 'numbered-series-first')
        self.assertEqual(compile_defaults(list(reversed(records)), {}, {})[0], out)
        # A newly installed game is another lookup in this same compiled result;
        # compilation has no installed-folder argument and cannot renumber it.

    def test_release_order_uses_metadata_not_alphabet_or_input_order(self):
        records = [disc('TEST-A', 'Invented Saga - Alpha', '2005-01-01'),
                   disc('TEST-Z', 'Invented Saga - Zulu', '2002-01-01')]
        out, _, _ = compile_defaults(records, {}, {})
        self.assertEqual(out['TEST-Z'], 'Invented Saga 1 - Zulu')
        self.assertEqual(out['TEST-A'], 'Invented Saga 2 - Alpha')

    def test_cross_region_alias_is_one_game_not_an_extra_sequel(self):
        records = [disc('TEST-1', 'Made Up - Dawn', '2001-01-01'),
                   disc('TEST-2', 'Different Regional Name', '2002-01-01', 'PAL'),
                   disc('TEST-3', 'Made Up - Dusk', '2003-01-01')]
        policy = {'regional_aliases': {'Made Up - Dawn': ['Different Regional Name']},
                  'families': [{'id': 'made-up', 'prefix': 'Made Up', 'patterns': ['^Made Up']}]}
        out, _, _ = compile_defaults(records, policy, {})
        self.assertEqual(out['TEST-1'], out['TEST-2'])
        self.assertEqual(out['TEST-3'], 'Made Up 2')

    def test_unknown_regional_equivalence_is_not_guessed(self):
        records = [disc('TEST-1', 'Made Up - Dawn', '2001-01-01', 'PAL'),
                   disc('TEST-2', 'Made Up - Daybreak', '2002-01-01', 'NTSC-U')]
        out, _, missing = compile_defaults(records, {}, {})
        self.assertEqual(out['TEST-1'], records[0]['name'])
        self.assertTrue(missing)

    def test_missing_or_overlapping_dates_do_not_invent_order(self):
        records = [disc('TEST-1', 'Made Up - Dawn', '2001'), disc('TEST-2', 'Made Up - Dusk')]
        self.assertTrue(compile_defaults(records, {}, {})[2])
        records[1]['facts'] = {'date': '2001-10-01'}
        out, _, missing = compile_defaults(records, {}, {})
        self.assertEqual(out['TEST-1'], 'Made Up - Dawn')
        self.assertTrue(any('unique order' in m['reason'] for m in missing))

    def test_subtitle_inference_does_not_collide_with_numbered_series(self):
        records = [disc('TEST-1', 'Made Up 2'), disc('TEST-2', 'Made Up - Dawn', '2003-01-01'),
                   disc('TEST-3', 'Made Up - Dusk', '2005-01-01')]
        out, _, missing = compile_defaults(records, {}, {})
        self.assertEqual(out['TEST-2'], 'Made Up - Dawn')
        self.assertTrue(missing)

    def test_normalisation_is_not_arbitrary_digit_replacement(self):
        policy = json.loads((ROOT / 'rules.json').read_text())
        for before, after in [('God of War II', 'God of War 2'), ('Driv3r', 'Driver 3'),
                              ('Ico', 'Ico'), ('007 - Nightfire', '007 - Nightfire'),
                              ('Mega Man X', 'Mega Man X'), ('Guilty Gear XX', 'Guilty Gear XX'),
                              ('Hunter X Hunter', 'Hunter X Hunter'), ('Game XIV', 'Game 14')]:
            self.assertEqual(normalise_title(before, policy), after)

    def test_years_do_not_imply_an_unnumbered_first_game(self):
        out, _, _ = compile_defaults([disc('TEST-1', 'Sports'), disc('TEST-2', 'Sports 2005')], {}, {})
        self.assertEqual(out['TEST-1'], 'Sports')

    def test_single_subtitled_first_game_with_numbered_sequel(self):
        records = [disc('TEST-1', 'New Series - Beginning'), disc('TEST-2', 'New Series II - Return')]
        out, _, _ = compile_defaults(records, {}, {})
        self.assertEqual(out['TEST-1'], 'New Series 1 - Beginning')
        records.append(disc('TEST-3', 'New Series - Side Story'))
        out, _, _ = compile_defaults(records, {}, {})
        self.assertEqual(out['TEST-1'], 'New Series - Beginning')

    def test_demo_filter_preserves_demolition(self):
        self.assertTrue(retail('SLUS-20001', 'Demolition Racer'))
        self.assertFalse(retail('SLUS-28001', 'Retail Name'))
        self.assertFalse(retail('TEST-1', 'Retail Name [Demo]'))

    def test_ampersand_is_not_assumed_to_be_a_compilation(self):
        policy = {'families': [{'id': 's', 'prefix': 'Series', 'patterns': ['^Series']}]}
        out, _, _ = compile_defaults([disc('TEST-1', 'Series - Hit & Run', '2003')], policy, {})
        self.assertEqual(out['TEST-1'], 'Series 1')

    def test_user_exceptions_win_and_input_metadata_is_not_mutated(self):
        records = [disc('TEST-1', 'Game II')]
        original = json.dumps(records)
        out, reason, _ = compile_defaults(records, {}, {'TEST-1': 'Personal 9'})
        self.assertEqual(out['TEST-1'], 'Personal 9')
        self.assertEqual(reason['TEST-1'], 'user-exception')
        self.assertEqual(json.dumps(records), original)

    def test_duplicate_identity_rejected(self):
        with self.assertRaises(ValueError):
            compile_defaults([disc('TEST-1', 'One'), disc('TEST-1', 'Two')], {}, {})


if __name__ == '__main__':
    unittest.main()
