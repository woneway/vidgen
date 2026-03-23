import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { atomDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Background } from "../components/Background";
import { COLORS, FONTS, SIZES } from "../theme";

interface CodeSceneProps {
  filename: string;
  code: string;
  language: string;
}

export const CodeScene: React.FC<CodeSceneProps> = ({
  filename,
  code,
  language,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const lines = code.split("\n");
  const maxVisibleLines = 18;
  const visibleLines = lines.slice(0, maxVisibleLines);

  // Window container spring entrance
  const windowProgress = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 80 },
    durationInFrames: 25,
  });
  const windowScale = interpolate(windowProgress, [0, 1], [0.9, 1]);
  const windowOpacity = interpolate(windowProgress, [0, 1], [0, 1]);

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
        {/* Terminal window */}
        <div
          style={{
            width: SIZES.width - 100,
            maxHeight: 1400,
            backgroundColor: "#1a1b26",
            borderRadius: 16,
            overflow: "hidden",
            boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
            transform: `scale(${windowScale})`,
            opacity: windowOpacity,
          }}
        >
          {/* Title bar */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              padding: "14px 20px",
              backgroundColor: "#24283b",
              gap: 10,
            }}
          >
            {/* Traffic light buttons */}
            <div
              style={{
                width: 14,
                height: 14,
                borderRadius: 7,
                backgroundColor: "#f85149",
              }}
            />
            <div
              style={{
                width: 14,
                height: 14,
                borderRadius: 7,
                backgroundColor: "#d29922",
              }}
            />
            <div
              style={{
                width: 14,
                height: 14,
                borderRadius: 7,
                backgroundColor: "#3fb950",
              }}
            />
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 20,
                color: COLORS.textSecondary,
                marginLeft: 12,
                flex: 1,
              }}
            >
              {filename}
            </div>
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 16,
                color: COLORS.accentOrange,
                backgroundColor: "rgba(210,153,34,0.12)",
                padding: "4px 10px",
                borderRadius: 8,
              }}
            >
              {language}
            </div>
          </div>

          {/* Code content with line-by-line reveal */}
          <div style={{ padding: "16px 0", overflow: "hidden" }}>
            {visibleLines.map((line, i) => {
              const lineDelay = 10 + i * 3;
              const lineOpacity = interpolate(
                frame,
                [lineDelay, lineDelay + 8],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );
              const lineX = interpolate(
                frame,
                [lineDelay, lineDelay + 8],
                [-20, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );

              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    opacity: lineOpacity,
                    transform: `translateX(${lineX}px)`,
                  }}
                >
                  {/* Line number */}
                  <div
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: SIZES.codeFontSize,
                      color: COLORS.textMuted,
                      width: 50,
                      textAlign: "right",
                      paddingRight: 16,
                      userSelect: "none",
                      flexShrink: 0,
                    }}
                  >
                    {i + 1}
                  </div>
                  {/* Code line */}
                  <div
                    style={{
                      flex: 1,
                      overflow: "hidden",
                    }}
                  >
                    <SyntaxHighlighter
                      language={language}
                      style={atomDark}
                      customStyle={{
                        margin: 0,
                        padding: 0,
                        background: "transparent",
                        fontSize: SIZES.codeFontSize,
                        lineHeight: 1.6,
                        fontFamily: FONTS.mono,
                      }}
                      codeTagProps={{
                        style: {
                          fontFamily: FONTS.mono,
                          fontSize: SIZES.codeFontSize,
                        },
                      }}
                      wrapLines={false}
                      PreTag="span"
                    >
                      {line || " "}
                    </SyntaxHighlighter>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
