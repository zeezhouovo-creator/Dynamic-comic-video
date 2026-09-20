"""Behavior tests for measured dialogue, incremental work and patch bounds."""
import copy
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from make_dialogue_fixture import build_dialogue as build
from pipeline import read,save,validate,local,compile_prompts
from production import inventory,render_payload,wav_timing

class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=build(Path(self.temp.name)/'project')
        path=self.root/'audio/test.wav'; path.parent.mkdir(exist_ok=True)
        with wave.open(str(path),'wb') as w:
            w.setparams((1,2,24000,0,'NONE','not compressed'))
            w.writeframes(b''.join(struct.pack('<h',int(9000*math.sin(i*.1)) if 6000<=i<18000 else 0) for i in range(24000)))
        board=read(self.root/'storyboard.json')
        for shot in board['shots']:
            shot['dialogue']=[{'speaker':'lin','text':'Test','start_frame':6,'end_frame':30,'audio':'audio/test.wav','timing_source':'audio'}]
            shot['direction']['reaction_hold_frames']=18
        save(self.root/'storyboard.json',board)
        motion=read(self.root/'motion_plan.json'); motion['version']='0.3'; save(self.root/'motion_plan.json',motion)
    def tearDown(self): self.temp.cleanup()
    def test_audio_silence_closes_mouth(self):
        frames,activity=wav_timing(self.root/'audio/test.wav',24)
        self.assertEqual(frames,24)
        self.assertTrue(activity)
        self.assertTrue(all(6<=f<18 for f in activity))
    def test_measured_timing_rejects_wrong_duration(self):
        board=read(self.root/'storyboard.json'); board['shots'][0]['dialogue'][0]['end_frame']=40
        save(self.root/'storyboard.json',board)
        self.assertTrue(any('Audio/dialogue duration mismatch' in e for e in validate(self.root,True)[1]))
    def test_single_shot_payload_rebases_audio_and_duration(self):
        data,errors,_=validate(self.root,True); self.assertEqual(errors,[])
        payload=render_payload(self.root,data,local,'shot_002')
        self.assertEqual(len(payload['shots']),1)
        self.assertEqual(payload['shots'][0]['start_frame'],0)
        self.assertEqual(payload['format']['duration_frames'],48)
        self.assertEqual(payload['shots'][0]['dialogue'][0]['start_frame'],6)
    def test_missing_report_and_incremental_fingerprints(self):
        data,_,_=validate(self.root)
        report=inventory(self.root,data,local); save(self.root/'asset_report.json',report)
        self.assertTrue(all(not s['changed'] for s in inventory(self.root,data,local)['shots']))
        (self.root/'shots/shot_002/layers/blink.png').unlink()
        report=inventory(self.root,data,local)
        self.assertEqual([s['shot_id'] for s in report['shots'] if s['changed']],['shot_002'])
        self.assertIn('shots/shot_002/layers/blink.png',report['shots'][1]['missing'])
    def test_partial_compile_preserves_other_prompts(self):
        data,_,_=validate(self.root); compile_prompts(self.root,data)
        path=self.root/'prompts/shot_001.json'; before=path.stat().st_mtime_ns
        compile_prompts(self.root,data,'shot_002')
        self.assertEqual(path.stat().st_mtime_ns,before)
    def test_selected_shot_does_not_require_other_assets(self):
        (self.root/'shots/shot_003/layers/blink.png').unlink()
        self.assertEqual(validate(self.root,True,'shot_002')[1],[])
        self.assertTrue(validate(self.root,True)[1])
    def test_speech_driver_requires_present_speaker(self):
        motion=read(self.root/'motion_plan.json')
        a=motion['shots'][0]['layers'][3]['acting']; a['part']='mouth'
        a['speech']={'speaker':'missing','closed_asset':'shots/shot_001/layers/eyes.png','open_asset':'shots/shot_001/layers/blink.png'}
        save(self.root/'motion_plan.json',motion)
        self.assertTrue(any('no visible speaking character' in e for e in validate(self.root)[1]))
    def test_patch_outside_canvas_rejected(self):
        motion=read(self.root/'motion_plan.json'); motion['shots'][0]['layers'][2]['region']=[.9,0,.2,.1]
        save(self.root/'motion_plan.json',motion)
        self.assertTrue(any('Invalid local patch region' in e for e in validate(self.root)[1]))
    def test_scene_reference_and_handoff_checked(self):
        board=read(self.root/'storyboard.json')
        board['shots'][0]['direction'].update(scene_id='missing',next_shot_id='shot_003')
        save(self.root/'storyboard.json',board)
        errors=validate(self.root)[1]
        self.assertTrue(any('Unknown scene' in e for e in errors))
        self.assertTrue(any('continuity link mismatch' in e for e in errors))
    def test_visible_listener_needs_reaction(self):
        board=read(self.root/'storyboard.json'); board['shots'][0]['dialogue'][0]['speaker']='offscreen'
        save(self.root/'storyboard.json',board)
        self.assertTrue(any('Missing visible listener reaction' in e for e in validate(self.root)[1]))
    def test_reused_background_rejected(self):
        import shutil
        shutil.copy2(self.root/'shots/shot_001/layers/bg.png',self.root/'shots/shot_002/layers/bg.png')
        self.assertTrue(any('Mechanically reused background' in e for e in validate(self.root,True)[1]))
    def test_required_direction_not_just_prompt_advice(self):
        board=read(self.root/'storyboard.json'); board['shots'][0].pop('direction')
        save(self.root/'storyboard.json',board)
        self.assertTrue(any('Missing independent shot direction' in e for e in validate(self.root)[1]))

if __name__=='__main__': unittest.main()
