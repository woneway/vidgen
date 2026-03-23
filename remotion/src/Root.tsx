import React from "react";
import { Composition } from "remotion";
import type { CalculateMetadataFunction } from "remotion";
import { CodeIntro } from "./CodeIntro";
import { CodeIntroSchema, type CodeIntroProps } from "./types";
import { SIZES } from "./theme";
import "./global.css";

/**
 * Dynamically set video duration based on audioDuration from props.
 * This ensures the rendered video matches the TTS audio length.
 */
const calculateMetadata: CalculateMetadataFunction<CodeIntroProps> = ({
  props,
}) => {
  return {
    durationInFrames: Math.max(
      SIZES.fps, // minimum 1 second
      Math.round(props.audioDuration * SIZES.fps),
    ),
    fps: SIZES.fps,
    width: SIZES.width,
    height: SIZES.height,
  };
};

const defaultProps = {
  title: "Sample Project",
  tags: ["#opensource", "#python"],
  scenes: [
    {
      narration: "这是一个示例项目的标题场景",
      imagePrompt: "A futuristic code project",
      visualType: "title_card" as const,
    },
    {
      narration: "项目拥有完善的代码架构和清晰的目录结构",
      imagePrompt: "Code architecture diagram",
      visualType: "data_card" as const,
    },
    {
      narration: "让我们来看看核心代码的实现",
      imagePrompt: "Code on screen",
      visualType: "code_snippet" as const,
    },
    {
      narration: "项目的目录结构清晰明了",
      imagePrompt: "File tree structure",
      visualType: "architecture" as const,
    },
    {
      narration: "感谢观看，欢迎访问项目主页",
      imagePrompt: "Call to action",
      visualType: "ending_card" as const,
    },
  ],
  analysis: {
    name: "Sample Project",
    description: "A sample project for preview",
    techStack: ["Python", "TypeScript", "React"],
    totalLoc: 12500,
    totalFiles: 87,
    dependencyCount: 24,
    testInfo: "pytest — 15 个测试文件",
    githubUrl: "https://github.com/example/sample",
    githubStats: { stars: 1200, forks: 340 },
    structure:
      "sample-project/\n├── src/\n│   ├── main.py\n│   ├── utils/\n│   └── models/\n├── tests/\n├── docs/\n└── README.md",
    codeExamples: [
      {
        filename: "main.py",
        code: 'import asyncio\nfrom pathlib import Path\n\nasync def main():\n    """Entry point for the application."""\n    config = load_config()\n    app = Application(config)\n    await app.start()\n\nif __name__ == "__main__":\n    asyncio.run(main())',
        language: "python",
      },
    ],
  },
  audioPath: "",
  audioDuration: 30,
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="CodeIntro"
      component={CodeIntro}
      durationInFrames={Math.round(defaultProps.audioDuration * SIZES.fps)}
      fps={SIZES.fps}
      width={SIZES.width}
      height={SIZES.height}
      schema={CodeIntroSchema}
      defaultProps={defaultProps}
      calculateMetadata={calculateMetadata}
    />
  );
};
