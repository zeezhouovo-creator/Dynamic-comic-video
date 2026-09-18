"""Generate explicitly synthetic, local geometry fixtures; never production artwork."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw
from pipeline import read

p=argparse.ArgumentParser(); p.add_argument('project',type=Path); a=p.parse_args()
brief=read(a.project/'production_brief.json'); board=read(a.project/'storyboard.json')
if read(a.project/'motion_plan.json')['asset_mode']!='fixture': raise SystemExit('Refusing to overwrite production assets')
w,h=brief['format']['width'],brief['format']['height']
for i,shot in enumerate(board['shots']):
    folder=a.project/'shots'/shot['id']; (folder/'layers').mkdir(parents=True,exist_ok=True)
    bg=Image.new('RGBA',(w,h),'#b3c1be'); d=ImageDraw.Draw(bg)
    d.rectangle((0,0,w,h*.68),fill='#637879')
    for x in range(35,w,95):
        d.rectangle((x,50,x+62,h*.65),fill='#344c52',outline='#273940',width=4)
        for y in range(90,int(h*.6),70): d.line((x,y,x+62,y),fill='#cca97a',width=7)
    d.rectangle((w*.60,25,w*.92,h*.58),fill='#c6dcd7',outline='#263f46',width=12)
    d.line((w*.76,25,w*.76,h*.58),fill='#263f46',width=8)
    bg.save(folder/'layers/bg.png')
    char=Image.new('RGBA',(w,h)); d=ImageDraw.Draw(char)
    cx=[int(w*.36),int(w*.51),int(w*.67)][i%3]; cy=[int(h*.39),int(h*.33),int(h*.32)][i%3]; r=[45,60,82][i%3]
    d.polygon([(cx-r,cy+r),(cx+r,cy+r),(cx+r*1.5,h),(cx-r*1.5,h)],fill='#d9cead',outline='#26343a',width=5)
    d.polygon([(cx-r*.6,cy+r*1.6),(cx+r*.6,cy+r*1.6),(cx+r,h),(cx-r,h)],fill='#354c67')
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill='#e3bfa2',outline='#29383d',width=5)
    d.pieslice((cx-r-8,cy-r-16,cx+r+8,cy+r),180,360,fill='#26343a')
    d.line((cx-r*.35,cy,cx-r*.12,cy),fill='#26343a',width=4)
    d.line((cx+r*.12,cy,cx+r*.35,cy),fill='#26343a',width=4)
    if i==0: d.line((cx+r,cy+r*1.6,cx+170,cy+130),fill='#e3bfa2',width=24)
    elif i==1: d.line((cx+r,cy+r*1.6,cx+140,cy+45),fill='#e3bfa2',width=24)
    else: d.line((cx-r,cy+r*1.7,cx-115,cy+95),fill='#e3bfa2',width=24)
    if i: d.rectangle((cx-120 if i==2 else cx+110,cy+60,cx-55 if i==2 else cx+180,cy+125),fill='#f3e7c8',outline='#715e49',width=3)
    char.save(folder/'layers/lin.png')
    fg=Image.new('RGBA',(w,h)); d=ImageDraw.Draw(fg)
    d.polygon([(0,h*.85),(w,h*.91),(w,h),(0,h)],fill='#4e4340')
    d.rectangle((40,h*.78,230,h*.88),fill='#a57455',outline='#312e31',width=5)
    fg.save(folder/'layers/fg.png')
    master=Image.alpha_composite(Image.alpha_composite(bg,char),fg)
    master.convert('RGB').save(folder/'master.png'); master.save(folder/'preview.png')
print('Created local synthetic fixtures, not generated manga or segmentation results.')
