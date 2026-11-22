# Video Render Pipeline (Cloud)

Zero-PC-load video rendering using GitHub Actions + FFmpeg + edge-tts.

## How it works

1. Go to **Actions** tab → **Render Video (Cloud)** → **Run workflow**
2. Enter your topic, narration script, voice, and style
3. GitHub renders the video on their servers (not your PC)
4. Download the rendered MP4 from the workflow artifacts

## Free limits
- **GitHub Actions:** 2,000 min/month (public repo) — a 40s video takes ~2 min to render
- **edge-tts:** Free Microsoft neural voices, no quota
- **FFmpeg:** Pre-installed on ubuntu-latest runners

## Voices available (edge-tts)
- en-US-AriaNeural (female, default)
- en-US-GuyNeural (male)
- en-US-JennyNeural (female)
- en-GB-SoniaNeural (British female)
- en-AU-NatashaNeural (Australian female)

## Video styles
- **motion** — Ken Burns zoom + crossfade transitions (default)
- **explainer** — Same as motion, optimized for longer content
- **shorts** — 9:16 vertical format for YouTube Shorts

## Trigger via API
You can trigger renders programmatically:
```bash
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/Ranji009/video-render-pipeline/actions/workflows/render.yml/dispatches \
  -d '{"ref":"main","inputs":{"topic":"My Topic","narration":"My script text here","voice":"en-US-AriaNeural","style":"motion"}}'
```

## Files
- `render.py` — Python render script (PIL images + edge-tts voice + FFmpeg motion)
- `.github/workflows/render.yml` — GitHub Actions workflow
