#!/usr/bin/env python3
"""Shorts builder: real browser screen-recording of a free tool + TTS + captions."""
import os, re, json, subprocess, asyncio, urllib.parse, urllib.request, shutil, sys
from pathlib import Path

OUT = Path("output"); OUT.mkdir(exist_ok=True)
WORK = Path("work"); WORK.mkdir(exist_ok=True)
REC = WORK / "rec"; REC.mkdir(exist_ok=True)

PROMPT = os.environ.get("PROMPT", "cyberpunk cat in neon Tokyo, cinematic lighting, 4k")
NARRATION = os.environ.get("NARRATION", "Most people pay twenty dollars a month for AI images. This does it for free.")
VOICE = os.environ.get("VOICE", "en-US-AriaNeural")
HOOK = os.environ.get("HOOK", "100% FREE AI IMAGES")
SITE = os.environ.get("SITE", "https://deepai.org/machine-learning-model/text2img")
W, H, FPS = 1080, 1920, 30

def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)

def dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

async def tts(text, path):
    import edge_tts
    c = edge_tts.Communicate(text, VOICE, rate="+6%")
    await c.save(str(path))
asyncio.run(tts(NARRATION, WORK/"voice.mp3"))
D = dur(WORK/"voice.mp3")
print("voice duration", D, flush=True)

found_image = False
shot = WORK/"shot.png"
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(viewport={"width":W,"height":H}, record_video_dir=str(REC),
                            record_video_size={"width":W,"height":H},
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
                            locale="en-US")
        pg = ctx.new_page()
        pg.goto(SITE, wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_timeout(2500)
        print("title:", pg.title(), flush=True)
        pg.screenshot(path=str(WORK/"debug1.png"))
        before = pg.evaluate("() => document.images.length")
        box = None
        for sel in ["textarea","input[type=text]","input:not([type])","[contenteditable=true]"]:
            for el in pg.query_selector_all(sel):
                try:
                    if el.is_visible() and el.bounding_box():
                        box = el; break
                except Exception:
                    pass
            if box: break
        if box:
            box.click()
            pg.wait_for_timeout(300)
            pg.keyboard.type(PROMPT, delay=45)
            pg.wait_for_timeout(500)
            clicked = False
            for name in ["generate","create","run","submit","make","draw"]:
                try:
                    btn = pg.get_by_role("button", name=re.compile(name, re.I)).first
                    if btn.count() and btn.is_visible():
                        btn.click(); clicked = True
                        print("clicked button:", name, flush=True)
                        break
                except Exception:
                    pass
            if not clicked:
                pg.keyboard.press("Enter")
                print("pressed enter", flush=True)
            for _ in range(60):
                pg.wait_for_timeout(1000)
                ok = pg.evaluate("""(b) => [...document.images].some(i => i.naturalWidth > 380 && i.src && !i.src.includes('icon')) || document.images.length > b + 1""", before)
                if ok:
                    found_image = True; break
            print("found_image", found_image, flush=True)
            if found_image:
                try:
                    el = pg.evaluate_handle("""() => { let best=null,area=0; for (const i of document.images){ const r=i.getBoundingClientRect(); const a=r.width*r.height; if(r.width>200 && a>area){area=a;best=i;} } return best; }""").as_element()
                    if el:
                        el.scroll_into_view_if_needed()
                        pg.wait_for_timeout(2500)
                        el.screenshot(path=str(shot))
                        print("shot saved", shot.stat().st_size, flush=True)
                except Exception as e:
                    print("shot err", e, flush=True)
                pg.wait_for_timeout(2500)
            else:
                pg.wait_for_timeout(1500)
        else:
            print("no input box found", flush=True)
        pg.wait_for_timeout(1200)
        pg.screenshot(path=str(WORK/"debug2.png"))
        ctx.close(); b.close()
except Exception as e:
    print("RECORD ERROR:", e, flush=True)

vids = sorted(REC.glob("*.webm"))
rec = vids[0] if vids else None
print("recording:", rec, flush=True)

img = None
if shot.exists():
    img = shot
else:
    try:
        img = WORK/"result.jpg"
        url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(PROMPT) + "?width=1080&height=1350&nologo=true&seed=42"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(img,"wb") as f:
            f.write(r.read())
        print("payoff image bytes", img.stat().st_size, flush=True)
    except Exception as e:
        print("IMAGE ERROR:", e, flush=True)
        img = None

card = WORK/"card.png"
if img and img.exists():
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(img).convert("RGB")
    scale = max(W/im.width, H/im.height)
    im = im.resize((int(im.width*scale), int(im.height*scale)), Image.LANCZOS)
    left = (im.width-W)//2; top = (im.height-H)//2
    im = im.crop((left, top, left+W, top+H))
    ov = Image.new("RGBA", (W,H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    d.rectangle([0, H-520, W, H], fill=(0,0,0,200))
    def font(sz, bold=True):
        c = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        return ImageFont.truetype(c, sz) if os.path.exists(c) else ImageFont.load_default()
    f1, f2 = font(54), font(42, False)
    lines=[]; cur=""
    for wd in PROMPT.split():
        t = (cur+" "+wd).strip()
        if d.textlength(t, font=f1) > W-120:
            lines.append(cur); cur=wd
        else: cur=t
    if cur: lines.append(cur)
    y = H-470
    for ln in lines[:3]:
        d.text((60,y), ln, font=f1, fill=(255,255,255,255)); y += 68
    d.text((60, H-150), "FREE  -  NO SIGNUP  -  INSTANT", font=f2, fill=(255,214,0,255))
    im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    im.save(card)
    print("card made", flush=True)

seg1 = WORK/"seg1.mp4"; seg2 = WORK/"seg2.mp4"
payoff = 6.5
main_len = max(D - payoff + 1.0, 8.0)

if rec:
    run(["ffmpeg","-y","-stream_loop","-1","-i",rec,"-t",f"{main_len:.2f}",
         "-vf",f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
         "-an","-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p",seg1])
else:
    run(["ffmpeg","-y","-f","lavfi","-i",f"color=c=0x0b0b12:s={W}x{H}:d={main_len:.2f}:r={FPS}",
         "-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p",seg1])

if card.exists():
    run(["ffmpeg","-y","-loop","1","-i",card,"-t",f"{payoff:.2f}",
         "-vf",f"scale={int(W*1.18)}:{int(H*1.18)},zoompan=z='min(zoom+0.0009,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(payoff*FPS)}:s={W}x{H}:fps={FPS},format=yuv420p",
         "-c:v","libx264","-preset","veryfast","-crf","21",seg2])
else:
    run(["ffmpeg","-y","-f","lavfi","-i",f"color=c=0x0b0b12:s={W}x{H}:d={payoff:.2f}:r={FPS}",
         "-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p",seg2])

def ass_time(t):
    h=int(t//3600); m=int(t%3600//60); s=t%60
    return f"{h}:{m:02d}:{s:05.2f}"

def chunks(text, n=7):
    words = text.split(); out=[]
    for i in range(0,len(words),n):
        out.append(" ".join(words[i:i+n]))
    return out

parts = chunks(NARRATION)
weights = [max(len(p),8) for p in parts]
tw = sum(weights); t0 = 0.3
events = []
for p,wt in zip(parts,weights):
    span = (D-0.7) * wt / tw
    events.append((t0, min(t0+span, D+0.5), p)); t0 += span

head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,62,&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,7,0,2,60,60,300,1
Style: Hook,DejaVu Sans,86,&H0000E6FF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,8,0,5,50,50,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
body = ["Dialogue: 0," + ass_time(0.0) + "," + ass_time(2.8) + ",Hook,,0,0,0,,{\\an5\\pos(540,300)}" + HOOK]
for a,b,txt in events:
    txt = txt.replace("{","(").replace("}","").replace("\n"," ")
    body.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Cap,,0,0,0,,{txt}")
(WORK/"captions.ass").write_text(head + "\n".join(body), encoding="utf-8")

with open(WORK/"list.txt","w") as f:
    f.write("file '" + str(seg1.resolve()) + "'\nfile '" + str(seg2.resolve()) + "'\n")
run(["ffmpeg","-y","-f","concat","-safe","0","-i",WORK/"list.txt","-c","copy",WORK/"base.mp4"])

run(["ffmpeg","-y","-i",WORK/"base.mp4","-i",WORK/"voice.mp3",
     "-vf","ass=" + str(WORK/"captions.ass"),
     "-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
     "-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",
     OUT/"short.mp4"])

for t in (1.5, 5, 9, 14, 19, 24):
    try:
        subprocess.run(["ffmpeg","-y","-ss",str(t),"-i",str(OUT/"short.mp4"),"-frames:v","1","-q:v","3",str(WORK/f"frame_{t}.jpg")], check=False)
    except Exception:
        pass
print("DONE", (OUT/"short.mp4").stat().st_size, flush=True)
