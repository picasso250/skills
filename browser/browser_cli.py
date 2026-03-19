import asyncio
import argparse
import sys
import json
from browser_agent import BrowserAgent

async def main():
    parser = argparse.ArgumentParser(
        description="BrowserAgent CLI - 直接操控本地已运行的浏览器 (9222 端口)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
操作示例:
  python browser_cli.py list-tabs
  python browser_cli.py open-tab https://www.google.com
  python browser_cli.py tree 0
  python browser_cli.py click 0 55
  python browser_cli.py type 0 55 "hello world{Enter}"
  python browser_cli.py screenshot 0 output.png
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # List Tabs
    subparsers.add_parser("list-tabs", help="显示所有打开的标签页")

    # Open Tab
    open_parser = subparsers.add_parser("open-tab", help="打开新标签页")
    open_parser.add_argument("url", help="URL 地址")

    # AXTree
    tree_parser = subparsers.add_parser("tree", help="获取 AXTree 结构")
    tree_parser.add_argument("tab_id", help="标签页 ID 或 URL 片段")
    tree_parser.add_argument("--node-id", "-n", help="指定起始 Node ID (可选)")

    # Screenshot
    shot_parser = subparsers.add_parser("screenshot", help="截取屏幕快照")
    shot_parser.add_argument("tab_id", help="标签页 ID 或 URL 片段")
    shot_parser.add_argument("output", help="保存的文件路径 (PNG 格式)")

    # Click
    click_parser = subparsers.add_parser("click", help="物理点击指定节点")
    click_parser.add_argument("tab_id", help="标签页 ID 或 URL 片段")
    click_parser.add_argument("node_id", help="Node ID 或 语义查询")

    # Scroll
    scroll_parser = subparsers.add_parser("scroll", help="滚动指定节点")
    scroll_parser.add_argument("tab_id", help="标签页 ID 或 URL 片段")
    scroll_parser.add_argument("node_id", help="Node ID 或 语义查询")
    scroll_parser.add_argument("delta", type=int, help="滚动偏移量 (正下负上)")

    # Type
    type_parser = subparsers.add_parser("type", help="物理输入文字")
    type_parser.add_argument("tab_id", help="标签页 ID 或 URL 片段")
    type_parser.add_argument("node_id", help="Node ID 或 语义查询")
    type_parser.add_argument("text", help="输入的文本 (支持 {Enter}, {Backspace} 等标签)")

    # Eval
    eval_parser = subparsers.add_parser("eval", help="在标签页内执行 JS 脚本")
    eval_parser.add_argument("tab_id", help="标签页 ID 或 URL 片段")
    eval_parser.add_argument("script", help="JS 代码字符串")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    agent = BrowserAgent()
    try:
        if args.command == "list-tabs":
            tabs = await agent.list_tabs()
            print("\n".join(tabs) or "No tabs open")
        
        elif args.command == "open-tab":
            print(await agent.open_tab(args.url))
            
        elif args.command == "tree":
            print(await agent.get_ax_tree(args.tab_id, args.node_id))
            
        elif args.command == "screenshot":
            data = await agent.screenshot(args.tab_id)
            with open(args.output, "wb") as f:
                f.write(data)
            print(f"Screenshot saved to {args.output}")
            
        elif args.command == "click":
            print(await agent.click(args.tab_id, args.node_id))
            
        elif args.command == "scroll":
            print(await agent.scroll(args.tab_id, args.node_id, args.delta))
            
        elif args.command == "type":
            print(await agent.type(args.tab_id, args.node_id, args.text))
            
        elif args.command == "eval":
            result = await agent.evaluate(args.tab_id, args.script)
            print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await agent.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
