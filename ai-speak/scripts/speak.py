import sys
import subprocess
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from pathlib import Path

# 默认 Server 端口
SERVER_URL = "http://127.0.0.1:9888/tts"
HOME_DIR = Path.home()
FFPLAY_PATH = str(
    HOME_DIR
    / "AppData"
    / "Local"
    / "Microsoft"
    / "WinGet"
    / "Packages"
    / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    / "ffmpeg-8.1-full_build"
    / "bin"
    / "ffplay.exe"
)
# 临时文件存放
OUTPUT_DIR = str(HOME_DIR / "GPT-SoVITS" / "output")

def speak(text):
    if not text:
        return

    try:
        query = urlencode({"text": text})
        with urlopen(f"{SERVER_URL}?{query}", timeout=30) as response:
            audio_bytes = response.read()

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        wav_path = os.path.join(OUTPUT_DIR, "ai_voice_skill.wav")
        with open(wav_path, "wb") as f:
            f.write(audio_bytes)

        # 静默播放
        subprocess.run([FFPLAY_PATH, "-nodisp", "-autoexit", wav_path], capture_output=True)
        print("Success: AI is speaking the provided text.")
    except HTTPError as e:
        print(f"Error: TTS Server returned status code {e.code}")
    except (URLError, TimeoutError):
        print(f"Error: Could not connect to TTS Server at {SERVER_URL}. Is 'python server.py' running in the GPT-SoVITS directory?")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        speak(" ".join(sys.argv[1:]))
    else:
        print("Usage: python speak.py <text>")
