import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { SIZES } from "../theme";

interface AIImageSceneProps {
  imagePath: string;
}

export const AIImageScene: React.FC<AIImageSceneProps> = ({ imagePath }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Ken Burns: slow zoom from 1.0 to 1.05 over the scene duration
  const scale = interpolate(
    frame,
    [0, durationInFrames],
    [1.0, 1.05],
    { extrapolateRight: "clamp" }
  );

  // Slight pan
  const translateX = interpolate(
    frame,
    [0, durationInFrames],
    [0, -10],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* Image with Ken Burns effect — path is relative to public/ */}
      <Img
        src={staticFile(imagePath)}
        style={{
          width: SIZES.width,
          height: SIZES.height,
          objectFit: "cover",
          transform: `scale(${scale}) translateX(${translateX}px)`,
        }}
      />

      {/* Bottom gradient mask for subtitle readability */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 500,
          background:
            "linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.3) 50%, transparent 100%)",
        }}
      />
    </AbsoluteFill>
  );
};
