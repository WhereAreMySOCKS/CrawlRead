# CrawlRead - 免费的英语阅读工具

一个帮助npy养成英语阅读习惯的后端项目。

CrawlRead基于FastAPI框架，配合[React前端](https://github.com/WhereAreMySOCKS/html-article-viewer)完美实现了定时抓取英文新闻，并提供**翻译与AI分析、出题功能**。

## 📰 文章抓取

目前支持自动抓取 **基督教科学箴言报 （Christian Science Monitor，CSM）** 多个板块内容（见config.yaml）：
- Business（商业）
- World（国际）
- USA（美国）
- Arts（艺术）

*CSM是一份内容严肃、视野国际化的新闻媒体。它虽然由基督教科学会创办，但其报道并非宗教宣传，而是以客观、深入、分析性强著称，被誉为“新闻界的良心”。《基督教科学箴言报》是**考研英语阅读真题的重要来源之一**。                    
                                                    来源：deepseek*


## ✨ 核心功能

### 智能内容提取
- **定时抓取** - 通过定时任务自动获取板块的最新完整文章
- **纯净阅读体验** - 自动去除广告、导航、**付费墙**等干扰元素，只保留文章正文及其他必要信息
### AI辅助阅读
- **支持接入Qwen大模型** - 扮演考研英语名师，分析文章，生成题目
- **支持接入百度翻译API** - 哪里不会点哪里，快速理解文章内容


## 🚀 快速开始

### 安装运行
```bash
# 1. 克隆项目
git clone https://github.com/WhereAreMySOCKS/CrawlRead.git
cd CrawlRead

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python main.py
```

服务启动后访问：http://localhost:8000

### 立即体验
打开浏览器访问 http://localhost:8000/docs 查看所有可用功能

