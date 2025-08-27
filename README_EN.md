# CrawlRead - Free English Reading Tool

A backend project designed to help npy develop the habit of reading English.

CrawlRead is based on the FastAPI framework and works seamlessly with the [React frontend](https://github.com/WhereAreMySOCKS/html-article-viewer) to periodically fetch English news articles and provide **translation, AI analysis, and question generation features**.

## 📰 Article Crawling

Currently supports automatic fetching of multiple sections from the **Christian Science Monitor (CSM)** (see config.yaml):
- Business
- World
- USA
- Arts

*CSM is a serious and internationally-focused news outlet. Although founded by the Christian Science Church, its reporting is not religious propaganda but is known for being objective, in-depth, and analytical, earning the title "the conscience of journalism." The Christian Science Monitor is also an **important source for English reading comprehension questions in postgraduate entrance exams**.*

## ✨ Core Features

### Intelligent Content Extraction
- **Scheduled Crawling** - Automatically fetches the latest complete articles from sections via scheduled tasks
- **Clean Reading Experience** - Automatically removes ads, navigation, **paywalls**, and other distractions, leaving only the article content and necessary information

### AI-Assisted Reading
- **Supports integration with Qwen large model** - Acts as a postgraduate English teacher, analyzing articles and generating questions
- **Supports integration with Baidu Translation API** - Quickly understand article content by clicking where needed

## 🚀 Quick Start

### Installation and Running
```bash
# 1. Clone the project
git clone https://github.com/WhereAreMySOCKS/CrawlRead.git
cd CrawlRead

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the service
python main.py
```

After starting the service, visit: http://localhost:8000

### Try It Now
Open your browser and visit http://localhost:8000/docs to explore all available features