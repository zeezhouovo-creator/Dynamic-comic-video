import React from 'react';
import {AbsoluteFill, Composition, Img, Sequence, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import data from './render-data.json';
const Shot = ({shot}: {shot: typeof data.shots[number]}) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{overflow:'hidden'}}>{[...shot.layers].sort((a,b)=>a.z-b.z).map(layer => {
    const value = (key: 'x'|'y'|'scale') => interpolate(frame,[0,shot.duration_frames-1],[layer.from[key],layer.to[key]],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
    return <Img key={layer.layer_id} src={staticFile(layer.asset)} style={{position:'absolute',width:'100%',height:'100%',transformOrigin:'50% 50%',transform:`translate(${value('x')}px, ${value('y')}px) scale(${value('scale')})`}}/>;
  })}{data.asset_mode==='fixture' && <div style={{position:'absolute',left:24,bottom:20,color:'white',background:'#172332',padding:'8px 14px',fontSize:18,fontFamily:'sans-serif'}}>PIPELINE FIXTURE · {shot.shot_id} · NOT FINAL ART</div>}</AbsoluteFill>;
};
const Video = () => <AbsoluteFill style={{background:'#172332'}}>{data.shots.map(shot=><Sequence key={shot.shot_id} from={shot.start_frame} durationInFrames={shot.duration_frames}><Shot shot={shot}/></Sequence>)}</AbsoluteFill>;
registerRoot(()=> <Composition id="MangaMotion" component={Video} width={data.format.width} height={data.format.height} fps={data.format.fps} durationInFrames={data.format.duration_frames}/>);
