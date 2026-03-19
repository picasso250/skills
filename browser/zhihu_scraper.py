import asyncio
import json
import hashlib
import re
import sys
import argparse
from browser_agent import BrowserAgent

class ZhihuScraper:
    def __init__(self, target_count=20, output_file="zhihu_posts.json", output_format="json"):
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
            if "zhihu.com" in t.lower():
                match = re.search(r"\[(\d+)\]", t)
                if match:
                    self.tab_id = match.group(1)
                    return
        await self.agent.open_tab("https://www.zhihu.com/")
        self.tab_id = "0"

    async def _extract_with_js(self):
        script = """
        () => {
            const cards = document.querySelectorAll('.Card.TopstoryItem, .Card.Feed');
            return Array.from(cards).map(c => {
                const titleNode = c.querySelector('.ContentItem-title, h2');
                const title = titleNode ? titleNode.innerText.trim() : "";
                
                const authorNode = c.querySelector('.AuthorInfo-name, .UserLink-link');
                const author = authorNode ? authorNode.innerText.trim() : "匿名用户";
                
                const excerptNode = c.querySelector('.RichText, .ContentItem-description');
                const excerpt = excerptNode ? excerptNode.innerText.replace(/\\s+/g, ' ').trim() : "";
                
                const upvoteNode = c.querySelector('.VoteButton--up');
                const upvotes = upvoteNode ? upvoteNode.innerText.replace(/\\s+/g, ' ').trim() : "0";
                
                const fullText = `【${title}】作者：${author} | ${upvotes} | ${excerpt}`;
                return { title, author, excerpt, upvotes, fullText };
            }).filter(item => item.title.length > 0);
        }
        """
        try:
            raw_items = await self.agent.evaluate(self.tab_id, script)
            new_found = 0
            for item in raw_items:
                h = self._get_content_hash(item['fullText'])
                if h not in self.seen_hashes:
                    self.seen_hashes.add(h)
                    self.posts.append(item)
                    new_found += 1
            return new_found
        except:
            return 0

    def _save(self):
        data = self.posts[:self.target_count]
        if self.output_format == "md":
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(f"# 知乎 Feed 快照\n\n总计：{len(data)}\n\n")
                for i, item in enumerate(data):
                    f.write(f"### {i+1}. {item['title']}\n")
                    f.write(f"- **作者**：{item['author']}\n")
                    f.write(f"- **赞同**：{item['upvotes']}\n")
                    f.write(f"- **摘要**：{item['excerpt']}\n\n---\n\n")
        else:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    async def run(self):
        try:
            await self._ensure_tab()
            print(f"开始抓取知乎内容 (目标: {self.target_count} 条)...")

            consecutive_empty = 0
            while len(self.posts) < self.target_count:
                new_count = await self._extract_with_js()
                print(f"进度: {len(self.posts)}/{self.target_count} (+{new_count} 新增)")

                if len(self.posts) >= self.target_count:
                    break

                if new_count == 0:
                    consecutive_empty += 1
                    if consecutive_empty > 5: 
                        print("连续多次未发现新内容，停止。")
                        break
                else:
                    consecutive_empty = 0

                print("正在执行滚动加载...")
                try:
                    await self.agent.scroll(self.tab_id, self.SCROLL_TARGET, 2000)
                except:
                    await self.agent.evaluate(self.tab_id, "window.scrollBy(0, 2000)")
                
                await asyncio.sleep(2.5)

            self._save()
            print(f"\n完成！结果已保存至 {self.output_file}")

        except Exception as e:
            print(f"异常: {e}")
        finally:
            await self.agent.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="知乎 Feed 抓取工具")
    parser.add_argument("-n", type=int, default=10, help="要抓取的数量")
    parser.add_argument("-o", "--out-file", dest="output")
    parser.add_argument("-f", "--format", choices=["json", "md"], default="json")
    args = parser.parse_args()
    
    out = args.output or f"zhihu_posts.{args.format}"
    scraper = ZhihuScraper(target_count=args.n, output_file=out, output_format=args.format)
    asyncio.run(scraper.run())
