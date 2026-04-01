import argparse
import os
import subprocess
import urllib.parse
import urllib.request
import sys
import json
import shutil
from pathlib import Path

# Constants
FFMPEG_PATH = r"C:\Users\MECHREV\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
RENDER_SCRIPT = r"C:\Users\MECHREV\.agents\skills\text-to-wavs\scripts\render_text_to_wav.py"
CANVAS_RENDERER = r"C:\Users\MECHREV\.agents\skills\bilibili-video-maker\renderer\render_canvas.js"
TTS_URL = "http://127.0.0.1:9888/tts"

def parse_args():
    parser = argparse.ArgumentParser(description="Create an animated Bilibili video.")
    parser.add_argument("--text-file", required=True, help="Path to the input text file.")
    parser.add_argument("--output-dir", required=True, help="Directory to save the results.")
    parser.add_argument("--basename", default="bilibili_video", help="Basename for output files.")
    parser.add_argument("--skip-render", action="store_true", help="Skip PNG rendering if frames already exist.")
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
    
    text_path = Path(args.text_file).resolve()
    if not text_path.exists():
        print(f"Error: Text file not found: {text_path}")
        sys.exit(1)
        
    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read().strip()
        
    # 1. Generate WAV and SRT/JSON via text-to-wavs
    wav_path = output_dir / f"{args.basename}.wav"
    json_path = output_dir / f"{args.basename}.segments.json"
    
    # Paths to internal scripts
    GPT_VENV_PYTHON = r"C:\Users\MECHREV\github\RVC-Boss\GPT-SoVITS\venv\Scripts\python.exe"
    ENHANCE_SCRIPT = r"C:\Users\MECHREV\.agents\skills\bilibili-video-maker\scripts\enhance_segments.py"

    if not wav_path.exists() or not json_path.exists():
        print(f"Generating WAV and SRT/JSON data via text-to-wavs for: {text_path}")
        try:
            env = os.environ.copy()
            env["TEXT_TO_WAVS_REEXEC"] = "1"
            subprocess.run([
                GPT_VENV_PYTHON, RENDER_SCRIPT,
                "--text-file", str(text_path.absolute()),
                "--output-dir", str(output_dir.absolute()),
                "--output-basename", args.basename
            ], check=True, env=env)
        except subprocess.CalledProcessError as e:
            print(f"Error generating data: {e}")
            sys.exit(1)
            
    # 2. Enhance segments (AI cleaning/highlighting)
    print("Enhancing segments (keywords and wrapping)...")
    try:
        subprocess.run([
            sys.executable, ENHANCE_SCRIPT,
            "--json-file", str(json_path)
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error enhancing segments: {e}")
        sys.exit(1)
            
    if not wav_path.exists():
        print(f"ERROR: Expected WAV file not found at {wav_path}")
        sys.exit(1)
            
    duration = get_wav_duration(wav_path)
    
    # 3. Canvas Rendering (PNG Sequence)
    frames_dir = output_dir / "frames"
    if not args.skip_render:
        print(f"Starting Canvas Renderer (JS)...")
        try:
            subprocess.run([
                "node", CANVAS_RENDERER,
                str(json_path),
                str(duration),
                str(output_dir)
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error in JS renderer: {e}")
            sys.exit(1)

    # 4. Assemble Video via FFmpeg
    print("Assembling video from PNG sequence...")
    video_path = output_dir / f"{args.basename}_animated.mp4"
    
    ffmpeg_cmd = [
        FFMPEG_PATH,
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
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        print(f"Success! Animated video created at: {video_path}")
        # Optional: cleanup frames to save space
        # shutil.rmtree(frames_dir)
    except subprocess.CalledProcessError as e:
        print(f"Error assembling video: {e.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    main()
