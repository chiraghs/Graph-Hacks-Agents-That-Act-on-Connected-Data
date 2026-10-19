import glob
import json
import os
import subprocess

raw_files = glob.glob("video_build/raw_video/*.webm")
if not raw_files:
    raise FileNotFoundError("Raw video WebM not found in video_build/raw_video/")

raw_webm = raw_files[0]
audio_wav = "video_build/master_narration.wav"
output_mp4 = "twinforge_connected_graph_walkthrough_demo.mp4"

print(f"Input video: {raw_webm}")
print(f"Input audio: {audio_wav}")
print(f"Output MP4:  {output_mp4}")

cmd = [
    "ffmpeg", "-y",
    "-i", raw_webm,
    "-i", audio_wav,
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "22",
    "-pix_fmt", "yuv420p",
    "-r", "30",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    output_mp4
]

print("Running ffmpeg multiplexing & encoding...")
subprocess.run(cmd, check=True)

import shutil
shutil.copy(output_mp4, os.path.join("static", output_mp4))

# Probe final MP4
probe_cmd = [
    "ffprobe", "-v", "error",
    "-show_entries", "format=duration,size,bit_rate",
    "-show_streams",
    "-of", "json", output_mp4
]
res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
info = json.loads(res.stdout)

dur = float(info["format"]["duration"])
size_mb = int(info["format"]["size"]) / (1024 * 1024)

print("\n" + "="*50)
print("FINAL VIDEO PRODUCTION COMPLETE")
print("="*50)
print(f"File Path: {os.path.abspath(output_mp4)}")
print(f"Static URL Path: http://localhost:8000/static/{output_mp4}")
print(f"Duration:  {dur:.2f} seconds ({dur/60:.2f} minutes)")
print(f"Size:      {size_mb:.2f} MB")
print("="*50)
