import React from "react";
import { AbsoluteFill } from "remotion";

interface SceneTransitionProps {
  children: React.ReactNode;
}

/**
 * Wrapper for scene content. TransitionSeries handles the actual
 * transition animation; this provides a consistent container.
 */
export const SceneTransition: React.FC<SceneTransitionProps> = ({
  children,
}) => {
  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
