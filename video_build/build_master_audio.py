import json
import subprocess
import os

with open("video_build/scenes.json", "r") as f:
    scenes = json.load(f)

# Generate 0.5s silence wav
silence_path = "video_build/audio/silence_05.wav"
subprocess.run([
    "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
    "-t", "0.5", silence_path
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# Create ffmpeg concat file
concat_txt = "video_build/audio/concat_list.txt"
timeline = []
current_time = 0.0

with open(concat_txt, "w") as f:
    for i, s in enumerate(scenes):
        s_wav = os.path.abspath(f"video_build/audio/{s['id']}.wav")
        f.write(f"file '{s_wav}'\n")
        timeline.append({
            "id": s["id"],
            "title": s["title"],
            "start": current_time,
            "duration": s["duration"],
            "end": current_time + s["duration"]
        })
        current_time += s["duration"]
        if i < len(scenes) - 1:
            sil_wav = os.path.abspath(silence_path)
            f.write(f"file '{sil_wav}'\n")
            current_time += 0.5

# Concatenate audio
master_audio = "video_build/master_narration.wav"
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt,
    "-c", "copy", master_audio
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# Probe master audio duration
res = subprocess.run([
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "json", master_audio
], capture_output=True, text=True, check=True)
master_dur = float(json.loads(res.stdout)["format"]["duration"])

print(f"Master Narration Audio generated: {master_audio}")
print(f"Total Duration: {master_dur:.2f}s (~{master_dur/60:.2f} minutes)")

with open("video_build/timeline.json", "w") as f:
    json.dump({
        "total_duration": master_dur,
        "scenes": timeline
    }, f, indent=2)

for item in timeline:
    print(f"  [{item['id']}] {item['start']:.1f}s -> {item['end']:.1f}s ({item['duration']:.1f}s): {item['title']}")
