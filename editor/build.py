"""Rebuild film.mp4 from edit.json. Needs python3 and ffmpeg. Made by Nathaniel (AI agent).
Sources are fetched once from Wikimedia Commons into ./sources (CC0 / public domain)."""
import json, os, subprocess, urllib.request, sys
E = json.load(open("edit.json"))
W, H, FPS = E["format"]["width"], E["format"]["height"], E["format"]["fps"]
os.makedirs("sources", exist_ok=True); os.makedirs("work", exist_ok=True)
def fetch(item):
    p = os.path.join("sources", item["source"])
    if not os.path.exists(p):
        req = urllib.request.Request(item["source_url"], headers={"user-agent": "Nathaniel-agent/1.0 (rebuild of a CC0 edit)"})
        with urllib.request.urlopen(req) as r, open(p, "wb") as f: f.write(r.read())
    return p
def run(*a): subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)
parts = []
for c in E["cuts"]:
    src = fetch(c); out = f"work/{c['index']:02d}.mp4"
    # 9:16 crop from a landscape source (crop_x = horizontal centre of the crop, 0..1), or plain scale for a vertical source
    frame = (f"crop='min(iw,ih*9/16)':ih:'(iw-min(iw,ih*9/16))*{c['crop_x']}':0,scale={W}:{H}:flags=lanczos,setsar=1")
    chain = f"setpts=(PTS-STARTPTS)/{c['speed']},fps={FPS},{frame}"
    if c["reverse"]: chain = f"setpts=(PTS-STARTPTS)/{c['speed']},fps={FPS},scale=-2:{H},reverse,{frame}"
    run("-ss", str(c["source_in"]), "-to", str(c["source_out"]), "-i", src, "-an", "-vf", chain,
        "-frames:v", str(c["frames"]), "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", "-r", str(FPS), out)
    parts.append(out)
with open("work/list.txt", "w") as f: f.writelines(f"file '{os.path.basename(p)}'\n" for p in parts)
run("-f", "concat", "-safe", "0", "-i", "work/list.txt", "-c", "copy", "work/video.mp4")
m = E["music"]; msrc = fetch(m); D = E["duration_s"]
af = (f"atrim=0:{D},asetpts=PTS-STARTPTS,aresample=48000,volume={m['gain_db']}dB,"
      f"afade=t=in:d={m['fade_in_s']},afade=t=out:st={D - m['fade_out_s']}:d={m['fade_out_s']},alimiter=limit=0.79:level=false")
run("-i", "work/video.mp4", "-ss", str(m["source_in"]), "-i", msrc, "-filter_complex", f"[1:a]{af}[a]", "-map", "0:v", "-map", "[a]",
    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), "-profile:v", "high",
    "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-t", str(D), "-movflags", "+faststart", "film.mp4")
print("film.mp4 written")
