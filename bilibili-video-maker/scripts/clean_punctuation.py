import json
import argparse
import re
from pathlib import Path

def strip_punctuation(text):
    # 定义需要移除的行末标点
    punctuations = "，。,.！？!?；;：:"
    
    # 如果有多行，每一行都要处理
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # 去除末尾空格后，再去除标点
        cleaned = line.strip().rstrip(punctuations)
        cleaned_lines.append(cleaned)
    
    return "\n".join(cleaned_lines)

def main():
    parser = argparse.ArgumentParser(description="Clean trailing punctuation from segments JSON.")
    parser.add_argument("--json-file", required=True, help="Path to segments_final.json")
    args = parser.parse_args()
    
    path = Path(args.json_file).resolve()
    if not path.exists():
        print(f"Error: File not found {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for item in data:
        if "text" in item:
            item["text"] = strip_punctuation(item["text"])
            
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"SUCCESS: Cleaned trailing punctuation in {path}")

if __name__ == "__main__":
    main()
