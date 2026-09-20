"""Synthetic joint/pose fixture, with a fixed camera and no user content."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
from pipeline import ROOT, read, save

def build(root):
    root=Path(root)
    for name in ('production_brief','characters','storyboard','motion_plan'):
        d=read(ROOT/'examples/library'/(name+'.json'))
        if name=='motion_plan':
            d['version']='0.2'
            for s in d['shots']:
                s['performance']={'intent':'Robot raises arm and blinks with camera fixed','reviewed':False}
                s['layers']=[s['layers'][0]]
                for lid,z,part in [('body',10,'whole'),('arm',20,'arm'),('eyes',30,'eyes')]:
                    base=f"shots/{s['shot_id']}/layers/"
                    layer={'layer_id':lid,'asset':base+lid+'.png','z':z,'from':{'x':0,'y':0,'scale':1},'to':{'x':0,'y':0,'scale':1}}
                    if part!='whole':
                        layer['acting']={'part':part,'pivot':[.5,.5],'keys':[{'frame':f,'x':0,'y':0,'rotation':r if part=='arm' else 0,'opacity':1} for f,r in [(0,0),(12,-60),(28,-60),(47,0)]]}
                        if part=='eyes': layer['acting']['poses']=[{'frame':0,'asset':base+'eyes.png'},{'frame':20,'asset':base+'blink.png'},{'frame':25,'asset':base+'eyes.png'}]
                    s['layers'].append(layer)
                s['layers'][0]['from']=s['layers'][0]['to']={'x':0,'y':0,'scale':1}
        elif name=='storyboard':
            for s in d['shots']:
                s['layers']=[s['layers'][0]]+[{'id':lid,'role':'character','character_id':'lin','elements':'Synthetic robot '+lid,'method':'extract','reason':'Joint animation test'} for lid in ('body','arm','eyes')]
        save(root/(name+'.json'),d)
    for i in range(1,4):
        folder=root/f'shots/shot_{i:03d}'; (folder/'layers').mkdir(parents=True,exist_ok=True)
        bg=Image.new('RGBA',(960,540),'#efeadb'); bg.save(folder/'layers/bg.png')
        body=Image.new('RGBA',bg.size); p=ImageDraw.Draw(body)
        p.rounded_rectangle((330,120,480,400),30,fill=['#568883','#6388ab','#947db2'][i-1])
        arm=Image.new('RGBA',bg.size); p=ImageDraw.Draw(arm); p.rounded_rectangle((465,255,630,285),15,fill='#edac58')
        eyes=Image.new('RGBA',bg.size); p=ImageDraw.Draw(eyes); p.ellipse((365,160,380,180),fill='#172332'); p.ellipse((425,160,440,180),fill='#172332')
        blink=Image.new('RGBA',bg.size); p=ImageDraw.Draw(blink); p.line((365,170,380,170),fill='#172332',width=4); p.line((425,170,440,170),fill='#172332',width=4)
        # Slight per-shot position variation makes fixture sprites distinct.
        for name,img in [('body',body),('arm',arm),('eyes',eyes),('blink',blink)]:
            if i>1:
                shifted=Image.new('RGBA',bg.size); shifted.alpha_composite(img,(0,i-1)); img=shifted
            img.save(folder/f'layers/{name}.png')
        for name in ('body','arm','eyes'):
            with Image.open(folder/f'layers/{name}.png') as img:
                bg=Image.alpha_composite(bg,img)
        bg.save(folder/'master.png')
    return root

if __name__=='__main__':
    target=Path(sys.argv[1])
    if target.exists(): raise SystemExit('Use a new output directory')
    print(build(target))
