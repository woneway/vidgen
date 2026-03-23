import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { Background } from "../components/Background";
import { COLORS, FONTS, SIZES } from "../theme";

interface ArchSceneProps {
  structure: string;
}

export const ArchScene: React.FC<ArchSceneProps> = ({ structure }) => {
  const frame = useCurrentFrame();

  const lines = structure.split("\n").slice(0, 28);

  // Title entrance
  const titleOpacity = interpolate(frame, [0, 15], [0, 1], {
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
        }}
      >
        {/* Title */}
        <div
          style={{
            fontFamily: FONTS.sans,
            fontSize: SIZES.headingFontSize - 4,
            fontWeight: 800,
            color: COLORS.textPrimary,
            marginBottom: 40,
            opacity: titleOpacity,
          }}
        >
          项目结构
        </div>

        {/* Directory tree container */}
        <div
          style={{
            backgroundColor: COLORS.bgCard,
            borderRadius: 16,
            padding: "30px 36px",
            width: SIZES.width - 120,
            border: `1px solid ${COLORS.border}`,
            overflow: "hidden",
          }}
        >
          {lines.map((line, i) => {
            const lineDelay = 8 + i * 2;
            const lineOpacity = interpolate(
              frame,
              [lineDelay, lineDelay + 8],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            const lineX = interpolate(
              frame,
              [lineDelay, lineDelay + 8],
              [-30, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );

            const isDir = line.trimEnd().endsWith("/");
            // Detect tree symbols
            const match = line.match(/^([\s│]*[├└]──\s*)/);
            const prefix = match ? match[1] : "";
            const name = match ? line.slice(prefix.length) : line;

            return (
              <div
                key={i}
                style={{
                  fontFamily: FONTS.mono,
                  fontSize: SIZES.codeFontSize + 2,
                  lineHeight: 1.7,
                  whiteSpace: "pre",
                  opacity: lineOpacity,
                  transform: `translateX(${lineX}px)`,
                  display: "flex",
                }}
              >
                {/* Tree symbols in gray */}
                <span style={{ color: COLORS.textMuted }}>{prefix}</span>
                {/* Name: blue for dirs, white for files */}
                <span
                  style={{
                    color: isDir ? COLORS.accentBlue : COLORS.textPrimary,
                    fontWeight: isDir ? 600 : 400,
                  }}
                >
                  {name}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
