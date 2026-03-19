import asyncio
import re
import json
import urllib.request
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, CDPSession

BROWSER_ENDPOINT = "http://127.0.0.1:9222"

class BrowserAgent:
    def __init__(self):
        self.pw = None
        self.browser: Browser = None
        self.context: BrowserContext = None

    async def _get_ws_url(self):
        try:
            with urllib.request.urlopen(f"{BROWSER_ENDPOINT}/json/version") as response:
                data = json.loads(response.read().decode())
                return data.get('webSocketDebuggerUrl')
        except Exception as e:
            print(f"Error fetching WS URL: {e}")
            return None

    async def _get_browser(self):
        if not self.browser or not self.browser.is_connected():
            if not self.pw:
                self.pw = await async_playwright().start()
            
            ws_url = await self._get_ws_url()
            if ws_url:
                # Playwright connect_over_cdp supports ws:// urls
                self.browser = await self.pw.chromium.connect_over_cdp(ws_url)
            else:
                # Fallback to endpoint if ws_url lookup fails
                self.browser = await self.pw.chromium.connect_over_cdp(BROWSER_ENDPOINT)
            
            self.context = self.browser.contexts[0]
        return self.browser

    async def _get_page(self, query: str) -> Page:
        await self._get_browser()
        pages = self.context.pages
        
        # Numeric index
        if re.match(r"^\d+$", query):
            index = int(query)
            if 0 <= index < len(pages):
                return pages[index]
            raise ValueError(f"Tab index {index} out of range (0-{len(pages)-1})")
        
        # URL match
        matches = [p for p in pages if query.lower() in p.url.lower()]
        if not matches:
            raise ValueError(f"Tab not found for query: {query}")
        
        # If multiple tabs match (common after reloads or duplicates), just pick the first one
        return matches[0]

    def _format_ax_tree(self, nodes: list, target_node_id: str = None) -> str:
        node_map = {n['nodeId']: n for n in nodes}
        root = next((n for n in nodes if n.get('role', {}).get('value') == "RootWebArea"), None)
        if not root:
            return "No RootWebArea found"

        output = []

        def print_node(node_id: str, depth: int):
            node = node_map.get(node_id)
            if not node:
                return

            role = node.get('role', {}).get('value', 'unknown')
            name = node.get('name', {}).get('value', '')
            child_ids = node.get('childIds', [])

            if role in ["InlineTextBox", "LineBreak"]:
                return

            is_generic = role in ["generic", "none"]
            is_root = role == "RootWebArea"
            is_target = node['nodeId'] == target_node_id

            # Skip empty generic nodes unless target/root
            if not is_root and not is_target and is_generic and not name:
                for cid in child_ids:
                    print_node(cid, depth)
                return

            indent = "  " * depth
            has_children = len(child_ids) > 0
            child_prefix = "[+]" if has_children else "   "
            output.append(f"{indent}{child_prefix} ID: {node['nodeId']} | [{role}] {name}")

            # Expand root or target
            if depth == 0 or is_target:
                for cid in child_ids:
                    print_node(cid, depth + 1)

        print_node(target_node_id or root['nodeId'], 0)
        return "\n".join(output)

    def _resolve_node_id(self, nodes: list, query: str) -> str:
        if re.match(r"^-?\d+$", query):
            return query
        
        target_role = None
        target_name = query
        if ":" in query:
            target_role, target_name = query.split(":", 1)

        def is_match(n):
            role = n.get('role', {}).get('value', '').lower()
            name = n.get('name', {}).get('value', '').lower()
            q = target_name.lower()
            
            if target_role:
                # 角色必须精确匹配，名称模糊匹配
                return role == target_role.lower() and q in name
            else:
                # 全局模糊匹配
                return q in role or q in name

        matches = [n for n in nodes if is_match(n)]
        
        if not matches:
            raise ValueError(f"Node not found for semantic query: '{query}'")
        
        # 优先选择名称更接近的
        if len(matches) > 1:
            # 如果有完全匹配的名称，选它
            exact_matches = [n for n in matches if n.get('name', {}).get('value', '').lower() == target_name.lower()]
            if exact_matches:
                return exact_matches[0]['nodeId']
            
            list_str = "\n".join([f"ID: {n['nodeId']} | [{n.get('role', {}).get('value')}] {n.get('name', {}).get('value', '')}" for n in matches[:5]])
            raise ValueError(f"Ambiguous node query: '{query}' matches multiple elements (showing first 5):\n{list_str}")
        
        return matches[0]['nodeId']

    async def _resolve_target_node_center(self, tab_id: str, node_query: str):
        page = await self._get_page(tab_id)
        client = await page.context.new_cdp_session(page)
        await client.send("Accessibility.enable")
        ax_tree = await client.send("Accessibility.getFullAXTree")
        nodes = ax_tree['nodes']
        
        target_id = self._resolve_node_id(nodes, node_query)
        target_node = next((n for n in nodes if n['nodeId'] == target_id), None)
        
        if not target_node or 'backendDOMNodeId' not in target_node:
            raise ValueError("Node not found or has no backendDOMNodeId")

        box_model = await client.send("DOM.getBoxModel", {"backendNodeId": target_node['backendDOMNodeId']})
        quad = box_model['model']['content']
        # quad is [x1, y1, x2, y2, x3, y3, x4, y4]
        x = (quad[0] + quad[2] + quad[4] + quad[6]) / 4
        y = (quad[1] + quad[3] + quad[5] + quad[7]) / 4
        return x, y, client

    # --- Public API ---

    async def list_tabs(self) -> list:
        await self._get_browser()
        return [f"[{i}] {p.url}" for i, p in enumerate(self.context.pages)]

    async def open_tab(self, url: str) -> str:
        await self._get_browser()
        page = await self.context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(1)
        return f"Opened {url}"

    async def get_ax_tree(self, tab_id: str, node_id: str = None) -> str:
        page = await self._get_page(tab_id)
        client = await page.context.new_cdp_session(page)
        await client.send("Accessibility.enable")
        ax_tree = await client.send("Accessibility.getFullAXTree")
        nodes = ax_tree['nodes']
        
        target_id = self._resolve_node_id(nodes, node_id) if node_id else None
        return self._format_ax_tree(nodes, target_id)

    async def screenshot(self, tab_id: str) -> bytes:
        page = await self._get_page(tab_id)
        return await page.screenshot(type="png")

    async def click(self, tab_id: str, node_id: str) -> str:
        x, y, client = await self._resolve_target_node_center(tab_id, node_id)
        await client.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        await client.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
        await client.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
        await asyncio.sleep(1)
        return f"Success: Physical click on {node_id}"

    async def scroll(self, tab_id: str, node_id: str, delta_y: int) -> str:
        x, y, client = await self._resolve_target_node_center(tab_id, node_id)
        await client.send("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": x, "y": y, "deltaX": 0, "deltaY": delta_y})
        await asyncio.sleep(1)
        return f"Success: Physical scroll on {node_id}"

    async def type(self, tab_id: str, node_id: str, text: str) -> str:
        x, y, client = await self._resolve_target_node_center(tab_id, node_id)
        
        # Focus
        await client.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
        await client.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})

        tokens = re.findall(r"(\{.*?\})|([^{]+)", text)
        for tag, plain in tokens:
            token = tag if tag else plain
            if token == "{Control+A}{Backspace}":
                await client.send("Input.dispatchKeyEvent", {"type": "keyDown", "modifiers": 2, "windowsVirtualKeyCode": 65, "key": "a", "code": "KeyA"})
                await client.send("Input.dispatchKeyEvent", {"type": "keyUp", "modifiers": 2, "windowsVirtualKeyCode": 65, "key": "a", "code": "KeyA"})
                await client.send("Input.dispatchKeyEvent", {"type": "keyDown", "windowsVirtualKeyCode": 8, "key": "Backspace", "code": "Backspace"})
                await client.send("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": 8, "key": "Backspace", "code": "Backspace"})
            elif token == "{Backspace}":
                await client.send("Input.dispatchKeyEvent", {"type": "keyDown", "windowsVirtualKeyCode": 8, "key": "Backspace", "code": "Backspace"})
                await client.send("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": 8, "key": "Backspace", "code": "Backspace"})
            elif token == "{Enter}":
                await client.send("Input.dispatchKeyEvent", {"type": "keyDown", "windowsVirtualKeyCode": 13, "key": "Enter", "code": "Enter"})
                await client.send("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": 13, "key": "Enter", "code": "Enter"})
            elif token == "{Tab}":
                await client.send("Input.dispatchKeyEvent", {"type": "keyDown", "windowsVirtualKeyCode": 9, "key": "Tab", "code": "Tab"})
                await client.send("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": 9, "key": "Tab", "code": "Tab"})
            elif token == "{ArrowDown}":
                await client.send("Input.dispatchKeyEvent", {"type": "keyDown", "windowsVirtualKeyCode": 40, "key": "ArrowDown", "code": "ArrowDown"})
                await client.send("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": 40, "key": "ArrowDown", "code": "ArrowDown"})
            elif token == "{ArrowUp}":
                await client.send("Input.dispatchKeyEvent", {"type": "keyDown", "windowsVirtualKeyCode": 38, "key": "ArrowUp", "code": "ArrowUp"})
                await client.send("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": 38, "key": "ArrowUp", "code": "ArrowUp"})
            else:
                for char in token:
                    if char == "\b":
                        await client.send("Input.dispatchKeyEvent", {"type": "keyDown", "windowsVirtualKeyCode": 8, "key": "Backspace", "code": "Backspace"})
                        await client.send("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": 8, "key": "Backspace", "code": "Backspace"})
                    else:
                        await client.send("Input.dispatchKeyEvent", {"type": "keyDown", "text": char})
                        await client.send("Input.dispatchKeyEvent", {"type": "keyUp"})

        await asyncio.sleep(0.5)
        return f"Success: Mixed physical type on {node_id}"

    async def evaluate(self, tab_id: str, script: str):
        page = await self._get_page(tab_id)
        result = await page.evaluate(script)
        await asyncio.sleep(1)
        return result

    async def disconnect(self):
        if self.browser:
            await self.browser.close()
        if self.pw:
            await self.pw.stop()
        self.browser = None
        self.pw = None
