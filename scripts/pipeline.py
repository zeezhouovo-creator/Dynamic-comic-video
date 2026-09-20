"""Local-only V0.1 contract validation, prompt compiler and renderer preparation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from jsonschema import Draft202012Validator
from PIL import Image
from acting import asset_names, check_acting
from production import inventory, check_dialogue, render_payload, check_direction

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('production_brief', 'characters', 'storyboard', 'motion_plan')

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def local(root, name):
    p = (root/name).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError('Asset escapes project: '+name)
    return p

def validate(project, assets=False, shot_id=None):
    data = {n:read(project/(n+'.json')) for n in NAMES}
    errors, warnings = [], []
    for n, d in data.items():
        schema = read(ROOT/'schemas'/(n+'.schema.json'))
        Draft202012Validator.check_schema(schema)
        for e in Draft202012Validator(schema).iter_errors(d):
            errors.append(f'{n}:{list(e.path)}: {e.message}')
    if errors:
        return data, errors, warnings
    brief, chars, board, motion = (data[n] for n in NAMES)
    if len({d['project_id'] for d in data.values()}) != 1:
        errors.append('project_id mismatch')
    def unique(items, key, label):
        ids=[s[key] for s in items]
        if len(ids)!=len(set(ids)): errors.append('Duplicate '+label)
        return set(ids)
    cids=unique(chars['characters'],'id','character id')
    bids=unique(board['beats'],'id','beat id')
    sids=unique(board['shots'],'id','shot id')
    mids=unique(motion['shots'],'shot_id','motion shot id')
    if shot_id and shot_id not in sids: errors.append('Unknown selected shot '+shot_id)
    if sids!=mids: errors.append('Storyboard/motion shot set mismatch')
    if [s['id'] for s in board['shots']]!=[s['shot_id'] for s in motion['shots']]: errors.append('Storyboard/motion order mismatch')
    for b in board['beats']:
        if b['source_excerpt'] not in brief['original_content']: errors.append('Beat source is not an original-content excerpt: '+b['id'])
    if bids!={s['beat_id'] for s in board['shots']}: errors.append('Uncovered or unknown narrative beat')
    previous={}; previous_shots=[]
    for shot in board['shots']:
        sid=shot['id']
        if shot['beat_id'] not in bids: errors.append('Unknown beat '+sid)
        layerids=unique(shot['layers'],'id',sid+' layer id')
        present=unique(shot['characters'],'character_id',sid+' performance')
        if not present<=cids: errors.append('Unknown character '+sid)
        if sum(l['role'] in ('background','panel_base') for l in shot['layers'])!=1: errors.append('Need exactly one completed background or static panel base '+sid)
        layerchars={l.get('character_id') for l in shot['layers'] if l['role']=='character' and l.get('character_id')}
        # A deliberate group cutout may contain several named characters. Infer its
        # membership from the declared elements text when no single character_id exists.
        for layer in shot['layers']:
            if layer['role']=='character' and not layer.get('character_id'):
                for character in chars['characters']:
                    if character['name'] in layer.get('elements',''):
                        layerchars.add(character['id'])
        if layerchars!=present: errors.append('Character layer/performance mismatch '+sid)
        for char in shot['characters']:
            cid=char['character_id']; old=previous.get(cid)
            if old and old['pose_tag']==char['pose_tag']:
                warnings.append({'shot':sid,'check':'pose','message':'Same pose as previous appearance','exception':shot['repetition_exception']})
            previous[cid]=char
        previous_shots.append(shot)
        if len(previous_shots)>=3:
            for key in ('shot_size','angle','composition_tag'):
                if len({s[key] for s in previous_shots[-3:]})==1:
                    warnings.append({'shot':sid,'check':key,'message':'Three consecutive identical tags','exception':shot['repetition_exception']})
    direction_errors,direction_warnings=check_direction(data)
    errors.extend(direction_errors); warnings.extend(direction_warnings)
    cursor=0; hashes={}; backgrounds={}
    for item in motion['shots']:
        sid=item['shot_id']; shot=next((s for s in board['shots'] if s['id']==sid),None)
        if item['start_frame']!=cursor: errors.append('Timeline gap/overlap '+sid)
        cursor+=item['duration_frames']
        if not shot: continue
        if item['duration_frames']!=shot['duration_frames']: errors.append('Duration mismatch '+sid)
        sequential=(item.get('performance') or {}).get('mode')=='sequential-comic'
        if motion['version']=='0.3' and (item.get('performance') or {}).get('mode') not in ('sequential-comic','fixed-camera-micro'):
            errors.append('V0.3 requires a fixed comic performance mode '+sid)
        if sequential and ('dialogue' not in shot or shot.get('transition')!='cut'):
            errors.append('Sequential comic requires dialogue (empty for silent shots) and cut transition '+sid)
        caption_end=0
        for cue in shot.get('dialogue',[]):
            if cue['start_frame']<caption_end or not cue['start_frame']<cue['end_frame']<=shot['duration_frames']:
                errors.append('Invalid dialogue timing '+sid)
            caption_end=cue['end_frame']
        lids=unique(item['layers'],'layer_id',sid+' motion layer')
        if lids!={l['id'] for l in shot['layers']}: errors.append('Layer set mismatch '+sid)
        unique(item['layers'],'z',sid+' z order')
        roles={l['id']:l['role'] for l in shot['layers']}
        selected=not shot_id or sid==shot_id
        if motion['version'] in ('0.2','0.3'):
            errors.extend(check_acting(item,motion['asset_mode']=='production',assets and selected,roles))
        elif assets and motion['asset_mode']=='production':
            errors.append('Legacy 0.1 is parallax-only; migrate motion_plan to 0.2 for production '+sid)
        bgz=[l['z'] for l in item['layers'] if roles.get(l['layer_id']) in ('background','panel_base')]
        if bgz and bgz[0]!=min(l['z'] for l in item['layers']): errors.append('Background must be bottom layer '+sid)
        if assets and selected and motion['asset_mode']=='production' and not all(item['review'][k] for k in ('master_alignment','background_completed','motion_bounds_checked')): errors.append('Production visual review incomplete '+sid)
        width,height=brief['format']['width'],brief['format']['height']
        for layer in item['layers']:
            if roles.get(layer['layer_id'])=='panel_base' and (layer['asset']!=shot['master'] or layer.get('region') or layer.get('acting')):
                errors.append('Panel base must be the unchanged original master '+sid)
            if 'region' in layer:
                x,y,w,h=layer['region']
                if w<=0 or h<=0 or x+w>1 or y+h>1: errors.append('Invalid local patch region '+sid)
            if any(r=='panel_base' for r in roles.values()):
                a=layer.get('acting',{})
                if a and (not layer.get('region') or any(k['x'] or k['y'] or k['rotation'] or k['opacity']!=1 for k in a['keys'])):
                    errors.append('Panel patch requires fixed local replacement region '+sid)
            for t in (layer['from'],layer['to']):
                if abs(t['x'])>(t['scale']-1)*width/2+1e-6 or abs(t['y'])>(t['scale']-1)*height/2+1e-6: errors.append('Motion can reveal canvas edge '+sid+'/'+layer['layer_id'])
        if assets and selected:
            for name,role in [(shot['master'],'master')]+[(name,roles.get(l['layer_id'])) for l in item['layers'] for name in asset_names(l)]:
                p=local(project,name)
                if not p.is_file(): errors.append('Missing asset '+name); continue
                try:
                    with Image.open(p) as im:
                        if im.size!=(width,height): errors.append('Canvas size mismatch '+name)
                        alpha=im.convert('RGBA').getchannel('A').getextrema()
                        if role in ('background','panel_base','master') and alpha!=(255,255): errors.append('Opaque image required '+name)
                        patch=any(l.get('region') and name in asset_names(l) for l in item['layers'])
                        if role in ('character','foreground','effects') and not patch and (alpha[0]==255 or alpha[1]==0): errors.append('Nonempty transparent layer required '+name)
                except Exception as e: errors.append('Invalid image '+name+': '+str(e))
                if role=='character':
                    digest=hashlib.sha256(p.read_bytes()).hexdigest()
                    if digest in hashes and hashes[digest]!=(sid,name): errors.append('Reused character cutout: '+name+' and '+hashes[digest][1])
                    hashes[digest]=(sid,name)
                if role=='background' and motion['version']=='0.3':
                    digest=hashlib.sha256(p.read_bytes()).hexdigest()
                    if digest in backgrounds: errors.append('Mechanically reused background asset: '+sid+' and '+backgrounds[digest])
                    backgrounds[digest]=sid
    if cursor!=brief['format']['duration_frames']: errors.append('Total duration mismatch')
    if brief['format']['width']%2 or brief['format']['height']%2: errors.append('H264 dimensions must be even')
    if assets and motion['asset_mode']=='production':
        for char in chars['characters']:
            if shot_id and char['id'] not in {c['character_id'] for s in board['shots'] if s['id']==shot_id for c in s['characters']}: continue
            if char['reference']['status']!='ready' or not local(project,char['reference']['image']).is_file(): errors.append('Character reference not ready: '+char['id'])
    if sids==mids:
        errors.extend(check_dialogue(project,data,local,assets,shot_id))
    return data,errors,warnings

def compile_prompts(project,data,shot_id=None):
    brief,chars,board=(data[n] for n in NAMES[:3]); lookup={c['id']:c for c in chars['characters']}
    paper_style = brief.get('style_preset') == 'paper-collage'
    style_addition = ('Layered paper collage illustration, tactile cut-paper edges, subtle paper fibers and print grain, '
                      'controlled registration offsets, soft contact shadows between layers, limited palette derived from '
                      'the production brief, handmade but precise silhouettes, clear readable faces and objects. Treat every '
                      'layer as a physical paper cutout; preserve a clean master composition before separation.') if paper_style else ''
    style_avoid = (['No glossy 3D plastic','no photorealistic surface','no random torn edges over faces or text',
                    'no independent lighting per layer','no unrelated scrapbook stickers','no theme or culture substitution']
                   if paper_style else [])
    for char in chars['characters']:
        if shot_id: continue
        save(project/'prompts'/('reference_'+char['id']+'.json'),{'task':'character_reference','identity':char['identity'],'prompt':char['reference']['prompt'],'output':char['reference']['image'],'lock':'identity_only','visual_language':brief['visual_language'],'style_preset':brief.get('style_preset','custom'),'style_addition':style_addition,'setting':brief['setting']})
    panels=[]
    for s in board['shots']:
        d=s.get('direction',{}); fps=brief['format']['fps']
        acting='；'.join(f"{c['character_id']}：{c['action']}" for c in s['characters']) or '无人；按场景叙事'
        expression='；'.join(f"{c['character_id']}：{c['expression']}，看向{c['gaze']}" for c in s['characters']) or '无'
        dialogue='；'.join(f"{c['speaker']}：{c['text']}" for c in s.get('dialogue',[])) or '无对白'
        timing='；'.join(f"{c['speaker']}：{c['start_frame']/fps:.3f}—{c['end_frame']/fps:.3f}秒（结束不含）" for c in s.get('dialogue',[])) or '无字幕'
        listening='；'.join(f"{r['character_id']}倾听反应：{r['response']}" for r in d.get('listening_reactions',[]))
        rows=[('镜头编号',s['id']),('持续时间',f"{s['duration_frames']/fps:.3f}秒 / {s['duration_frames']}帧"),('景别',s['shot_size']),('机位/构图',d.get('camera_position',s['angle'])+'；'+s['composition']),('场景背景',s['setting']+'；'+d.get('background_view','旧版未记录背景视图')),('出场人物','、'.join(c['character_id'] for c in s['characters']) or '无人'),('人物动作',acting+('；'+listening if listening else '')),('人物表情/视线',expression),('台词',dialogue),('字幕出现时机',timing),('微动态',d.get('micro_actions','旧版未记录')),('切镜原因',d.get('cut_reason',s['purpose'])),('下一镜头衔接',str(d.get('next_shot_id') or '结束')+'；'+d.get('handoff',s['continuity']))]
        panels.append('\n\n'.join(f'{label}：{value}' for label,value in rows)+'\n')
    (project/'storyboard_review.md').write_text('\n'.join(panels),encoding='utf-8')
    for shot in board['shots']:
        if shot_id and shot['id']!=shot_id: continue
        plan=next(s for s in data['motion_plan']['shots'] if s['shot_id']==shot['id'])
        space=next((s for s in board.get('scenes',[]) if s['id']==shot.get('direction',{}).get('scene_id')),None)
        index=board['shots'].index(shot)
        neighbors=[{'id':b['id'],'direction':b.get('direction'),'characters':b['characters']} for j,b in enumerate(board['shots']) if abs(j-index)==1]
        shot={**shot,'scene_space':space,'adjacent_shot_context':neighbors,
              'director_rules':'Keep location geometry, lighting, time and major objects consistent while independently composing each panel from its motivated camera position. Do not reuse the same background image or zoom/crop a previous panel. Preserve character identity and accessories. Design both speaking and listening reactions causally; follow incoming/outgoing state, gaze, cut reason and handoff. Hold briefly for a motivated reaction after dialogue. Comic exaggeration only at emotional peaks. The camera remains fixed inside each panel.'}
        save(project/'prompts'/(shot['id']+'_acting.json'),{
            'task':'prepare_aligned_acting_assets','master':shot['master'],
            'performers':shot['characters'],'performance':plan.get('performance'),
            'layers':plan['layers'],
            'dialogue':shot.get('dialogue',[]),
            'scene_space':space,
            'direction':shot.get('direction'),
            'sequential_comic_constraints':('One panel expresses one line, action or reaction. Fixed camera and composition. Animate character mouths, eyes, expressions, head, hands or simple limbs; use a new hard-cut panel for complex actions and new angles. Comic exaggeration, symbols and text effects are allowed for punchlines. Preserve character identity across panels. Subtitles follow supplied dialogue intervals. No camera motion or whole-image stretch as acting.' if (plan.get('performance') or {}).get('mode')=='sequential-comic' else None),
            'micro_performance_constraints':({'primary':'Exactly one complete blink per original comic shot; small mouth opening only during timed speech; extremely slight head turn; almost imperceptible chest/shoulder breathing; minimal hair movement. Preserve original pose and expression design.','secondary':'Remain still except optional occasional blinking. No secondary head, breathing or sway tracks.','stability':'No camera movement, whole-image stretch, large limb action, position changes, facial drift, deformed hands/feet or twisted bodies. Preserve original 2D linework.','review':'Visually count one primary blink and verify secondary stillness and anatomical stability; these are not automatically pixel-validated.'} if (plan.get('performance') or {}).get('mode')=='fixed-camera-micro' else None),
            'instructions':('Preserve the original master composition and pose. Fixed camera: no zoom, pan, rotation, scale or parallax. Animate only subtle local blinking, speech-timed mouth shapes, breathing and small head/hair/clothing motion. Keep background, identity and linework stable; no stretching or deformation. Mouth motion requires supplied dialogue timings and aligned local assets; automatic lip sync is not implemented.' if (plan.get('performance') or {}).get('mode')=='fixed-camera-micro' else 'Design anticipation, action, reaction and hold. Generate fresh pose drawings or separate joints from this shot master; fill exposed areas. Keep identity and contact points consistent. Never substitute a lineup crop or camera zoom for acting.')})
        save(project/'prompts'/(shot['id']+'.json'),{'task':'fresh_master_composition','output':shot['master'],'canvas':brief['format'],'original_content':brief['original_content'],'preserve':brief['content_preservation'],'setting':brief['setting'],'visual_language':brief['visual_language'],'style_preset':brief.get('style_preset','custom'),'style_addition':style_addition,'beat':next(b for b in board['beats'] if b['id']==shot['beat_id']),'shot':shot,'identity_references':[{'image':lookup[c['character_id']]['reference']['image'],'identity':lookup[c['character_id']]['identity'],'reference_scope':'face/hair/clothes/proportions only; do not copy pose or composition'} for c in shot['characters']],'negative_constraints':['Do not change cultural setting or topic','Do not paste or recycle a reference standing pose','No baked-in dialogue or captions']+style_avoid,'layer_instruction':'Generate and review the complete master FIRST. Extract/reconstruct aligned layers from this exact master; fill all occluded background. Never independently invent unrelated layers.'})

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['validate','compile','prepare','report'])
    parser.add_argument('project',type=Path)
    parser.add_argument('--renderer',type=Path)
    parser.add_argument('--assets',action='store_true')
    parser.add_argument('--shot',help='Compile or prepare only this shot; preparation rebases its timeline to zero')
    args=parser.parse_args(); project=args.project.resolve()
    data,errors,warnings=validate(project,args.assets or args.command=='prepare',args.shot)
    save(project/'qc_report.json',{'errors':errors,'repetition_warnings':warnings,'visual_review_required':True})
    if errors:
        print('\n'.join(errors)); return 1
    save(project/'asset_report.json',inventory(project,data,local))
    if args.command=='compile': compile_prompts(project,data,args.shot)
    if args.command=='prepare':
        if not args.renderer: parser.error('--renderer is required for prepare')
        renderer=args.renderer.resolve()
        if renderer==project or renderer.is_relative_to(project): parser.error('Renderer must be outside the source project')
        shutil.copytree(ROOT/'assets/remotion',renderer,dirs_exist_ok=True)
        for shot in data['motion_plan']['shots']:
            if args.shot and shot['shot_id']!=args.shot: continue
            for layer in shot['layers']:
                for name in asset_names(layer):
                    dest=local(renderer/'public',name); dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(local(project,name),dest)
        render_data=render_payload(project,data,local,args.shot)
        for shot in render_data['shots']:
            for cue in shot['dialogue']:
                if cue.get('audio'):
                    dest=local(renderer/'public',cue['audio']); dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(local(project,cue['audio']),dest)
        save(renderer/'src/render-data.json',render_data)
    print(f'PASS: {args.command}; {len(warnings)} repetition warning(s). See qc_report.json; semantic/visual QC remains human or agent reviewed.')
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError) as e: print(str(e),file=sys.stderr); sys.exit(1)
