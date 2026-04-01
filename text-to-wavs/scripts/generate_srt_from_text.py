#!/usr/bin/env python3
import argparse
import re
import wave
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate SRT timestamps from text for an existing wav (no wav splitting)."
    )
    parser.add_argument("--text-file", required=True, help="UTF-8 text file for subtitle content")
    parser.add_argument("--wav-file", required=True, help="WAV file path used for total duration")
    parser.add_argument("--output-srt", required=True, help="Output SRT path")
    parser.add_argument(
        "--min-segment-sec",
        type=float,
        default=0.55,
        help="Minimum duration per subtitle segment when distributing timeline.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def normalize_text_for_punct_split(text: str) -> str:
    # Keep punctuation, remove layout-only newlines.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "", text)
    return text.strip()


def split_by_punctuation(text: str) -> list[str]:
    text = normalize_text_for_punct_split(text)
    if not text:
        return []

    # Chinese + English punctuation sentence split.
    parts = re.split(r"(?<=[。！？!?；;：:…])", text)
    segments = [p.strip() for p in parts if p and p.strip()]
    if not segments:
        return [text]
    return segments


def wav_duration_seconds(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def segment_weight(text: str) -> float:
    # Use visible chars as proxy for speaking time.
    chars = [ch for ch in text if not ch.isspace()]
    return max(1.0, float(len(chars)))


def distribute_durations(total_sec: float, segments: list[str], min_segment_sec: float) -> list[float]:
    if not segments:
        return []
    n = len(segments)
    if n == 1:
        return [total_sec]

    min_segment_sec = max(0.0, min_segment_sec)
    if min_segment_sec * n >= total_sec:
        # Not enough duration budget; fall back to proportional only.
        min_segment_sec = 0.0

    weights = [segment_weight(seg) for seg in segments]
    total_weight = sum(weights)
    base = [min_segment_sec] * n
    remaining = total_sec - min_segment_sec * n

    durations = [base[i] + (remaining * weights[i] / total_weight) for i in range(n)]

    # Fix floating-point drift so total matches wav duration exactly.
    drift = total_sec - sum(durations)
    durations[-1] += drift
    return durations


def format_srt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    ms_total = int(round(seconds * 1000.0))
    hours = ms_total // 3600000
    ms_total %= 3600000
    minutes = ms_total // 60000
    ms_total %= 60000
    secs = ms_total // 1000
    millis = ms_total % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(path: Path, segments: list[str], durations: list[float]) -> None:
    start = 0.0
    lines: list[str] = []
    for idx, (seg, dur) in enumerate(zip(segments, durations), start=1):
        end = start + max(0.0, dur)
        lines.append(str(idx))
        lines.append(f"{format_srt_time(start)} --> {format_srt_time(end)}")
        lines.append(seg)
        lines.append("")
        start = end
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    text_file = Path(args.text_file).resolve()
    wav_file = Path(args.wav_file).resolve()
    output_srt = Path(args.output_srt).resolve()

    if not text_file.exists():
        print(f"ERROR: text file not found: {text_file}")
        return 1
    if not wav_file.exists():
        print(f"ERROR: wav file not found: {wav_file}")
        return 1

    text = read_text(text_file)
    segments = split_by_punctuation(text)

    if not segments:
        print("ERROR: no subtitle segments after split")
        return 1

    total_sec = wav_duration_seconds(wav_file)
    durations = distribute_durations(total_sec, segments, args.min_segment_sec)
    write_srt(output_srt, segments, durations)
    print(f"OUTPUT_SRT:{output_srt}")
    print(f"SEGMENTS:{len(segments)}")
    print(f"DURATION_SEC:{total_sec:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
