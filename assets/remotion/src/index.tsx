import React from 'react';
import {AbsoluteFill, Audio, Composition, Img, Sequence, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import input from './render-data.json';
type Key={frame:number;x:number;y:number;rotation:number;opacity:number};
type Layer={layer_id:string;asset:string;region?:[number,number,number,number];z:number;from:{x:number;y:number;scale:number};to:{x:number;y:number;scale:number};acting?:{part:string;pivot:[number,number];keys:Key[];speech?:{speaker:string;closed_asset:string;open_asset:string};poses?:{frame:number;asset:string}[]}};
const data=input as {format:{width:number;height:number;fps:number;duration_frames:number};asset_mode:string;shots:{shot_id:string;start_frame:number;duration_frames:number;layers:Layer[];dialogue?:{speaker:string;text:string;start_frame:number;end_frame:number;audio?:string;mouth_open_frames?:number[]}[]}[]};
const Shot = ({shot}: {shot: typeof data.shots[number]}) => {
  const frame = useCurrentFrame();
  const caption=shot.dialogue?.find(c=>frame>=c.start_frame && frame<c.end_frame);
  return <AbsoluteFill style={{overflow:'hidden'}}>{[...shot.layers].sort((a,b)=>a.z-b.z).map(layer => {
    const value = (key: 'x'|'y'|'scale') => interpolate(frame,[0,shot.duration_frames-1],[layer.from[key],layer.to[key]],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
    const a=layer.acting;
    const local=(key:'x'|'y'|'rotation'|'opacity',fallback:number)=>a?interpolate(frame,a.keys.map(k=>k.frame),a.keys.map(k=>k[key]),{extrapolateLeft:'clamp',extrapolateRight:'clamp'}):fallback;
    let pose=a?.poses?.filter(p=>p.frame<=frame).at(-1)?.asset ?? layer.asset;
    if(a?.speech){
      const cue=shot.dialogue?.find(c=>c.speaker===a.speech!.speaker && frame>=c.start_frame && frame<c.end_frame);
      pose=cue?.mouth_open_frames?.includes(frame-cue.start_frame)?a.speech.open_asset:a.speech.closed_asset;
    }
    const r=layer.region;
    return <AbsoluteFill key={layer.layer_id} style={{clipPath:r?`inset(${r[1]*100}% ${(1-r[0]-r[2])*100}% ${(1-r[1]-r[3])*100}% ${r[0]*100}%)`:undefined,transformOrigin:'50% 50%',transform:`translate(${value('x')}px, ${value('y')}px) scale(${value('scale')})`}}><Img src={staticFile(pose)} style={{width:'100%',height:'100%',opacity:local('opacity',1),transformOrigin:a?`${a.pivot[0]*100}% ${a.pivot[1]*100}%`:'50% 50%',transform:`translate(${local('x',0)}px, ${local('y',0)}px) rotate(${local('rotation',0)}deg)`}}/></AbsoluteFill>;
  })}{caption && <div style={{position:'absolute',bottom:'10%',left:'6%',right:'6%',textAlign:'center',color:'white',fontSize:Math.round(data.format.height*.045),fontFamily:'Arial, "Microsoft YaHei", sans-serif',fontWeight:700,whiteSpace:'pre-wrap',overflowWrap:'anywhere',textShadow:'-2px -2px 0 black, 2px -2px 0 black, -2px 2px 0 black, 2px 2px 0 black'}}>{caption.text}</div>}{data.asset_mode==='fixture' && <div style={{position:'absolute',left:24,bottom:20,color:'white',background:'#172332',padding:'8px 14px',fontSize:18,fontFamily:'sans-serif'}}>PIPELINE FIXTURE · {shot.shot_id} · NOT FINAL ART</div>}</AbsoluteFill>;
};
const Video = () => <AbsoluteFill style={{background:'#172332'}}>{data.shots.map(shot=><Sequence key={shot.shot_id} from={shot.start_frame} durationInFrames={shot.duration_frames}><Shot shot={shot}/>{shot.dialogue?.filter(c=>c.audio).map((c,i)=><Sequence key={i} from={c.start_frame} durationInFrames={c.end_frame-c.start_frame}><Audio src={staticFile(c.audio!)} /></Sequence>)}</Sequence>)}</AbsoluteFill>;
registerRoot(()=> <Composition id="MangaMotion" component={Video} width={data.format.width} height={data.format.height} fps={data.format.fps} durationInFrames={data.format.duration_frames}/>);
