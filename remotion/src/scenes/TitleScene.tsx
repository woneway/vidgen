import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Background } from "../components/Background";
import { COLORS, FONTS, SIZES } from "../theme";
import type { Analysis } from "../types";

interface TitleSceneProps {
  projectName: string;
  tagline: string;
  analysis: Analysis;
}

export const TitleScene: React.FC<TitleSceneProps> = ({
  projectName,
  tagline,
  analysis,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Project name: spring bounce-in
  const nameProgress = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 100 },
    durationInFrames: 30,
  });
  const nameScale = interpolate(nameProgress, [0, 1], [0.6, 1]);
  const nameOpacity = interpolate(nameProgress, [0, 1], [0, 1]);

  // Tagline: delayed fade-in
  const taglineOpacity = interpolate(frame, [20, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const taglineY = interpolate(frame, [20, 40], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Decorative line: slide in from left
  const lineWidth = interpolate(frame, [30, 55], [0, 400], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Tech stack tags: staggered entrance
  const tags = analysis.techStack.slice(0, 5);

  return (
    <AbsoluteFill>
      <Background variant="gradient" />

      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: SIZES.padding,
        }}
      >
        {/* Project name */}
        <div
          style={{
            fontFamily: FONTS.sans,
            fontSize: SIZES.titleFontSize,
            fontWeight: 900,
            color: COLORS.textPrimary,
            textAlign: "center",
            transform: `scale(${nameScale})`,
            opacity: nameOpacity,
            lineHeight: 1.3,
            maxWidth: 900,
          }}
        >
          {projectName}
        </div>

        {/* Decorative line */}
        <div
          style={{
            width: lineWidth,
            height: 4,
            borderRadius: 2,
            background: `linear-gradient(90deg, ${COLORS.accentBlue}, ${COLORS.accentGreen})`,
            marginTop: 30,
            marginBottom: 30,
          }}
        />

        {/* Tagline */}
        <div
          style={{
            fontFamily: FONTS.sans,
            fontSize: SIZES.bodyFontSize,
            color: COLORS.textSecondary,
            textAlign: "center",
            opacity: taglineOpacity,
            transform: `translateY(${taglineY}px)`,
            maxWidth: 800,
            lineHeight: 1.6,
          }}
        >
          {tagline}
        </div>

        {/* Tech stack tags */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: 12,
            marginTop: 50,
          }}
        >
          {tags.map((tag, i) => {
            const tagDelay = 40 + i * 6;
            const tagOpacity = interpolate(
              frame,
              [tagDelay, tagDelay + 12],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            const tagY = interpolate(
              frame,
              [tagDelay, tagDelay + 12],
              [20, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            return (
              <div
                key={tag}
                style={{
                  fontFamily: FONTS.sans,
                  fontSize: SIZES.smallFontSize,
                  color: COLORS.accentBlue,
                  backgroundColor: "rgba(56,138,244,0.12)",
                  padding: "8px 20px",
                  borderRadius: 20,
                  border: `1px solid rgba(56,138,244,0.25)`,
                  opacity: tagOpacity,
                  transform: `translateY(${tagY}px)`,
                }}
              >
                {tag}
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
