import argparse
import os
import subprocess
import sys
import json
from pathlib import Path

# Constants
FFMPEG_PATH = Path.home() / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1-full_build/bin/ffmpeg.exe"
CANVAS_RENDERER = Path.home() / ".agents/skills/bilibili-video-maker/renderer/render_canvas.js"

def parse_args():
    parser = argparse.ArgumentParser(description="PURE RENDERER: Create video from existing assets.")
    parser.add_argument("--wav-file", required=True, help="Path to the source audio.")
    parser.add_argument("--json-file", required=True, help="Path to the cleaned segments JSON.")
    parser.add_argument("--output-dir", required=True, help="Where to save the result.")
    parser.add_argument("--basename", default="final_result", help="Output filename base.")
    return parser.parse_args()

def get_wav_duration(wav_path):
    import wave
    with wave.open(str(wav_path), 'rb') as f:
        frames = f.getnframes()
        rate = f.getframerate()
        return frames / float(rate)

def main():
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    wav_path = Path(args.wav_file).resolve()
    json_path = Path(args.json_file).resolve()
    
    if not wav_path.exists():
        print(f"Error: WAV not found: {wav_path}")
        sys.exit(1)
    if not json_path.exists():
        print(f"Error: JSON not found: {json_path}")
        sys.exit(1)

    duration = get_wav_duration(wav_path)
    frames_dir = output_dir / "frames"
    
    # Step 1: Canvas Rendering
    print(f"Rendering frames using {json_path} (Duration: {duration:.2f}s)...")
    try:
        subprocess.run([
            "node", str(CANVAS_RENDERER),
            str(json_path.absolute()),
            str(duration),
            str(output_dir.absolute())
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error in JS renderer: {e}")
        sys.exit(1)

    # Step 2: FFmpeg Assembly
    print("Assembling video...")
    video_path = output_dir / f"{args.basename}.mp4"
    if video_path.exists():
        video_path.unlink()

    ffmpeg_cmd = [
        str(FFMPEG_PATH),
        "-framerate", "30",
        "-i", str(frames_dir / "frame_%05d.png"),
        "-i", str(wav_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        "-y",
        str(video_path)
    ]
    
    try:
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        print(f"\nSUCCESS! Video created at: {video_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error assembling video: {e.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    main()
