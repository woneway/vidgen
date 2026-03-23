import React from "react";
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { COLORS, FONTS, SIZES } from "../theme";

interface SubtitleProps {
  text: string;
}

export const Subtitle: React.FC<SubtitleProps> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Split text into lines of ~14 chars for Chinese
  const lines = splitTextLines(text, 14);
  const visibleLines = lines.slice(0, 4); // max 4 lines

  // Fade in the subtitle bar
  const barOpacity = interpolate(frame, [5, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 120,
        left: 0,
        right: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        opacity: barOpacity,
      }}
    >
      {/* Semi-transparent background bar */}
      <div
        style={{
          backgroundColor: "rgba(0, 0, 0, 0.65)",
          borderRadius: 16,
          padding: "20px 40px",
          maxWidth: SIZES.width - 80,
        }}
      >
        {visibleLines.map((line, i) => {
          const lineDelay = i * 4;
          const lineProgress = spring({
            frame: frame - lineDelay,
            fps,
            config: { damping: 30, stiffness: 120 },
          });
          const translateY = interpolate(lineProgress, [0, 1], [15, 0]);
          const opacity = interpolate(lineProgress, [0, 1], [0, 1]);

          return (
            <div
              key={i}
              style={{
                fontFamily: FONTS.sans,
                fontSize: SIZES.subtitleFontSize,
                fontWeight: 700,
                color: COLORS.textPrimary,
                textAlign: "center",
                lineHeight: 1.6,
                textShadow: "0 2px 8px rgba(0,0,0,0.8)",
                transform: `translateY(${translateY}px)`,
                opacity,
              }}
            >
              {line}
            </div>
          );
        })}
      </div>
    </div>
  );
};

function splitTextLines(text: string, maxChars: number): string[] {
  const lines: string[] = [];
  let remaining = text;
  while (remaining.length > 0) {
    if (remaining.length <= maxChars) {
      lines.push(remaining);
      break;
    }
    // Try to split at punctuation or space
    let splitIdx = maxChars;
    const punctuation = "，。！？、；：";
    for (let j = maxChars; j > maxChars - 5 && j > 0; j--) {
      if (punctuation.includes(remaining[j]) || remaining[j] === " ") {
        splitIdx = j + 1;
        break;
      }
    }
    lines.push(remaining.slice(0, splitIdx));
    remaining = remaining.slice(splitIdx);
  }
  return lines;
}
