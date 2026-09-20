import React from 'react';
import {AbsoluteFill, Composition, Img, Sequence, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import input from './render-data.json';
type Key={frame:number;x:number;y:number;rotation:number;opacity:number};
type Layer={layer_id:string;asset:string;z:number;from:{x:number;y:number;scale:number};to:{x:number;y:number;scale:number};acting?:{part:string;pivot:[number,number];keys:Key[];poses?:{frame:number;asset:string}[]}};
const data=input as {format:{width:number;height:number;fps:number;duration_frames:number};asset_mode:string;shots:{shot_id:string;start_frame:number;duration_frames:number;layers:Layer[];dialogue?:{speaker:string;text:string;start_frame:number;end_frame:number}[]}[]};
const Shot = ({shot}: {shot: typeof data.shots[number]}) => {
  const frame = useCurrentFrame();
  const caption=shot.dialogue?.find(c=>frame>=c.start_frame && frame<c.end_frame);
  return <AbsoluteFill style={{overflow:'hidden'}}>{[...shot.layers].sort((a,b)=>a.z-b.z).map(layer => {
    const value = (key: 'x'|'y'|'scale') => interpolate(frame,[0,shot.duration_frames-1],[layer.from[key],layer.to[key]],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
    const a=layer.acting;
    const local=(key:'x'|'y'|'rotation'|'opacity',fallback:number)=>a?interpolate(frame,a.keys.map(k=>k.frame),a.keys.map(k=>k[key]),{extrapolateLeft:'clamp',extrapolateRight:'clamp'}):fallback;
    const pose=a?.poses?.filter(p=>p.frame<=frame).at(-1)?.asset ?? layer.asset;
    return <AbsoluteFill key={layer.layer_id} style={{transformOrigin:'50% 50%',transform:`translate(${value('x')}px, ${value('y')}px) scale(${value('scale')})`}}><Img src={staticFile(pose)} style={{width:'100%',height:'100%',opacity:local('opacity',1),transformOrigin:a?`${a.pivot[0]*100}% ${a.pivot[1]*100}%`:'50% 50%',transform:`translate(${local('x',0)}px, ${local('y',0)}px) rotate(${local('rotation',0)}deg)`}}/></AbsoluteFill>;
  })}{caption && <div style={{position:'absolute',bottom:'10%',left:'6%',right:'6%',textAlign:'center',color:'white',fontSize:Math.round(data.format.height*.045),fontFamily:'Arial, "Microsoft YaHei", sans-serif',fontWeight:700,whiteSpace:'pre-wrap',overflowWrap:'anywhere',textShadow:'-2px -2px 0 black, 2px -2px 0 black, -2px 2px 0 black, 2px 2px 0 black'}}>{caption.text}</div>}{data.asset_mode==='fixture' && <div style={{position:'absolute',left:24,bottom:20,color:'white',background:'#172332',padding:'8px 14px',fontSize:18,fontFamily:'sans-serif'}}>PIPELINE FIXTURE · {shot.shot_id} · NOT FINAL ART</div>}</AbsoluteFill>;
};
const Video = () => <AbsoluteFill style={{background:'#172332'}}>{data.shots.map(shot=><Sequence key={shot.shot_id} from={shot.start_frame} durationInFrames={shot.duration_frames}><Shot shot={shot}/></Sequence>)}</AbsoluteFill>;
registerRoot(()=> <Composition id="MangaMotion" component={Video} width={data.format.width} height={data.format.height} fps={data.format.fps} durationInFrames={data.format.duration_frames}/>);
