import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";

interface BackgroundProps {
  variant?: "gradient" | "particles" | "solid";
}

export const Background: React.FC<BackgroundProps> = ({
  variant = "gradient",
}) => {
  const frame = useCurrentFrame();

  if (variant === "solid") {
    return (
      <AbsoluteFill style={{ backgroundColor: COLORS.bgDark }} />
    );
  }

  // Animated gradient: slowly shift hue over time
  const hueShift = interpolate(frame, [0, 300], [0, 30], {
    extrapolateRight: "extend",
  });
  const bgColor1 = `hsl(${220 + hueShift}, 40%, 6%)`;
  const bgColor2 = `hsl(${240 + hueShift}, 35%, 12%)`;
  const bgColor3 = `hsl(${260 + hueShift}, 30%, 8%)`;

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${bgColor1} 0%, ${bgColor2} 50%, ${bgColor3} 100%)`,
      }}
    >
      {/* Subtle grid overlay for depth */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `radial-gradient(circle at 50% 50%, rgba(56,138,244,0.03) 0%, transparent 70%)`,
        }}
      />
    </AbsoluteFill>
  );
};
