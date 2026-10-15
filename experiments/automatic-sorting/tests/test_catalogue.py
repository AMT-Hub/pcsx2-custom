import configparser
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('catalogue', ROOT / 'generate_catalogue.py')
catalogue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalogue)


class CatalogueTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'catalogue.json').read_text(encoding='utf-8'))
        self.ini = configparser.ConfigParser(interpolation=None)
        self.ini.read(ROOT / 'automatic-sorting.ini', encoding='utf-8')

    def test_all_reviewed_records_compile_exactly(self):
        serials = {}
        for game in self.data['games']:
            self.assertTrue(game['identities'])
            for identity in game['identities']:
                serial = identity['serial']
                self.assertNotIn(serial, serials)
                serials[serial] = game['sorting_title']
                self.assertEqual(self.ini[serial]['SortingTitle'], game['sorting_title'])
        self.assertEqual(set(serials), set(self.ini.sections()))

    def test_gadget_racers_regional_ambiguity(self):
        self.assertEqual(self.ini['SLUS-20225']['SortingTitle'], 'Choro Q HG 1')
        self.assertEqual(self.ini['SLES-51911']['SortingTitle'], 'Choro Q HG 3')

    def test_deadlocked_gladiator_same_order(self):
        titles = {i['name']: self.ini[i['serial']]['SortingTitle']
                  for g in self.data['games'] for i in g['identities']}
        self.assertEqual(titles['Ratchet - Deadlocked'], 'Ratchet & Clank 4')
        self.assertEqual(titles['Ratchet - Gladiator'], 'Ratchet & Clank 4')

    def test_monster_hunter_japanese_serial(self):
        self.assertEqual(self.ini['SLPM-66280']['SortingTitle'], 'Monster Hunter 2')

    def test_screenshot_quidditch_not_silently_renumbered(self):
        game = next(g for g in self.data['games'] if g['id'] == 'harry-potter-quidditch')
        self.assertEqual(game['sorting_title'], 'Harry Potter 4')

    def test_no_fuzzy_or_roman_token_guessing(self):
        seed = {'games':[{'id':'ico', 'aliases':['Ico'], 'sorting_title':'Team ICO 1'}]}
        _, result = catalogue.generate(seed, {'SCUS-97113':{'name':'Ico'},
             'TEST-1':{'name':'Ico [Demo]'}, 'TEST-2':{'name':'Ico 2'},
             'TEST-3':{'name':'Ico & Another Game'}, 'TEST-4':{'name':'Ico [Beta]'}})
        self.assertEqual(result, {'SCUS-97113':'Team ICO 1'})

    def test_conflicting_identity_rejected(self):
        seed = {'games':[{'id':'a','aliases':['A'],'sorting_title':'A 1'},
                         {'id':'b','aliases':['B'],'sorting_title':'B 1'}]}
        with self.assertRaises(ValueError):
            catalogue.generate(seed, {'TEST-1':{'name':'A','name-en':'B'}})

    def test_unknown_explicit_serial_rejected(self):
        seed = {'games':[{'id':'a','aliases':['A'],'sorting_title':'A 1','serials':['MISSING-1']}]}
        with self.assertRaises(ValueError):
            catalogue.generate(seed, {'TEST-1':{'name':'A'}})


if __name__ == '__main__':
    unittest.main()
