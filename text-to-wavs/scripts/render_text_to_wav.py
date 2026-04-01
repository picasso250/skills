#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_GPT_SOVITS_ROOT = Path(r"C:\Users\MECHREV\github\RVC-Boss\GPT-SoVITS")
MODEL_NAME = "刘亦菲"
GPT_PATH = "GPT_weights_v2/liuyifei-e15.ckpt"
SOVITS_PATH = "SoVITS_weights_v2/liuyifei_SoVITS.pth"
REF_WAV_PATH = "output/sliced/刘亦菲听她说话是一种治愈.m4a_0002868480_0003070400.wav"
LANGUAGE = "中文"
HOW_TO_CUT = "不切"
SAMPLE_STEPS = 32
REEXEC_ENV_KEY = "TEXT_TO_WAVS_REEXEC"
FUNASR_ASR_MODEL_DIR = Path(
    r"C:\Users\MECHREV\.cache\modelscope\hub\models\iic\speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
)
FUNASR_ASR_MODEL_ID = "iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
FUNASR_VAD_DIR = "tools/asr/models/speech_fsmn_vad_zh-cn-16k-common-pytorch"
FUNASR_PUNC_DIR = "tools/asr/models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate wav + subtitle files from raw text."
    )
    parser.add_argument("--text-file", required=True, help="Path to UTF-8 raw text file")
    parser.add_argument("--output-dir", help="Output directory for wav/srt/json; defaults to a temp directory")
    parser.add_argument("--output-basename", default="tts_output", help="Base name for wav/srt/json outputs")
    parser.add_argument(
        "--gpt-sovits-root",
        default=str(DEFAULT_GPT_SOVITS_ROOT),
        help="Path to GPT-SoVITS root",
    )
    return parser.parse_args()


def clean_synthesis_text(raw_text: str) -> str:
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = text.replace("\n", "")
    return text.strip()


def ensure_output_dir(output_dir: str | None) -> Path:
    if output_dir:
        out = Path(output_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)
        return out
    return Path(tempfile.mkdtemp(prefix="text-to-wav-")).resolve()


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
    result = subprocess.run([str(venv_python), *sys.argv], env=env)
    raise SystemExit(result.returncode)


def setup_gpt_sovits(root_dir: Path):
    root_dir = root_dir.resolve()
    if not root_dir.exists():
        raise RuntimeError(f"GPT-SoVITS root not found: {root_dir}")
    if not (root_dir / "server.py").exists():
        raise RuntimeError(f"server.py not found under GPT-SoVITS root: {root_dir}")

    os.chdir(root_dir)
    gpt_sovits_dir = root_dir / "GPT_SoVITS"
    sys.path.insert(0, str(root_dir))
    sys.path.insert(0, str(gpt_sovits_dir))

    root_dir_str = str(root_dir).replace("\\", "/")
    os.environ["bert_path"] = f"{root_dir_str}/GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large"
    os.environ["cnhubert_base_path"] = f"{root_dir_str}/GPT_SoVITS/pretrained_models/chinese-hubert-base"
    os.environ["version"] = "v2"
    os.environ["gpt_path"] = GPT_PATH
    os.environ["sovits_path"] = SOVITS_PATH

    import soundfile as sf
    import GPT_SoVITS.feature_extractor.cnhubert as cnhubert
    import torchaudio
    from GPT_SoVITS.inference_webui import change_gpt_weights, change_sovits_weights, get_tts_wav

    cnhubert.cnhubert_base_path = os.environ["cnhubert_base_path"]
    try:
        torchaudio.set_audio_backend("soundfile")
    except Exception:
        pass
    return sf, change_gpt_weights, change_sovits_weights, get_tts_wav


def load_model(change_gpt_weights, change_sovits_weights) -> None:
    print(f"Loading {MODEL_NAME} model...")
    change_gpt_weights(GPT_PATH)
    for _ in change_sovits_weights(SOVITS_PATH, prompt_language=LANGUAGE, text_language=LANGUAGE):
        pass
    print(f"{MODEL_NAME} model loaded.")


def build_acoustic_timeline(gpt_sovits_root: Path, wav_file: Path) -> list[dict]:
    try:
        from funasr import AutoModel
    except Exception as exc:
        raise RuntimeError(f"Failed to import FunASR in GPT-SoVITS venv: {exc}") from exc

    model_ref = str(FUNASR_ASR_MODEL_DIR) if FUNASR_ASR_MODEL_DIR.exists() else FUNASR_ASR_MODEL_ID
    vad_ref = str((gpt_sovits_root / FUNASR_VAD_DIR).resolve())
    punc_ref = str((gpt_sovits_root / FUNASR_PUNC_DIR).resolve())

    asr_model = AutoModel(
        model=model_ref,
        vad_model=vad_ref,
        punc_model=punc_ref,
    )
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
        records.append(
            {
                "start_sec": start_sec,
                "end_sec": end_sec,
                "text": text,
            }
        )

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


def write_json(path: Path, records: list[dict]) -> None:
    output = []
    for idx, item in enumerate(records, start=1):
        output.append(
            {
                "index": idx,
                "start_sec": round(float(item["start_sec"]), 3),
                "end_sec": round(float(item["end_sec"]), 3),
                "text": str(item["text"]),
            }
        )
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


def write_asr_text(path: Path, records: list[dict]) -> None:
    lines = [str(item["text"]) for item in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    text_file = Path(args.text_file).resolve()
    output_dir = ensure_output_dir(args.output_dir)

    if not text_file.exists():
        print(f"ERROR: text file not found: {text_file}")
        return 1

    raw_text = text_file.read_text(encoding="utf-8")
    synth_text = clean_synthesis_text(raw_text)
    if not synth_text:
        print("ERROR: synthesis text is empty")
        return 1

    base = args.output_basename
    wav_file = output_dir / f"{base}.wav"
    srt_path = output_dir / f"{base}.srt"
    json_path = output_dir / f"{base}.segments.json"
    asr_text_path = output_dir / f"{base}.asr.txt"

    try:
        gpt_sovits_root = Path(args.gpt_sovits_root)
        maybe_reexec_in_gpt_venv(gpt_sovits_root)
        sf, change_gpt_weights, change_sovits_weights, get_tts_wav = setup_gpt_sovits(gpt_sovits_root)
        load_model(change_gpt_weights, change_sovits_weights)

        result_list = list(
            get_tts_wav(
                ref_wav_path=REF_WAV_PATH,
                prompt_text="",
                prompt_language=LANGUAGE,
                text=synth_text,
                text_language=LANGUAGE,
                ref_free=True,
                sample_steps=SAMPLE_STEPS,
                how_to_cut=HOW_TO_CUT,
            )
        )
        if not result_list:
            raise RuntimeError("TTS returned no audio")
        sampling_rate, audio_data = result_list[-1]
        sf.write(wav_file, audio_data, sampling_rate)

        records = build_acoustic_timeline(gpt_sovits_root, wav_file)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    write_srt(srt_path, records)
    write_json(json_path, records)
    write_asr_text(asr_text_path, records)

    print(f"OUTPUT_DIR:{output_dir}")
    print(f"OUTPUT_WAV:{wav_file}")
    print(f"OUTPUT_SRT:{srt_path}")
    print(f"OUTPUT_SEGMENTS_JSON:{json_path}")
    print(f"OUTPUT_ASR_TEXT:{asr_text_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
