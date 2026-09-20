"""Finite animation validation; transforms alone cannot prove convincing acting."""
def asset_names(layer):
    a=layer.get('acting',{}); speech=a.get('speech',{})
    return list(dict.fromkeys([layer['asset']]+[p['asset'] for p in a.get('poses',[])]+[speech[k] for k in ('closed_asset','open_asset') if k in speech]))

def check_acting(shot, production, assets, roles):
    errors=[]; active=False
    sid=shot['shot_id']; perf=shot.get('performance')
    if not perf: errors.append('Missing performance plan '+sid)
    micro=(perf or {}).get('mode')=='fixed-camera-micro'
    fixed=micro or (perf or {}).get('mode')=='sequential-comic'
    for layer in shot['layers']:
        if fixed and any(layer[t]!={'x':0,'y':0,'scale':1} for t in ('from','to')):
            errors.append('Fixed-camera mode requires identity layer framing '+sid+'/'+layer['layer_id'])
        a=layer.get('acting')
        if not a: continue
        keys=a['keys']; poses=a.get('poses',[])
        for group in (keys,poses):
            if not group: continue
            frames=[k['frame'] for k in group]
            if frames[0]!=0 or frames!=sorted(set(frames)) or frames[-1]>=shot['duration_frames']:
                errors.append('Invalid acting frames '+sid+'/'+layer['layer_id'])
        changing=len({(k['x'],k['y'],k['rotation'],k['opacity']) for k in keys})>1
        pose_change=len({p['asset'] for p in poses})>1
        speech=a.get('speech')
        if speech:
            if poses: errors.append('Speech and explicit poses cannot share one mouth track '+sid)
            if a['part']!='mouth' or speech['closed_asset']==speech['open_asset']:
                errors.append('Speech requires mouth part and distinct assets '+sid)
            else: active=True
        if fixed:
            if roles.get(layer['layer_id']) in ('background','panel_base') and (speech or pose_change or any(k['x'] or k['y'] or k['rotation'] or k['opacity']!=1 for k in keys)):
                errors.append('Fixed-camera background must remain unchanged '+sid)
            if micro and any(abs(k['rotation'])>2 for k in keys):
                errors.append('Micro acting rotation exceeds 2 degrees '+sid+'/'+layer['layer_id'])
        # Whole-cutout movement is still camera-like; local joints or new drawings count.
        if roles.get(layer['layer_id'])!='background' and (pose_change or (a['part']!='whole' and changing)):
            active=True
    if not active and not (perf or {}).get('static_reason'):
        errors.append('Camera-only shot requires acting or justified static hold '+sid)
    if production and assets and not (perf or {}).get('reviewed'):
        errors.append('Performance visual review incomplete '+sid)
    return errors
