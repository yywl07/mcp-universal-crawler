# src/server.py
import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# 引入之前的逻辑模块
from .crawler import GenericImageCrawler
from .ranker import UniversalRanker

# 1. 初始化 MCP Server 实例
app_server = Server("universal-crawler-sse")

# 实例化功能模块
crawler = GenericImageCrawler(output_dir="./downloads")
ranker = UniversalRanker()

# 2. 注册工具 (Tool Registration)
@app_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="auto_crawl_images",
            description="自动搜索并下载互联网上的图片。支持根据关键词寻找专业网站并抓取。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词 (例如: '风景', '病理切片', '二次元头像')"
                    },
                    "max_sites": {
                        "type": "integer",
                        "description": "要爬取的网站数量 (默认3)",
                        "default": 3
                    },
                    "count_per_site": {
                        "type": "integer",
                        "description": "每个网站下载的图片数量 (默认5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        )
    ]

# 3. 工具逻辑实现
@app_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    if name == "auto_crawl_images":
        query = arguments.get("query")
        max_sites = arguments.get("max_sites", 3)
        count = arguments.get("count_per_site", 5)

        # 调用 Ranker 进行搜索
        ranked_sites = ranker.search_and_rank(query, max_results=10)
        
        if not ranked_sites:
            return [TextContent(type="text", text="未找到相关网站。")]

        report = [f"🔍 搜索关键词: {query}\n"]
        total_downloaded = 0

        # 遍历网站爬取
        for i, site in enumerate(ranked_sites[:max_sites]):
            url = site['href']
            report.append(f"--- 来源 {i+1}: {site['title']} ---")
            
            try:
                # 调用 Crawler
                # 注意：crawler.crawl 是同步代码，但在 async 函数里调用没问题，
                # 如果并发量大建议用 asyncio.to_thread 包装，这里简单处理直接调用
                results = crawler.crawl(url, max_images=count, keyword_filter=query.split()[0])
                num = len(results)
                total_downloaded += num
                
                if num > 0:
                    names = [os.path.basename(r['path']) for r in results[:2]]
                    report.append(f"✅ 下载 {num} 张 (样例: {', '.join(names)}...)")
                else:
                    report.append("⚠️ 未抓取到有效图片")
            except Exception as e:
                report.append(f"❌ 错误: {str(e)}")
            report.append("")

        report.append(f"🎉 任务结束，共保存 {total_downloaded} 张图片至 {crawler.images_dir}")
        return [TextContent(type="text", text="\n".join(report))]

    raise ValueError(f"Unknown tool: {name}")

# 4. 配置 SSE 和 HTTP 路由 (Starlette)
sse = SseServerTransport("/messages")

async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await app_server.run(streams[0], streams[1], app_server.create_initialization_options())

async def handle_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

# 5. 启动入口
starlette_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    # 使用 uvicorn 启动
    uvicorn.run(starlette_app, host="0.0.0.0", port=8000)