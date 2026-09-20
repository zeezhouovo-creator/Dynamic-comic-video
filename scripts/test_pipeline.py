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
        self.assertTrue(any('review incomplete' in x for x in validate(self.project,True)[1]))
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

class ActingTests(PipelineTests):
    def setUp(self):
        from make_acting_fixture import build
        self.temp=tempfile.TemporaryDirectory()
        self.project=build(Path(self.temp.name)/'project')
    # Keep legacy fixture-specific checks in PipelineTests.
    def test_reused_cutout(self):
        shutil.copy2(self.project/'shots/shot_001/layers/arm.png',self.project/'shots/shot_002/layers/arm.png')
        self.assertTrue(any('Reused character cutout' in x for x in validate(self.project,True)[1]))
    def test_missing_performance(self):
        self.edit('motion_plan',lambda d:d['shots'][0].pop('performance'))
        self.assertTrue(any('Missing performance' in x for x in validate(self.project)[1]))
    def test_camera_only(self):
        self.edit('motion_plan',lambda d:[l.pop('acting',None) for l in d['shots'][0]['layers']])
        self.assertTrue(any('Camera-only' in x for x in validate(self.project)[1]))
        self.edit('motion_plan',lambda d:d['shots'][0]['performance'].update(static_reason='Pause for reading'))
        self.assertEqual(validate(self.project)[1],[])
    def test_invalid_key_time(self):
        self.edit('motion_plan',lambda d:d['shots'][0]['layers'][2]['acting']['keys'][-1].update(frame=48))
        self.assertTrue(any('Invalid acting frames' in x for x in validate(self.project)[1]))
    def test_missing_pose_asset(self):
        (self.project/'shots/shot_001/layers/blink.png').unlink()
        self.assertTrue(validate(self.project,True)[1])
    def test_sequential_requires_dialogue(self):
        self.edit('storyboard',lambda d:d['shots'][0].pop('dialogue'))
        self.assertTrue(any('requires dialogue' in x for x in validate(self.project)[1]))
    def test_dialogue_cannot_cross_cut(self):
        self.edit('storyboard',lambda d:d['shots'][0]['dialogue'][0].update(end_frame=49))
        self.assertTrue(any('Invalid dialogue timing' in x for x in validate(self.project)[1]))
    def test_dialogue_cannot_overlap(self):
        self.edit('storyboard',lambda d:d['shots'][0]['dialogue'].append({'speaker':'lin','text':'Overlap','start_frame':20,'end_frame':30}))
        self.assertTrue(any('Invalid dialogue timing' in x for x in validate(self.project)[1]))
    def test_sequential_rejects_camera_move(self):
        self.edit('motion_plan',lambda d:d['shots'][0]['layers'][0]['to'].update(scale=1.05))
        self.assertTrue(any('identity layer framing' in x for x in validate(self.project)[1]))
    def test_compiled_panel_review(self):
        from pipeline import compile_prompts
        data,errors,_=validate(self.project)
        self.assertEqual(errors,[])
        compile_prompts(self.project,data)
        self.assertTrue((self.project/'storyboard_review.md').is_file())
        prompt=read(self.project/'prompts/shot_001_acting.json')
        self.assertEqual(prompt['dialogue'],data['storyboard']['shots'][0]['dialogue'])
    def test_fixed_camera_micro(self):
        def micro(d):
            for s in d['shots']:
                s['performance']['mode']='fixed-camera-micro'
                for l in s['layers']:
                    for k in l.get('acting',{}).get('keys',[]):
                        k['rotation']=k['rotation']/60
        self.edit('motion_plan',micro)
        self.assertEqual(validate(self.project,True)[1],[])
        self.edit('motion_plan',lambda d:d['shots'][0]['layers'][0]['to'].update(scale=1.05))
        self.assertTrue(any('identity layer framing' in x for x in validate(self.project)[1]))
    def test_micro_rejects_large_action(self):
        self.edit('motion_plan',lambda d:d['shots'][0]['performance'].update(mode='fixed-camera-micro'))
        self.assertTrue(any('exceeds 2 degrees' in x for x in validate(self.project)[1]))
    def test_micro_rejects_background_acting(self):
        def background(d):
            s=d['shots'][0]
            s['performance']['mode']='fixed-camera-micro'
            import copy
            s['layers'][0]['acting']=copy.deepcopy(s['layers'][2]['acting'])
        self.edit('motion_plan',background)
        self.assertTrue(any('background must remain unchanged' in x for x in validate(self.project)[1]))

if __name__=='__main__': unittest.main()
