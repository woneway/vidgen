import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import {
  linearTiming,
  TransitionSeries,
} from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { Subtitle } from "./components/Subtitle";
import { SceneTransition } from "./components/SceneTransition";
import { TitleScene } from "./scenes/TitleScene";
import { AIImageScene } from "./scenes/AIImageScene";
import { CodeScene } from "./scenes/CodeScene";
import { DataScene } from "./scenes/DataScene";
import { ArchScene } from "./scenes/ArchScene";
import { EndingScene } from "./scenes/EndingScene";
import { SIZES } from "./theme";
import type { CodeIntroProps, Scene } from "./types";

export const CodeIntro: React.FC<CodeIntroProps> = ({
  title,
  scenes,
  analysis,
  audioPath,
  audioDuration,
}) => {
  const fps = SIZES.fps;
  const totalFrames = Math.round(audioDuration * fps);
  const transitionFrames = SIZES.transitionDuration;
  const numScenes = scenes.length;

  // Each scene duration, accounting for transition overlaps
  const totalTransitionFrames = Math.max(0, numScenes - 1) * transitionFrames;
  const perScene = Math.round(
    (totalFrames + totalTransitionFrames) / numScenes
  );

  // Track code example index for code_snippet scenes
  let codeExampleIdx = 0;

  return (
    <AbsoluteFill>
      <TransitionSeries>
        {scenes.map((scene, i) => {
          const elements: React.ReactNode[] = [];

          // Scene content
          elements.push(
            <TransitionSeries.Sequence
              key={`scene-${i}`}
              durationInFrames={perScene}
            >
              <SceneTransition>
                {renderScene(scene, analysis, title, codeExampleIdx)}
                <Subtitle text={scene.narration} />
              </SceneTransition>
            </TransitionSeries.Sequence>
          );

          // Update code example index
          if (scene.visualType === "code_snippet") {
            codeExampleIdx++;
          }

          // Transition (except after last scene)
          if (i < numScenes - 1) {
            elements.push(
              <TransitionSeries.Transition
                key={`trans-${i}`}
                presentation={fade()}
                timing={linearTiming({ durationInFrames: transitionFrames })}
              />
            );
          }

          return elements;
        })}
      </TransitionSeries>

      {/* Audio track — path is relative to public/, served via staticFile() */}
      {audioPath ? <Audio src={staticFile(audioPath)} /> : null}
    </AbsoluteFill>
  );
};

function renderScene(
  scene: Scene,
  analysis: CodeIntroProps["analysis"],
  title: string,
  codeExampleIdx: number
): React.ReactNode {
  switch (scene.visualType) {
    case "title_card":
      return (
        <TitleScene
          projectName={analysis.name}
          tagline={scene.narration}
          analysis={analysis}
        />
      );

    case "ai_image":
      if (scene.imagePath) {
        return <AIImageScene imagePath={scene.imagePath} />;
      }
      // Fallback: show as title card if no image
      return (
        <TitleScene
          projectName={analysis.name}
          tagline={scene.narration}
          analysis={analysis}
        />
      );

    case "code_snippet": {
      const examples = analysis.codeExamples;
      if (examples.length > 0) {
        const example = examples[codeExampleIdx % examples.length];
        return (
          <CodeScene
            filename={example.filename}
            code={example.code}
            language={example.language}
          />
        );
      }
      // Fallback
      return (
        <CodeScene
          filename="example"
          code={scene.narration}
          language="text"
        />
      );
    }

    case "data_card":
      return <DataScene analysis={analysis} />;

    case "architecture":
      return <ArchScene structure={analysis.structure} />;

    case "ending_card":
      return (
        <EndingScene
          projectName={analysis.name}
          summary={scene.narration}
          githubUrl={analysis.githubUrl}
        />
      );

    default:
      return (
        <TitleScene
          projectName={title}
          tagline={scene.narration}
          analysis={analysis}
        />
      );
  }
}
