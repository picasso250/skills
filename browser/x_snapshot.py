import asyncio
import json
import re
from browser_agent import BrowserAgent

async def main():
    agent = BrowserAgent()
    try:
        tabs = await agent.list_tabs()
        tab_id = None
        for t in tabs:
            if "x.com/home" in t.lower():
                match = re.search(r"\[(\d+)\]", t)
                if match: tab_id = match.group(1); break
        
        if tab_id is None:
            print("未找到 X 主页")
            return

        print(f"正在标签页 [{tab_id}] 注入 JS 进行精准提取...")

        # 注入一个更稳健的 JS，专门针对 X.com 的文章结构
        script = """
        () => {
            // 获取所有文章元素
            const articles = document.querySelectorAll('article');
            return Array.from(articles).map(a => {
                // 移除不必要的空白字符
                return a.innerText.replace(/\\s+/g, ' ').trim();
            }).filter(text => text.length > 30);
        }
        """
        
        results = await agent.evaluate(tab_id, script)
        
        with open("x_visible_snapshot.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n成功！JS 提取到 {len(results)} 条可见帖子。")
        for i, post in enumerate(results):
            print(f"{i+1}. {post[:100]}...")

    except Exception as e:
        print(f"错误: {e}")
    finally:
        await agent.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
