#!/usr/bin/env python3
import argparse
import contextlib
import os
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

HOME_DIR = Path.home()
DEFAULT_GPT_SOVITS_ROOT = HOME_DIR / "github" / "RVC-Boss" / "GPT-SoVITS"
REEXEC_ENV_KEY = "AUDIO_TO_SRT_REEXEC"
FUNASR_ASR_MODEL_DIR = Path(
    HOME_DIR
    / ".cache"
    / "modelscope"
    / "hub"
    / "models"
    / "iic"
    / "speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
)
FUNASR_ASR_MODEL_ID = "iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
FUNASR_VAD_DIR = "tools/asr/models/speech_fsmn_vad_zh-cn-16k-common-pytorch"
FUNASR_PUNC_DIR = "tools/asr/models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate srt timeline and ASR text from input audio.")
    parser.add_argument("--audio-file", required=True, help="Input audio file path, supports wav/mp3.")
    parser.add_argument("--output-dir", help="Output directory, defaults to a temp directory.")
    parser.add_argument("--output-basename", required=True, help="Output basename for srt/asr artifacts.")
    parser.add_argument(
        "--gpt-sovits-root",
        default=str(DEFAULT_GPT_SOVITS_ROOT),
        help="Path to GPT-SoVITS root",
    )
    parser.add_argument("--ffmpeg-bin", default="ffmpeg", help="ffmpeg executable name/path.")
    parser.add_argument("--verbose", action="store_true", help="Print raw FunASR progress and warnings.")
    return parser.parse_args()


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


@contextlib.contextmanager
def quiet_external_output(enabled: bool):
    if not enabled:
        yield
        return

    with open(os.devnull, "w", encoding="utf-8") as sink:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                yield


def ensure_output_dir(output_dir: str | None) -> Path:
    if output_dir:
        out = Path(output_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)
        return out
    return Path(tempfile.mkdtemp(prefix="audio-to-srt-")).resolve()


def maybe_reexec_in_gpt_venv(root_dir: Path) -> None:
    venv_python = root_dir / "venv" / "Scripts" / "python.exe"
    if os.environ.get(REEXEC_ENV_KEY) == "1":
        return
    if not venv_python.exists():
        return
    if Path(sys.executable).resolve() == venv_python.resolve():
        return
    env = os.environ.copy()
    env[REEXEC_ENV_KEY] = "1"
    env.setdefault("PYTHONUTF8", "1")
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run([str(venv_python), *sys.argv], env=env)
    raise SystemExit(result.returncode)


def convert_to_wav_if_needed(audio_file: Path, ffmpeg_bin: str) -> tuple[Path, Path | None]:
    if audio_file.suffix.lower() == ".wav":
        return audio_file, None
    tmp_wav = Path(tempfile.mkdtemp(prefix="audio-to-srt-convert-")) / f"{audio_file.stem}.wav"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(audio_file),
        "-ar",
        "16000",
        "-ac",
        "1",
        str(tmp_wav),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg convert failed: {stderr}")
    return tmp_wav, tmp_wav.parent


def build_acoustic_timeline(gpt_sovits_root: Path, wav_file: Path, verbose: bool = False) -> list[dict]:
    with quiet_external_output(not verbose):
        try:
            from funasr import AutoModel
        except Exception as exc:
            raise RuntimeError(f"Failed to import FunASR in GPT-SoVITS venv: {exc}") from exc

        model_ref = str(FUNASR_ASR_MODEL_DIR) if FUNASR_ASR_MODEL_DIR.exists() else FUNASR_ASR_MODEL_ID
        vad_ref = str((gpt_sovits_root / FUNASR_VAD_DIR).resolve())
        punc_ref = str((gpt_sovits_root / FUNASR_PUNC_DIR).resolve())
        asr_model = AutoModel(model=model_ref, vad_model=vad_ref, punc_model=punc_ref)

        result = asr_model.generate(
            input=str(wav_file),
            sentence_timestamp=True,
            return_raw_text=True,
        )
    if not result:
        raise RuntimeError("FunASR returned empty result")

    sentence_info = result[0].get("sentence_info") or []
    records: list[dict] = []
    for item in sentence_info:
        text = (item.get("text") or "").strip()
        start_ms = item.get("start")
        end_ms = item.get("end")
        if not text:
            continue
        if start_ms is None or end_ms is None:
            continue
        start_sec = max(0.0, float(start_ms) / 1000.0)
        end_sec = max(start_sec, float(end_ms) / 1000.0)
        records.append({"start_sec": start_sec, "end_sec": end_sec, "text": text})

    if not records:
        raise RuntimeError("FunASR returned no sentence_info timestamps")
    return records


def format_srt_time(seconds: float) -> str:
    ms_total = int(round(max(0.0, seconds) * 1000.0))
    hours = ms_total // 3600000
    ms_total %= 3600000
    minutes = ms_total // 60000
    ms_total %= 60000
    secs = ms_total // 1000
    millis = ms_total % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(path: Path, records: list[dict]) -> None:
    lines: list[str] = []
    for idx, item in enumerate(records, start=1):
        start = float(item["start_sec"])
        end = float(item["end_sec"])
        lines.append(str(idx))
        lines.append(f"{format_srt_time(start)} --> {format_srt_time(end)}")
        lines.append(str(item["text"]))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_asr_text(path: Path, records: list[dict]) -> None:
    lines = [str(item["text"]) for item in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    configure_stdio()
    args = parse_args()
    audio_file = Path(args.audio_file).resolve()
    if not audio_file.exists():
        print(f"ERROR: audio file not found: {audio_file}")
        return 1

    output_dir = ensure_output_dir(args.output_dir)
    base = args.output_basename
    srt_path = output_dir / f"{base}.srt"
    asr_text_path = output_dir / f"{base}.asr.txt"

    try:
        gpt_sovits_root = Path(args.gpt_sovits_root).resolve()
        maybe_reexec_in_gpt_venv(gpt_sovits_root)
        wav_for_asr, tmp_dir = convert_to_wav_if_needed(audio_file, args.ffmpeg_bin)
        records = build_acoustic_timeline(gpt_sovits_root, wav_for_asr, verbose=args.verbose)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        if "tmp_dir" in locals() and tmp_dir and tmp_dir.exists():
            try:
                for child in tmp_dir.iterdir():
                    child.unlink(missing_ok=True)
                tmp_dir.rmdir()
            except Exception:
                pass

    write_srt(srt_path, records)
    write_asr_text(asr_text_path, records)

    print(f"OK:{output_dir}")
    print(f"SRT:{srt_path}")
    print(f"ASR_TEXT:{asr_text_path}")
    print(f"SEGMENTS:{len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
