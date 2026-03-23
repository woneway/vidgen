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

interface EndingSceneProps {
  projectName: string;
  summary: string;
  githubUrl: string | null;
}

export const EndingScene: React.FC<EndingSceneProps> = ({
  projectName,
  summary,
  githubUrl,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Project name entrance
  const nameProgress = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 100 },
    durationInFrames: 25,
  });
  const nameScale = interpolate(nameProgress, [0, 1], [0.8, 1]);
  const nameOpacity = interpolate(nameProgress, [0, 1], [0, 1]);

  // Summary fade in
  const summaryOpacity = interpolate(frame, [15, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // GitHub URL fade in
  const urlOpacity = interpolate(frame, [30, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // CTA button pulse animation
  const pulsePhase = Math.sin((frame / fps) * Math.PI * 2 * 0.8);
  const ctaScale = 1 + pulsePhase * 0.03;
  const ctaOpacity = interpolate(frame, [40, 55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

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
          gap: 30,
        }}
      >
        {/* Project name */}
        <div
          style={{
            fontFamily: FONTS.sans,
            fontSize: SIZES.titleFontSize - 4,
            fontWeight: 900,
            color: COLORS.textPrimary,
            textAlign: "center",
            transform: `scale(${nameScale})`,
            opacity: nameOpacity,
            maxWidth: 850,
            lineHeight: 1.3,
          }}
        >
          {projectName}
        </div>

        {/* Summary text */}
        <div
          style={{
            fontFamily: FONTS.sans,
            fontSize: SIZES.bodyFontSize,
            color: COLORS.textSecondary,
            textAlign: "center",
            opacity: summaryOpacity,
            maxWidth: 800,
            lineHeight: 1.7,
          }}
        >
          {summary}
        </div>

        {/* GitHub URL */}
        {githubUrl && (
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: SIZES.smallFontSize,
              color: COLORS.accentBlue,
              opacity: urlOpacity,
              marginTop: 10,
            }}
          >
            {githubUrl}
          </div>
        )}

        {/* CTA button */}
        <div
          style={{
            marginTop: 30,
            backgroundColor: COLORS.accentBlue,
            borderRadius: 40,
            padding: "18px 50px",
            transform: `scale(${ctaScale})`,
            opacity: ctaOpacity,
            boxShadow: "0 8px 30px rgba(56,138,244,0.35)",
          }}
        >
          <div
            style={{
              fontFamily: FONTS.sans,
              fontSize: SIZES.bodyFontSize,
              fontWeight: 700,
              color: "#ffffff",
            }}
          >
            Star on GitHub
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
