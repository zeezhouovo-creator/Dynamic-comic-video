"""Local-only V0.1 contract validation, prompt compiler and renderer preparation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from jsonschema import Draft202012Validator
from PIL import Image

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

def validate(project, assets=False):
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
        if sum(l['role']=='background' for l in shot['layers'])!=1: errors.append('Need exactly one completed background '+sid)
        layerchars={l.get('character_id') for l in shot['layers'] if l['role']=='character'}
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
    cursor=0; hashes={}
    for item in motion['shots']:
        sid=item['shot_id']; shot=next((s for s in board['shots'] if s['id']==sid),None)
        if item['start_frame']!=cursor: errors.append('Timeline gap/overlap '+sid)
        cursor+=item['duration_frames']
        if not shot: continue
        if item['duration_frames']!=shot['duration_frames']: errors.append('Duration mismatch '+sid)
        lids=unique(item['layers'],'layer_id',sid+' motion layer')
        if lids!={l['id'] for l in shot['layers']}: errors.append('Layer set mismatch '+sid)
        unique(item['layers'],'z',sid+' z order')
        roles={l['id']:l['role'] for l in shot['layers']}
        bgz=[l['z'] for l in item['layers'] if roles.get(l['layer_id'])=='background']
        if bgz and bgz[0]!=min(l['z'] for l in item['layers']): errors.append('Background must be bottom layer '+sid)
        if motion['asset_mode']=='production' and not all(item['review'][k] for k in ('master_alignment','background_completed','motion_bounds_checked')): errors.append('Production visual review incomplete '+sid)
        width,height=brief['format']['width'],brief['format']['height']
        for layer in item['layers']:
            for t in (layer['from'],layer['to']):
                if abs(t['x'])>(t['scale']-1)*width/2+1e-6 or abs(t['y'])>(t['scale']-1)*height/2+1e-6: errors.append('Motion can reveal canvas edge '+sid+'/'+layer['layer_id'])
        if assets:
            for name,role in [(shot['master'],'master')]+[(l['asset'],roles.get(l['layer_id'])) for l in item['layers']]:
                p=local(project,name)
                if not p.is_file(): errors.append('Missing asset '+name); continue
                try:
                    with Image.open(p) as im:
                        if im.size!=(width,height): errors.append('Canvas size mismatch '+name)
                        alpha=im.convert('RGBA').getchannel('A').getextrema()
                        if role in ('background','master') and alpha!=(255,255): errors.append('Opaque image required '+name)
                        if role in ('character','foreground','effects') and (alpha[0]==255 or alpha[1]==0): errors.append('Nonempty transparent layer required '+name)
                except Exception as e: errors.append('Invalid image '+name+': '+str(e))
                if role=='character':
                    digest=hashlib.sha256(p.read_bytes()).hexdigest()
                    if digest in hashes: errors.append('Reused character cutout: '+name+' and '+hashes[digest])
                    hashes[digest]=name
    if cursor!=brief['format']['duration_frames']: errors.append('Total duration mismatch')
    if brief['format']['width']%2 or brief['format']['height']%2: errors.append('H264 dimensions must be even')
    if assets and motion['asset_mode']=='production':
        for char in chars['characters']:
            if char['reference']['status']!='ready' or not local(project,char['reference']['image']).is_file(): errors.append('Character reference not ready: '+char['id'])
    return data,errors,warnings

def compile_prompts(project,data):
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
        save(project/'prompts'/('reference_'+char['id']+'.json'),{'task':'character_reference','identity':char['identity'],'prompt':char['reference']['prompt'],'output':char['reference']['image'],'lock':'identity_only','visual_language':brief['visual_language'],'style_preset':brief.get('style_preset','custom'),'style_addition':style_addition,'setting':brief['setting']})
    for shot in board['shots']:
        save(project/'prompts'/(shot['id']+'.json'),{'task':'fresh_master_composition','output':shot['master'],'canvas':brief['format'],'original_content':brief['original_content'],'preserve':brief['content_preservation'],'setting':brief['setting'],'visual_language':brief['visual_language'],'style_preset':brief.get('style_preset','custom'),'style_addition':style_addition,'beat':next(b for b in board['beats'] if b['id']==shot['beat_id']),'shot':shot,'identity_references':[{'image':lookup[c['character_id']]['reference']['image'],'identity':lookup[c['character_id']]['identity'],'reference_scope':'face/hair/clothes/proportions only; do not copy pose or composition'} for c in shot['characters']],'negative_constraints':['Do not change cultural setting or topic','Do not paste or recycle a reference standing pose','No baked-in dialogue or captions']+style_avoid,'layer_instruction':'Generate and review the complete master FIRST. Extract/reconstruct aligned layers from this exact master; fill all occluded background. Never independently invent unrelated layers.'})

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['validate','compile','prepare'])
    parser.add_argument('project',type=Path)
    parser.add_argument('--renderer',type=Path)
    parser.add_argument('--assets',action='store_true')
    args=parser.parse_args(); project=args.project.resolve()
    data,errors,warnings=validate(project,args.assets or args.command=='prepare')
    save(project/'qc_report.json',{'errors':errors,'repetition_warnings':warnings,'visual_review_required':True})
    if errors:
        print('\n'.join(errors)); return 1
    if args.command=='compile': compile_prompts(project,data)
    if args.command=='prepare':
        if not args.renderer: parser.error('--renderer is required for prepare')
        renderer=args.renderer.resolve()
        if renderer==project or renderer.is_relative_to(project): parser.error('Renderer must be outside the source project')
        shutil.copytree(ROOT/'assets/remotion',renderer,dirs_exist_ok=True)
        for shot in data['motion_plan']['shots']:
            for layer in shot['layers']:
                dest=local(renderer/'public',layer['asset']); dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(local(project,layer['asset']),dest)
        save(renderer/'src/render-data.json',{'format':data['production_brief']['format'],**data['motion_plan']})
    print(f'PASS: {args.command}; {len(warnings)} repetition warning(s). See qc_report.json; semantic/visual QC remains human or agent reviewed.')
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError) as e: print(str(e),file=sys.stderr); sys.exit(1)
