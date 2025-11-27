# Universal Web Crawler MCP (SSE Version) 🕷️

这是一个基于 MCP (Model Context Protocol) 的通用图片爬虫工具，采用 **SSE (Server-Sent Events)** 架构。它可以作为独立服务运行，供 Claude Desktop 或其他 MCP 客户端远程连接。

## ✨ 特性
- **全自动**：输入关键词 -> 自动搜索 -> 自动评分 -> 自动下载。
- **SSE架构**：基于 Starlette 构建，支持 HTTP 远程调用，无需本地作为子进程运行。
- **通用性**：适用于医学、摄影、设计等各种领域的图片采集。

## 📦 安装

1. 克隆项目：
   ```bash
   git clone [https://github.com/你的用户名/Universal_Web_Crawler_MCP.git](https://github.com/你的用户名/Universal_Web_Crawler_MCP.git)
   cd Universal_Web_Crawler_MCP

2.安装依赖：
pip install -r requirements.txt


🚀 运行服务
启动 SSE 服务器：

Bash

python src/server.py
终端将显示 Uvicorn running on http://0.0.0.0:8000。

⚙️ 连接 Claude Desktop
你需要修改 Claude 的配置文件，这次使用的配置类型是 sse 而不是 stdio。

修改配置文件 (例如 macOS: ~/Library/Application Support/Claude/claude_desktop_config.json)：

JSON

{
  "mcpServers": {
    "web-crawler-sse": {
      "url": "http://localhost:8000/sse"
    }
  }
}
重启 Claude Desktop，即可在对话中使用工具。