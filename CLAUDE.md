# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**vidgen** is an async Python CLI that generates short vertical videos (1080x1920, TikTok/Douyin format). Two pipelines:

1. **hot_topic** — auto-fetch trending topics, generate narrated video with AI images
2. **code_intro** — analyze a code project, generate an intro/promo video with animated React scenes (Remotion)

Uses MiniMax API for LLM + AI images, Edge-TTS for Chinese TTS, Remotion (React) for high-quality video rendering.

## Setup & Running

```bash
# Python dependencies
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Remotion dependencies (required for code_intro pipeline)
cd remotion && npm install && cd ..

# System: ffmpeg and ffprobe (brew install ffmpeg on macOS)

# Environment
cp .env.example .env
# Set MINIMAX_API_KEY and optionally MINIMAX_API_HOST in .env

# Run
python main.py                                          # Trending topic video
python main.py "Topic Name"                             # Specific topic
python main.py --pipeline code_intro /path/to/project   # Code intro video
python main.py --pipeline code_intro /path --scenes 5   # Custom scene count
```

## Architecture

### hot_topic pipeline (4-stage, Pillow+FFmpeg)

```
[Script] → [Images + TTS] → [Subtitle overlay] → [FFmpeg compose] → MP4
```

### code_intro pipeline (5-stage, Remotion)

```
[Code analysis] → [Competitor research] → [Script generation]
  → [AI images + TTS] → [Remotion render] → MP4
```

Remotion renders all visual scenes as React components:
- `TitleScene` — spring bounce-in + tech stack tags
- `AIImageScene` — Ken Burns zoom + gradient mask
- `CodeScene` — terminal window + syntax highlight + line-by-line reveal
- `DataScene` — 2x2 metrics grid + count-up animation
- `ArchScene` — directory tree with typewriter effect
- `EndingScene` — CTA pulse animation
- Scene transitions: fade (20 frames)
- Subtitles: per-line spring entrance animation

### Key files

```
main.py                         CLI entry point
pipelines/
  base.py                       Abstract BasePipeline
  hot_topic.py                  Trending topic → Pillow+FFmpeg
  code_intro.py                 Code project → Remotion
modules/
  providers.py                  MiniMax API wrapper (chat, image)
  script.py                     LLM script generation + validation
  code_analyzer.py              Project introspection (LOC, deps, structure)
  competitor.py                 Competitor research via LLM
  remotion_render.py            Python→Remotion bridge (props.json + CLI)
  image.py / tts.py             AI image gen / Edge-TTS
  composer.py                   FFmpeg video composition
  subtitle.py / visual_cards.py Pillow-based rendering (hot_topic)
remotion/
  src/index.ts                  Remotion entry point
  src/Root.tsx                  Composition registration + calculateMetadata
  src/CodeIntro.tsx             Main composition (TransitionSeries + Audio)
  src/types.ts                  Zod schemas for props
  src/theme.ts                  Colors, fonts, sizes
  src/scenes/*.tsx              6 scene components
  src/components/*.tsx          Background, Subtitle, SceneTransition
```

## Key Technical Details

- **Async-first:** All stages use `asyncio`; blocking ops in `run_in_executor()`
- **Remotion rendering:** Python writes `props.json` (camelCase), copies assets to `remotion/public/assets/`, calls `npx remotion render`; assets cleaned up after render
- **Asset serving:** Remotion serves files from `public/` via `staticFile()`. Audio/images are staged there temporarily.
- **Dynamic duration:** `calculateMetadata` in Root.tsx sets video length from `audioDuration` prop
- **Video format:** 1080x1920 @ 25fps, H.264/AAC
- **Chinese fonts:** Uses system fonts (PingFang SC on macOS, Noto Sans CJK on Linux)
- **No tests exist** in the codebase currently
