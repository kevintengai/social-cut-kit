import React from "react";
import {AbsoluteFill, Composition, Html5Audio, Img, OffthreadVideo, Sequence, registerRoot, staticFile} from "remotion";
import cut from "./cut.json";
import {captionLayout, levelAt} from "./cut-plan.cjs";

// Every Number Here Comes From cut.json. The Timing And Layout Rules Live In cut-plan.cjs.
const fill = {position: "absolute", left: 0, top: 0, width: "100%", height: "100%", objectFit: "fill", maxWidth: "none"};

function Picture({row}) {
  if (row.kind === "image") return <Img src={staticFile(row.file)} style={fill} />;
  return <OffthreadVideo src={staticFile(row.file)} trimBefore={row.trim} playbackRate={row.speed ?? 1} muted
    toneMapped={row.toneMapped} pauseWhenBuffering style={fill} />;
}

function Sound({row, speed}) {
  return <Html5Audio src={staticFile(row.file)} trimBefore={row.sound.trim} playbackRate={speed}
    volume={frame => levelAt(row.sound, frame, row.frames, cut.fps)} pauseWhenBuffering />;
}

function Shot({row}) {
  return <Sequence from={row.from} durationInFrames={row.frames} name={row.id}>
    <div style={{position: "absolute", overflow: "hidden", ...row.box}}>
      <div style={{position: "absolute", ...row.media, ...(row.filter ? {filter: row.filter} : {})}}><Picture row={row} /></div>
    </div>
    {row.sound ? <Sound row={row} speed={row.speed} /> : null}
  </Sequence>;
}

function Overlay({row}) {
  return <Sequence from={row.from} durationInFrames={row.frames} name={row.id}>
    <div style={{position: "absolute", left: row.left, top: row.top, width: row.width, height: row.height}}><Picture row={row} /></div>
  </Sequence>;
}

function Cue({row}) {
  return <Sequence from={row.from} durationInFrames={row.frames} name={row.id} layout="none">
    <Sound row={{file: row.file, frames: row.frames, sound: row}} speed={1} />
  </Sequence>;
}

function Caption({row, look}) {
  const edge = row.position === "top" ? {top: look.edge} : row.position === "bottom" ? {bottom: look.edge} : {top: "50%", transform: "translateY(-50%)"};
  return <Sequence from={row.from} durationInFrames={row.frames} name={row.id}>
    <div style={{position: "absolute", left: look.side, right: look.side, ...edge, textAlign: "center", whiteSpace: "pre-line", textWrap: "balance",
      fontFamily: look.fontFamily, fontWeight: 700, fontSize: look.fontSize, lineHeight: look.lineHeight + "px", color: look.color,
      WebkitTextStroke: look.stroke * 2 + "px " + look.outline, paintOrder: "stroke fill", strokeLinejoin: "round"}}>{row.text}</div>
  </Sequence>;
}

function Edit() {
  const look = captionLayout(cut.captionStyle, cut.width, cut.height);
  return <AbsoluteFill style={{backgroundColor: "black"}}>
    {cut.shots.map(row => <Shot key={row.id} row={row} />)}
    {cut.overlays.map(row => <Overlay key={row.id} row={row} />)}
    {cut.captions.map(row => <Caption key={row.id} row={row} look={look} />)}
    {cut.audio.map(row => <Cue key={row.id} row={row} />)}
  </AbsoluteFill>;
}

function Root() {
  return <Composition id="VideoEdit" component={Edit} width={cut.width} height={cut.height} fps={cut.fps} durationInFrames={cut.frames} />;
}
registerRoot(Root);
