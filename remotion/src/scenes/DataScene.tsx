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

interface DataSceneProps {
  analysis: Analysis;
}

interface MetricCard {
  label: string;
  value: number;
  color: string;
  suffix?: string;
}

export const DataScene: React.FC<DataSceneProps> = ({ analysis }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const metrics: MetricCard[] = [
    {
      label: "代码行数",
      value: analysis.totalLoc,
      color: COLORS.accentBlue,
    },
    {
      label: "文件数量",
      value: analysis.totalFiles,
      color: COLORS.accentGreen,
    },
    {
      label: "依赖数量",
      value: analysis.dependencyCount,
      color: COLORS.accentOrange,
    },
    {
      label: "技术栈",
      value: analysis.techStack.length,
      color: COLORS.accentPurple,
      suffix: " 项",
    },
  ];

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
            fontSize: SIZES.headingFontSize,
            fontWeight: 800,
            color: COLORS.textPrimary,
            marginBottom: 60,
            opacity: titleOpacity,
          }}
        >
          项目数据一览
        </div>

        {/* 2x2 grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 28,
            width: SIZES.width - 120,
          }}
        >
          {metrics.map((metric, i) => {
            const delay = 10 + i * 8;
            const cardProgress = spring({
              frame: frame - delay,
              fps,
              config: { damping: 14, stiffness: 100 },
            });
            const cardScale = interpolate(cardProgress, [0, 1], [0.8, 1]);
            const cardOpacity = interpolate(cardProgress, [0, 1], [0, 1]);

            // Count-up animation
            const countProgress = interpolate(
              frame,
              [delay + 10, delay + 60],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            const displayValue = Math.round(metric.value * countProgress);

            return (
              <div
                key={metric.label}
                style={{
                  backgroundColor: COLORS.bgCard,
                  borderRadius: 20,
                  padding: "36px 28px",
                  transform: `scale(${cardScale})`,
                  opacity: cardOpacity,
                  border: `1px solid ${COLORS.border}`,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                {/* Color accent bar */}
                <div
                  style={{
                    width: 60,
                    height: 5,
                    borderRadius: 3,
                    backgroundColor: metric.color,
                    marginBottom: 8,
                  }}
                />

                {/* Number */}
                <div
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 64,
                    fontWeight: 800,
                    color: metric.color,
                    lineHeight: 1,
                  }}
                >
                  {formatNumber(displayValue)}
                  {metric.suffix || ""}
                </div>

                {/* Label */}
                <div
                  style={{
                    fontFamily: FONTS.sans,
                    fontSize: SIZES.bodyFontSize,
                    color: COLORS.textSecondary,
                  }}
                >
                  {metric.label}
                </div>
              </div>
            );
          })}
        </div>

        {/* Tech stack tags at bottom */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: 10,
            marginTop: 50,
            maxWidth: SIZES.width - 120,
          }}
        >
          {analysis.techStack.slice(0, 8).map((tech, i) => {
            const tagDelay = 50 + i * 4;
            const tagOpacity = interpolate(
              frame,
              [tagDelay, tagDelay + 10],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            return (
              <div
                key={tech}
                style={{
                  fontFamily: FONTS.mono,
                  fontSize: SIZES.smallFontSize - 4,
                  color: COLORS.textSecondary,
                  backgroundColor: "rgba(139,148,158,0.1)",
                  padding: "6px 16px",
                  borderRadius: 12,
                  border: `1px solid ${COLORS.border}`,
                  opacity: tagOpacity,
                }}
              >
                {tech}
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
