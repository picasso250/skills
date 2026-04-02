import argparse
import subprocess
import os
import sys

def main():
    parser = argparse.ArgumentParser(description='Ollama OCR Tool using qwen2.5vl:7b')
    parser.add_argument('--file', type=str, required=True, help='Path to the image file')
    parser.add_argument('--prompt', type=str, default='请提取这张图片中的所有文字：', help='Custom prompt for OCR')
    parser.add_argument('--model', type=str, default='qwen2.5vl:7b', help='Ollama model to use')

    args = parser.parse_args()

    image_path = os.path.abspath(args.file)

    if not os.path.exists(image_path):
        print(f"Error: File not found at {image_path}")
        sys.exit(1)

    # 构造 Ollama 命令
    # 注意：某些版本的 Ollama CLI 在处理带空格的路径时需要特别处理
    command = f'ollama run {args.model} "{args.prompt} {image_path}"'
    
    print(f"--- Processing: {os.path.basename(image_path)} ---")
    
    try:
        # 使用 shell=True 以支持 Windows 的命令解析
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        
        # 实时打印输出，以便用户看到进度
        for line in process.stdout:
            print(line, end='')
            
        process.wait()
        
        if process.returncode != 0:
            print(f"\nError: Ollama exited with code {process.returncode}")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
