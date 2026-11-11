import React, {useLayoutEffect, useRef} from "react";
import {AbsoluteFill, Composition, registerRoot, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
import {Audio} from "@remotion/media";
import {MotionFrame} from "./painter.mjs";
import project from "./frame-project.json";
import timeline from "./timeline.json";

function Storyboard() {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const target = useRef(null);
  useLayoutEffect(() => {
    MotionFrame.draw(target.current, project, frame / fps);
  }, [frame, fps, width, height]);
  return <AbsoluteFill>
    <canvas ref={target} width={width} height={height} style={{width, height}} />
    {timeline.audio.map(cue => <Audio
      key={cue.id}
      src={staticFile(cue.file)}
      from={cue.from}
      durationInFrames={cue.frames}
      premountFor={fps}
      volume={cue.gain}
      {...(cue.trimBefore ? {trimBefore: cue.trimBefore} : {})}
    />)}
  </AbsoluteFill>;
}

function Root() {
  return <Composition
    id="MotionStoryboard"
    component={Storyboard}
    width={timeline.width}
    height={timeline.height}
    fps={timeline.fps}
    durationInFrames={timeline.frames}
  />;
}
registerRoot(Root);
