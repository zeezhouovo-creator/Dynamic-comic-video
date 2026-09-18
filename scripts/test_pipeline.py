"""Behavioral regression checks; temporary copies never alter source fixtures."""
import shutil
import tempfile
import unittest
from pathlib import Path
from pipeline import ROOT, read, save, validate

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.project=Path(self.temp.name)/'project'
        shutil.copytree(ROOT/'examples/library',self.project)
    def tearDown(self): self.temp.cleanup()
    def edit(self,name,change):
        p=self.project/(name+'.json'); data=read(p); change(data); save(p,data)
    def test_valid_fixture(self): self.assertEqual(validate(self.project,True)[1],[])
    def test_gap(self):
        self.edit('motion_plan',lambda d:d['shots'][1].update(start_frame=49))
        self.assertTrue(any('gap/overlap' in x for x in validate(self.project)[1]))
    def test_unknown_character(self):
        self.edit('storyboard',lambda d:d['shots'][0]['characters'][0].update(character_id='unknown'))
        self.assertTrue(any('Unknown character' in x for x in validate(self.project)[1]))
    def test_unreviewed_production(self):
        self.edit('motion_plan',lambda d:d.update(asset_mode='production'))
        self.assertTrue(any('review incomplete' in x for x in validate(self.project)[1]))
    def test_repetition_report(self):
        def repeat(d):
            for s in d['shots']:
                s.update(shot_size='wide',angle='eye_level',composition_tag='center')
                s['characters'][0]['pose_tag']='standing'
        self.edit('storyboard',repeat)
        self.assertEqual({w['check'] for w in validate(self.project)[2]},{'pose','shot_size','angle','composition_tag'})
    def test_reused_cutout(self):
        shutil.copy2(self.project/'shots/shot_001/layers/lin.png',self.project/'shots/shot_002/layers/lin.png')
        self.assertTrue(any('Reused character cutout' in x for x in validate(self.project,True)[1]))
    def test_out_of_bounds(self):
        self.edit('motion_plan',lambda d:d['shots'][0]['layers'][0]['to'].update(x=900))
        self.assertTrue(any('reveal canvas edge' in x for x in validate(self.project)[1]))
    def test_path_escape(self):
        self.edit('motion_plan',lambda d:d['shots'][0]['layers'][0].update(asset='../secret.png'))
        self.assertTrue(validate(self.project)[1])

if __name__=='__main__': unittest.main()
