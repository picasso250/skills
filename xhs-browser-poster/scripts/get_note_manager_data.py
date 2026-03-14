import asyncio
import sys
import os
import json

# Adjust the path to import BrowserAgent
# In production, we might want a more robust way to find this path
sys.path.append(r'C:\Users\MECHREV\.agents\skills\browser')
from browser_agent import BrowserAgent

async def fetch_notes_data():
    agent = BrowserAgent()
    try:
        url = "https://creator.xiaohongshu.com/new/note-manager"
        
        # Navigate or find tab
        try:
            page = await agent._get_page(url)
            await page.reload()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
        except Exception:
            await agent.open_tab(url)
            await asyncio.sleep(5) # Wait for load

        # Extraction script
        script = """
        () => {
            const noteElements = document.querySelectorAll('.note');
            return Array.from(noteElements).map(el => {
                // 1. 尝试获取标题：通常在 .info 类下的第一个非状态文本
                // 观察发现，审核中时，.info 内可能包含两个子节点：一个是 tag，一个是真正的 title
                const infoEl = el.querySelector('.info');
                let title = "";
                if (infoEl) {
                    // 深度优先查找第一个长文本，或者排除掉已知的短状态标签
                    const textNodes = Array.from(infoEl.childNodes)
                        .map(n => n.innerText || n.textContent)
                        .filter(t => t && t.trim().length > 0);
                    
                    // 如果第一个是状态（如“审核中”），取第二个作为标题
                    if (textNodes[0] && (textNodes[0].includes("审核中") || textNodes[0].includes("未通过"))) {
                        title = textNodes[1] || textNodes[0];
                    } else {
                        title = textNodes[0] || "";
                    }
                }
                title = title.split('\\n')[0].trim();
                
                // 2. 提取状态
                const statusTag = el.querySelector('.time_status .d-text, .time_status [class*="tag"], .info [class*="tag"]')?.innerText || "已发布";
                
                const time = el.querySelector('.time')?.innerText || "";
                const publishDate = time.replace('发布于 ', '').trim();
                
                const statsElements = Array.from(el.querySelectorAll('.icon'));
                const stats = statsElements.map(icon => icon.innerText.trim());
                
                return {
                    title: title,
                    status: statusTag.trim(),
                    publish_date: publishDate,
                    views: stats[0] || "0",
                    comments: stats[1] || "0",
                    likes: stats[2] || "0",
                    collections: stats[3] || "0",
                    shares: stats[4] || "0"
                };
            });
        }
        """
        notes = await agent.evaluate(url, script)
        return notes

    except Exception as e:
        print(f"Error fetching notes: {e}")
        return []
    finally:
        await agent.disconnect()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch XHS Note Manager data.")
    parser.add_argument("--format", choices=["tsv", "json"], default="tsv", help="Output format (default: tsv)")
    args = parser.parse_args()

    notes = asyncio.run(fetch_notes_data())
    
    if not notes:
        sys.exit(0)

    if args.format == "json":
        print(json.dumps(notes, indent=2, ensure_ascii=False))
    else:
        # TSV format
        headers = ["title", "publish_date", "views", "comments", "likes", "collections", "shares"]
        print("\t".join(headers))
        for n in notes:
            row = [str(n.get(h, "")) for h in headers]
            print("\t".join(row))
