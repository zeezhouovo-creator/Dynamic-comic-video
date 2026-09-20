"""Public V0.3 audio/mouth fixture; synthetic test tone, not voice acting."""
import math
import struct
import sys
import wave
from pathlib import Path
from PIL import Image,ImageDraw
from make_acting_fixture import build
from pipeline import read,save

def build_dialogue(root):
    root=build(root); board=read(root/'storyboard.json'); motion=read(root/'motion_plan.json')
    board['scenes']=[{'id':'test-room','space':'Synthetic robot test room; schematic backgrounds only','time':'day','lighting':'flat test lighting','anchors':['left window','right shelf']}]
    (root/'audio').mkdir(exist_ok=True)
    with wave.open(str(root/'audio/tone.wav'),'wb') as w:
        w.setparams((1,2,24000,0,'NONE','not compressed'))
        w.writeframes(b''.join(struct.pack('<h',int(4500*math.sin(i*math.tau*220/24000)) if i%12000<8000 else 0) for i in range(36000)))
    motion['version']='0.3'
    for i,(s,m) in enumerate(zip(board['shots'],motion['shots'])):
        s['source_panel']=f'panel_{i+1:02d}'
        s['direction']={'scene_id':'test-room','camera_position':['front','window side','shelf side'][i],
            'background_view':['window and shelf','window detail','shelf detail'][i],'view_id':f'view_{i}',
            'incoming_state':'Robot receives the cue','outgoing_state':'Robot finishes the test gesture',
            'micro_actions':'Raise arm, blink and speak to the audio pulse',
            'cut_reason':'Move to the next test response','next_shot_id':board['shots'][i+1]['id'] if i<2 else None,
            'handoff':'Gesture completes before next independent panel','reaction_hold_frames':6,'listening_reactions':[]}
        bg=Image.new('RGBA',(960,540),'#efeadb'); draw=ImageDraw.Draw(bg)
        if i==0:
            draw.rectangle((30,40,200,300),outline='#84979b',width=8); draw.rectangle((730,60,920,400),outline='#b09570',width=8)
        elif i==1:
            draw.rectangle((30,20,280,440),outline='#84979b',width=8); draw.line((155,20,155,440),fill='#84979b',width=6)
        else:
            draw.rectangle((680,20,930,440),outline='#b09570',width=8)
            for y in (120,240,360): draw.line((680,y,930,y),fill='#b09570',width=6)
        bg.save(root/f"shots/{s['id']}/layers/bg.png")
        s['dialogue']=[{'speaker':'lin','text':'Synthetic audio / mouth test','start_frame':6,'end_frame':42,'audio':'audio/tone.wav','timing_source':'audio'}]
        s['layers'].append({'id':'mouth','role':'character','character_id':'lin','elements':'Synthetic mouth','method':'extract','reason':'Speech timing test'})
        folder=f"shots/{s['id']}/layers/"
        for state in ('closed','open'):
            img=Image.new('RGBA',(960,540)); p=ImageDraw.Draw(img)
            p.ellipse((392,203+i,420,219+i if state=='open' else 207+i),fill='#172332')
            img.save(root/(folder+'mouth_'+state+'.png'))
        m['layers'].append({'layer_id':'mouth','asset':folder+'mouth_closed.png','z':40,'from':{'x':0,'y':0,'scale':1},'to':{'x':0,'y':0,'scale':1},'acting':{'part':'mouth','pivot':[.5,.5],'keys':[{'frame':f,'x':0,'y':0,'rotation':0,'opacity':1} for f in (0,47)],'speech':{'speaker':'lin','closed_asset':folder+'mouth_closed.png','open_asset':folder+'mouth_open.png'}}})
        for name in ('body','arm','eyes','mouth_closed'):
            with Image.open(root/(folder+name+'.png')) as im: bg=Image.alpha_composite(bg,im)
        bg.save(root/f"shots/{s['id']}/master.png")
    save(root/'storyboard.json',board); save(root/'motion_plan.json',motion)
    return root

if __name__=='__main__':
    target=Path(sys.argv[1])
    if target.exists(): raise SystemExit('Use a new output directory')
    print(build_dialogue(target))
