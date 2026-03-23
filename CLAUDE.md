# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**vidgen** is an async Python CLI that generates short vertical videos (1080×1920, TikTok/Douyin format) from trending topics or user-specified subjects. It uses MiniMax API for LLM script generation and AI image generation, Edge-TTS for free Chinese TTS, Pillow for subtitle overlay, and FFmpeg for video composition.

## Setup & Running

```bash
# Dependencies
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# System: ffmpeg and ffprobe must be installed (brew install ffmpeg on macOS)

# Environment
cp .env.example .env
# Set MINIMAX_API_KEY and optionally MINIMAX_API_HOST in .env

# Run
python main.py                    # Auto-fetch trending topic from Weibo/Baidu
python main.py "Topic Name"       # Specific topic
python main.py "Topic" --output ./custom_output
```

## Architecture

The system is a 4-stage async pipeline in `pipelines/hot_topic.py`:

1. **Script** (`modules/script.py`) → MiniMax chat API generates a 5-scene storyboard JSON `{title, tags, scenes[{image_prompt, narration}]}`
2. **Content** (concurrent via `asyncio.gather`):
   - Images (`modules/image.py`) → 5× MiniMax image generation (9:16 ratio); falls back to text cards (`modules/card.py`) on failure
   - TTS (`modules/tts.py`) → Edge-TTS synthesizes all narrations concatenated into one MP3
3. **Subtitles** (`modules/subtitle.py`) → Pillow burns narration text onto each image (white text, black stroke, semi-transparent bar)
4. **Compose** (`modules/composer.py`) → FFmpeg assembles images with Ken Burns zoom effect + TTS audio into H.264/AAC MP4

**Key relationships:**
- `main.py` → `HotTopicPipeline` (extends `pipelines/base.py`) → `modules/*`
- `modules/providers.py` is the single MiniMax API wrapper (chat, image generation, file download)
- All artifacts are named by topic slug: `_script.json`, `_img_N.jpg`, `_cap_N.jpg`, `_tts.mp3`, `_final.mp4`
- `pipeline.py` (root) is a legacy monolithic implementation; prefer the `pipelines/` + `modules/` structure

## Key Technical Details

- **Async-first:** All stages use `asyncio`; blocking Pillow operations run via `loop.run_in_executor()`
- **Fallback chain:** Image generation failure → `card.py` generates gradient text card via FFmpeg
- **Video format:** 1080×1920 @ 25fps, each scene duration = `total_audio / num_scenes`, Ken Burns zoom capped at 1.05×
- **Chinese fonts:** On macOS uses STHeiti/Songti; Linux requires Noto Sans CJK SC
- **No tests exist** in the codebase currently
