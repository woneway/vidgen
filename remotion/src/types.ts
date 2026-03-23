import { z } from "zod";

export const SceneSchema = z.object({
  narration: z.string(),
  imagePrompt: z.string(),
  visualType: z.enum([
    "title_card",
    "ai_image",
    "code_snippet",
    "data_card",
    "architecture",
    "ending_card",
  ]),
  imagePath: z.string().optional(),
});

export const AnalysisSchema = z.object({
  name: z.string(),
  description: z.string(),
  techStack: z.array(z.string()),
  totalLoc: z.number(),
  totalFiles: z.number(),
  dependencyCount: z.number(),
  testInfo: z.string(),
  githubUrl: z.string().nullable(),
  githubStats: z
    .object({
      stars: z.number(),
      forks: z.number(),
    })
    .nullable(),
  structure: z.string(),
  codeExamples: z.array(
    z.object({
      filename: z.string(),
      code: z.string(),
      language: z.string(),
    })
  ),
});

export const CodeIntroSchema = z.object({
  title: z.string(),
  tags: z.array(z.string()),
  scenes: z.array(SceneSchema),
  analysis: AnalysisSchema,
  audioPath: z.string(),
  audioDuration: z.number(),
});

export type CodeIntroProps = z.infer<typeof CodeIntroSchema>;
export type Scene = z.infer<typeof SceneSchema>;
export type Analysis = z.infer<typeof AnalysisSchema>;
