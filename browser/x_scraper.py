import asyncio
import json
import hashlib
import re
import sys
import argparse
from browser_agent import BrowserAgent

class XScraper:
    def __init__(self, target_count=20, output_file="x_posts.json", output_format="json"):
        self.agent = BrowserAgent()
        self.target_count = target_count
        self.output_file = output_file
        self.output_format = output_format.lower()
        self.posts = []
        self.seen_hashes = set()
        self.tab_id = None
        self.SCROLL_TARGET = "main" 

    def _get_content_hash(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    async def _ensure_tab(self):
        tabs = await self.agent.list_tabs()
        for t in tabs:
            if "x.com/home" in t.lower():
                match = re.search(r"\[(\d+)\]", t)
                if match: 
                    self.tab_id = match.group(1)
                    return
        await self.agent.open_tab("https://x.com/home")
        self.tab_id = "0"

    async def _extract_with_js(self):
        script = """
        () => {
            const articles = document.querySelectorAll('article');
            return Array.from(articles).map(a => {
                return a.innerText.replace(/\\s+/g, ' ').trim();
            }).filter(text => text.length > 50);
        }
        """
        try:
            raw_posts = await self.agent.evaluate(self.tab_id, script)
            new_found = 0
            for content in raw_posts:
                h = self._get_content_hash(content)
                if h not in self.seen_hashes:
                    self.seen_hashes.add(h)
                    self.posts.append({
                        "content": content,
                        "hash": h
                    })
                    new_found += 1
            return new_found
        except:
            return 0

    def _save_as_json(self, data):
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_as_md(self, data):
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(f"# X.com Posts Snapshot\n\n")
            f.write(f"Total posts: {len(data)}\n\n")
            for i, post in enumerate(data):
                f.write(f"## Post {i+1}\n\n")
                f.write(f"{post['content']}\n\n")
                f.write(f"---\n\n")

    async def run(self):
        try:
            await self._ensure_tab()
            print(f"开始抓取 X 内容 (目标: {self.target_count} 条，格式: {self.output_format})...")

            consecutive_empty = 0
            while len(self.posts) < self.target_count:
                new_count = await self._extract_with_js()
                print(f"进度: {len(self.posts)}/{self.target_count} (+{new_count} 新增)")

                if len(self.posts) >= self.target_count:
                    break

                if new_count == 0:
                    consecutive_empty += 1
                    if consecutive_empty > 5:
                        print("连续多次未发现新内容，停止抓取。")
                        break
                else:
                    consecutive_empty = 0

                print(f"正在执行滚动加载...")
                try:
                    await self.agent.scroll(self.tab_id, self.SCROLL_TARGET, 2500)
                except:
                    await self.agent.evaluate(self.tab_id, "window.scrollBy(0, 2500)")
                
                await asyncio.sleep(2.5)

            final_data = self.posts[:self.target_count]
            
            if self.output_format == "md":
                self._save_as_md(final_data)
            else:
                self._save_as_json(final_data)
            
            print(f"\n抓取完成！保存至 {self.output_file}")

        except Exception as e:
            print(f"异常: {e}")
        finally:
            await self.agent.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="X.com 内容抓取工具 (支持 JSON/MD)")
    parser.add_argument("-n", type=int, default=10, help="要抓取的数量")
    parser.add_argument("-o", "--out-file", dest="output", help="输出文件名 (如果不指定，将根据格式自动生成)")
    parser.add_argument("-f", "--format", choices=["json", "md"], default="json", help="输出格式: json 或 md (默认 json)")
    
    args = parser.parse_args()
    
    # 如果没指定输出文件，自动补全后缀
    if not args.output:
        args.output = f"x_posts.{args.format}"
    
    scraper = XScraper(target_count=args.n, output_file=args.output, output_format=args.format)
    asyncio.run(scraper.run())
