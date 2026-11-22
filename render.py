#!/usr/bin/env python3
"""Cloud video renderer - runs on GitHub Actions, zero PC load."""
import os, asyncio, subprocess, re, textwrap
from PIL import Image, ImageDraw, ImageFont

WORK = os.getcwd()
OUT = os.path.join(WORK, "output")
os.makedirs(OUT, exist_ok=True)

TOPIC = os.environ.get("TOPIC", "AI Agents: The Future of Work")
NARRATION = os.environ.get("NARRATION", "AI agents are changing how we work.")
VOICE = os.environ.get("VOICE", "en-US-AriaNeural")
STYLE = os.environ.get("STYLE", "motion")
W, H = 1920, 1080

def get_font(size, bold=True):
    cands = (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"])
    for c in cands:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()

def gradient(draw, top, bot):
    for y in range(H):
        t = y / H
        r = int(top[0]*(1-t) + bot[0]*t)
        g = int(top[1]*(1-t) + bot[1]*t)
        b = int(top[2]*(1-t) + bot[2]*t)
        draw.line([(0,y),(W,y)], fill=(r,g,b))

SCENES = [
    (TOPIC, "The Future of Work in 2026", (0,180,255)),
    ("What Are AI Agents?", "Autonomous systems that perceive, reason, and act", (100,200,255)),
    ("Beyond Chatbots", "They take real actions using tools and APIs", (120,220,200)),
    ("Top Use Cases", "Support, Development, Analysis, Productivity", (150,200,100)),
    ("Real-World Impact", "Faster tasks, lower costs, 24/7 availability", (200,180,80)),
    ("Challenges", "Reliability, privacy, human oversight needed", (220,120,80)),
    ("The Future", "Is Agentic - arriving faster than you think", (180,100,255)),
]

# Generate scene images
for i, (title, sub, accent) in enumerate(SCENES, 1):
    img = Image.new("RGB", (W,H))
    d = ImageDraw.Draw(img)
    gradient(d, (5,10,30), (0,0,0))
    d.rectangle([(80, H//2-130),(W-80, H//2-120)], fill=accent)
    ft = get_font(72, True)
    bbox = d.textbbox((0,0), title, font=ft)
    d.text(((W-(bbox[2]-bbox[0]))//2, H//2-80), title, font=ft, fill=(255,255,255))
    fs = get_font(36, False)
    bbox2 = d.textbbox((0,0), sub, font=fs)
    d.text(((W-(bbox2[2]-bbox2[0]))//2, H//2+20), sub, font=fs, fill=(180,180,200))
    d.text((W-120, H-60), f"{i}/{len(SCENES)}", font=get_font(28,False), fill=(100,100,120))
    img.save(os.path.join(WORK, f"slide{i}.png"))
    print(f"Slide {i} saved")

# Generate voice
async def gen_voice():
    import edge_tts
    comm = edge_tts.Communicate(NARRATION, VOICE, rate="+5%")
    await comm.save(os.path.join(WORK, "narration.mp3"))
    print("Voice saved")

asyncio.run(gen_voice())

# Get audio duration
r = subprocess.run(["ffmpeg", "-i", os.path.join(WORK, "narration.mp3")], capture_output=True, text=True)
m = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", r.stderr)
audio_dur = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)) + int(m.group(4))/100 if m else 40
print(f"Audio: {audio_dur}s")

per = audio_dur / len(SCENES)

# Build ffmpeg with zoompan + xfade
inputs = []
for i in range(1, len(SCENES)+1):
    inputs += ["-loop","1","-t",str(per),"-i", os.path.join(WORK, f"slide{i}.png")]
inputs += ["-i", os.path.join(WORK, "narration.mp3")]

parts = []
for i in range(len(SCENES)):
    parts.append(f"[{i}:v]scale=3840:2160,zoompan=z='min(zoom+0.0008,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(per*25)}:s=1920x1080:fps=25[v{i}]")

cur = "v0"
off = per - 0.5
for i in range(1, len(SCENES)):
    ol = f"xf{i}" if i < len(SCENES)-1 else "outv"
    parts.append(f"[{cur}][v{i}]xfade=transition=fade:duration=0.5:offset={off:.2f}[{ol}]")
    cur = ol
    off += per - 0.5

parts.append(f"[{len(SCENES)}:a]afade=t=in:st=0:d=0.5,afade=t=out:st={audio_dur-1}:d=1[aout]")
fc = ";".join(parts)

cmd = ["ffmpeg","-y"] + inputs + [
    "-filter_complex", fc,
    "-map","[outv]","-map","[aout]",
    "-c:v","libx264","-preset","medium","-crf","23",
    "-c:a","aac","-b:a","128k",
    "-shortest", os.path.join(OUT, "video.mp4")
]
print("Rendering...")
r = subprocess.run(cmd, capture_output=True, text=True, timeout=540)
if r.returncode != 0:
    print("FFMPEG ERROR:")
    print(r.stderr[-3000:])
    raise SystemExit(1)
print("Done! Output:", os.path.join(OUT, "video.mp4"))
