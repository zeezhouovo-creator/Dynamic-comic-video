"""Finite animation validation; transforms alone cannot prove convincing acting."""
def asset_names(layer):
    return list(dict.fromkeys([layer['asset']]+[p['asset'] for p in layer.get('acting',{}).get('poses',[])]))

def check_acting(shot, production, assets, roles):
    errors=[]; active=False
    sid=shot['shot_id']; perf=shot.get('performance')
    if not perf: errors.append('Missing performance plan '+sid)
    for layer in shot['layers']:
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
        # Whole-cutout movement is still camera-like; local joints or new drawings count.
        if roles.get(layer['layer_id'])!='background' and (pose_change or (a['part']!='whole' and changing)):
            active=True
    if not active and not (perf or {}).get('static_reason'):
        errors.append('Camera-only shot requires acting or justified static hold '+sid)
    if production and assets and not (perf or {}).get('reviewed'):
        errors.append('Performance visual review incomplete '+sid)
    return errors
