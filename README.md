# 🌏 多語言學習平台 (Multilingual Learning Platform)

> **Language / 語言:** [繁體中文](#繁體中文) | [English](#english)

---

<a name="繁體中文"></a>
## 繁體中文版

一個整合 AI 技術的多語言學習平台，支援中文和韓文詞彙學習，提供互動式知識圖譜、單字收藏、學習遊戲等功能。

## ✨ 主要功能

### 📚 中文學習
- **智能詞彙分析**：使用 AI (Gemini) 分析網頁或純文字內容，自動提取中文詞彙
- **TOCFL 級數標記**：自動標註 TOCFL (華語文能力測驗) 級數（第1-7級）
- **知識圖譜視覺化**：互動式 D3.js 圖譜，顏色標示不同級數
- **英文翻譯與定義**：每個詞彙包含英文翻譯、英文定義和例句
- **單字收藏系統**：雙擊節點即可收藏單字，支援分級管理

### 🇰🇷 韓文學習
- **韓文新聞分析**：分析韓文網頁內容，提取關鍵詞彙
- **中文翻譯對照**：提供韓文單字的中文翻譯和定義
- **知識圖譜視覺化**：互動式節點圖譜，方便探索詞彙關係
- **例句學習**：韓文例句搭配中文翻譯

### 🎮 學習遊戲
- **單字配對遊戲**：考驗記憶力的翻牌配對
- **打字練習遊戲**：訓練拼寫能力
- **聽力練習**：TTS 語音生成，訓練聽力理解

### 👤 用戶系統
- **帳號註冊/登入**：使用 Supabase 管理用戶資料
- **個人化收藏**：每個用戶獨立的單字收藏庫
- **多語言介面**：支援繁體中文、簡體中文、英文、韓文

---

## 🚀 快速開始

### 前置需求

- Python 3.9+
- Node.js (可選，用於前端開發)
- Supabase 帳號
- Google Gemini API Key

### 本地安裝

1. **克隆專案**
```bash
git clone https://github.com/pupupeter/12312366.git
cd 12312366
```

2. **安裝依賴**
```bash
pip install -r requirements.txt
```

3. **設定環境變數**

創建 `.env` 檔案：
```env
# Supabase 配置
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Gemini API
GEMINI_API_KEY=your_gemini_api_key
```

4. **設定 Supabase 資料庫**

在 Supabase SQL Editor 執行以下 SQL 創建資料表：

```sql
-- 用戶表
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT UNIQUE,
    language TEXT DEFAULT 'zh-TW',
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- 中文單字收藏表
CREATE TABLE chinese_words (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    chinese TEXT NOT NULL,
    english TEXT,
    definition TEXT,
    example_chinese TEXT,
    example_english TEXT,
    level TEXT,
    level_category TEXT,
    level_number TEXT,
    saved_at TIMESTAMP DEFAULT NOW()
);

-- 韓文單字收藏表
CREATE TABLE korean_words (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    korean TEXT NOT NULL,
    chinese TEXT,
    definition TEXT,
    example_korean TEXT,
    example_chinese TEXT,
    saved_at TIMESTAMP DEFAULT NOW()
);
```

5. **啟動應用**
```bash
python railway_app.py
```

應用將在 `http://localhost:8080` 啟動

---

## 📖 使用方法

### 中文詞彙分析

1. 登入後點擊「中文詞彙學習」
2. 輸入網址或貼上純文字
3. 點擊「開始分析」
4. 等待 AI 分析完成後，自動開啟知識圖譜

**知識圖譜操作：**
- **滑過節點**：查看單字詳細資訊（英文翻譯、定義、例句）
- **雙擊節點**：收藏單字到個人清單
- **拖曳節點**：重新排列圖譜
- **滾輪縮放**：放大/縮小圖譜
- **點擊「❓ Help」**：查看完整使用說明

**TOCFL 級數顏色：**
- 🟢 綠色：第1-2級（基礎）
- 🟡 黃色：第3級（進階）
- 🟠 橙色：第4-5級（進階-精熟）
- 🔴 紅色：第6-7級（精熟）
- ⚫ 灰色：未分級

### 韓文詞彙分析

1. 登入後點擊「韓文詞彙學習」
2. 輸入韓文網頁網址
3. 點擊「開始分析」
4. 查看知識圖譜並收藏單字

**知識圖譜操作：**
- **滑過節點**：查看韓文單字的中文翻譯和例句
- **雙擊節點**：收藏單字
- **點擊「❓ 使用說明」**：查看中文操作指南

### 學習遊戲

1. 點擊「單字學習遊戲」
2. 選擇遊戲類型：
   - **配對遊戲**：翻牌配對單字與翻譯
   - **打字遊戲**：根據提示輸入正確單字
3. 遊戲內容來自你的收藏單字

### 管理收藏

- 點擊「📚 我的收藏」查看所有收藏單字
- 可按語言、級數篩選
- 支援刪除不需要的單字
- 匯出為 CSV 檔案供外部使用

---

## 🛠️ 部署方法

### Railway 部署 (推薦)

Railway 提供免費額度，適合快速部署。

1. **準備工作**
   - 註冊 [Railway](https://railway.app/) 帳號
   - Fork 此專案到你的 GitHub

2. **創建新專案**
   - 登入 Railway
   - 點擊「New Project」
   - 選擇「Deploy from GitHub repo」
   - 選擇你 Fork 的專案

3. **設定環境變數**

   在 Railway 專案的 Variables 頁面添加：
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   GEMINI_API_KEY=your_gemini_api_key
   PORT=8080
   ```

4. **部署設定**

   Railway 會自動偵測 Python 專案，並使用以下設定：
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python railway_app.py`

5. **完成部署**
   - Railway 會自動部署並提供一個公開 URL
   - 例如：`https://your-app.railway.app`

6. **自動部署**
   - 每次 push 到 GitHub main 分支
   - Railway 會自動重新部署

### Vercel 部署 (備選)

Vercel 也可以部署 Python Flask 應用。

1. **準備 vercel.json**

   確保專案根目錄有 `vercel.json`：
   ```json
   {
     "version": 2,
     "builds": [
       {
         "src": "railway_app.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "railway_app.py"
       }
     ]
   }
   ```

2. **部署到 Vercel**
   ```bash
   npm i -g vercel
   vercel
   ```

3. **設定環境變數**

   在 Vercel Dashboard 的 Settings → Environment Variables 添加：
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `GEMINI_API_KEY`

### 本地開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入你的配置

# 啟動開發服務器
python railway_app.py
```

訪問 `http://localhost:8080`

---

## 📁 專案結構

```
12312366/
├── railway_app.py              # 主應用程式 (Flask)
├── chinese_analysis.py         # 中文圖譜生成
├── korean_analysis.py          # 韓文圖譜生成
├── supabase_utils.py          # Supabase 資料庫操作
├── tocfl_loader.py            # TOCFL 詞彙表載入器
├── translations.py            # 多語言翻譯
├── templates/                 # HTML 模板
│   ├── dashboard.html         # 主控面板
│   ├── review22.html          # 收藏頁面
│   ├── games/                 # 遊戲頁面
│   └── ...
├── static/                    # 靜態資源
├── 14452詞語表202504.csv      # TOCFL 詞彙表
├── requirements.txt           # Python 依賴
├── .env                       # 環境變數 (不提交到 Git)
└── README.md                  # 本文件
```

---

## 🔧 技術棧

### 後端
- **Flask**：Web 框架
- **Supabase**：資料庫 (PostgreSQL)
- **Google Gemini**：AI 詞彙分析
- **smolagents**：AI Agent 框架

### 前端
- **D3.js**：知識圖譜視覺化
- **Bootstrap**：UI 框架
- **Jinja2**：模板引擎

### 部署
- **Railway**：主要部署平台
- **Vercel**：備選部署平台

---

## 🌐 環境變數說明

| 變數名稱 | 說明 | 必填 |
|---------|------|------|
| `SUPABASE_URL` | Supabase 專案 URL | ✅ |
| `SUPABASE_ANON_KEY` | Supabase 匿名金鑰 | ✅ |
| `GEMINI_API_KEY` | Google Gemini API 金鑰 | ✅ |
| `PORT` | 應用端口 (預設 8080) | ❌ |

---

## 📝 常見問題

### Q: 如何獲取 Gemini API Key?
A: 前往 [Google AI Studio](https://makersuite.google.com/app/apikey) 申請免費 API Key。

### Q: Supabase 如何設定?
A:
1. 註冊 [Supabase](https://supabase.com/)
2. 創建新專案
3. 在 Settings → API 找到 URL 和 anon key
4. 在 SQL Editor 執行資料表創建 SQL

### Q: 部署後無法登入?
A: 確認 Supabase 環境變數設定正確，並檢查資料表是否已創建。

### Q: 中文分析沒有反應?
A: 檢查 Gemini API Key 是否有效，以及是否有 API 配額。

### Q: 圖譜顯示空白?
A: 確認瀏覽器支援 D3.js，建議使用最新版 Chrome 或 Firefox。

---

## 📄 授權

MIT License

---

## 👨‍💻 開發者

由 Claude Code 協助開發

---

## 🔗 相關連結

- [Supabase 文檔](https://supabase.com/docs)
- [Railway 文檔](https://docs.railway.app/)
- [Google Gemini API](https://ai.google.dev/)
- [D3.js 文檔](https://d3js.org/)

---
---

<a name="english"></a>
## English Version

An AI-powered multilingual learning platform supporting Chinese and Korean vocabulary learning with interactive knowledge graphs, word collections, learning games, and more.

## ✨ Key Features

### 📚 Chinese Learning
- **Smart Vocabulary Analysis**: Uses AI (Gemini) to analyze web pages or plain text content, automatically extracting Chinese vocabulary
- **TOCFL Level Tagging**: Automatically labels TOCFL (Test of Chinese as a Foreign Language) levels (Levels 1-7)
- **Knowledge Graph Visualization**: Interactive D3.js graphs with color-coded difficulty levels
- **English Translations & Definitions**: Each word includes English translation, English definition, and example sentences
- **Word Collection System**: Double-click nodes to save words with level-based management

### 🇰🇷 Korean Learning
- **Korean News Analysis**: Analyzes Korean web content and extracts key vocabulary
- **Chinese Translation Reference**: Provides Chinese translations and definitions for Korean words
- **Knowledge Graph Visualization**: Interactive node graphs for exploring vocabulary relationships
- **Example Sentence Learning**: Korean example sentences with Chinese translations

### 🎮 Learning Games
- **Word Matching Game**: Memory-testing card matching
- **Typing Practice Game**: Spelling ability training
- **Listening Practice**: TTS voice generation for listening comprehension training

### 👤 User System
- **Account Registration/Login**: User data management via Supabase
- **Personalized Collections**: Independent word collection library for each user
- **Multilingual Interface**: Supports Traditional Chinese, Simplified Chinese, English, and Korean

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js (optional, for frontend development)
- Supabase account
- Google Gemini API Key

### Local Installation

1. **Clone the project**
```bash
git clone https://github.com/pupupeter/12312366.git
cd 12312366
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**

Create a `.env` file:
```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Gemini API
GEMINI_API_KEY=your_gemini_api_key
```

4. **Set up Supabase database**

Execute the following SQL in Supabase SQL Editor to create tables:

```sql
-- Users table
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT UNIQUE,
    language TEXT DEFAULT 'zh-TW',
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Chinese words collection table
CREATE TABLE chinese_words (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    chinese TEXT NOT NULL,
    english TEXT,
    definition TEXT,
    example_chinese TEXT,
    example_english TEXT,
    level TEXT,
    level_category TEXT,
    level_number TEXT,
    saved_at TIMESTAMP DEFAULT NOW()
);

-- Korean words collection table
CREATE TABLE korean_words (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    korean TEXT NOT NULL,
    chinese TEXT,
    definition TEXT,
    example_korean TEXT,
    example_chinese TEXT,
    saved_at TIMESTAMP DEFAULT NOW()
);
```

5. **Start the application**
```bash
python railway_app.py
```

The application will start at `http://localhost:8080`

---

## 📖 How to Use

### Chinese Vocabulary Analysis

1. After logging in, click "Chinese Vocabulary Learning"
2. Enter a URL or paste plain text
3. Click "Start Analysis"
4. Wait for AI analysis to complete, then the knowledge graph will open automatically

**Knowledge Graph Operations:**
- **Hover over nodes**: View detailed word information (English translation, definition, example sentences)
- **Double-click nodes**: Save words to your personal list
- **Drag nodes**: Rearrange the graph
- **Scroll wheel zoom**: Zoom in/out of the graph
- **Click "❓ Help"**: View complete usage instructions

**TOCFL Level Colors:**
- 🟢 Green: Level 1-2 (Basic)
- 🟡 Yellow: Level 3 (Intermediate)
- 🟠 Orange: Level 4-5 (Intermediate-Advanced)
- 🔴 Red: Level 6-7 (Advanced)
- ⚫ Gray: Ungraded

### Korean Vocabulary Analysis

1. After logging in, click "Korean Vocabulary Learning"
2. Enter a Korean webpage URL
3. Click "Start Analysis"
4. View the knowledge graph and save words

**Knowledge Graph Operations:**
- **Hover over nodes**: View Chinese translations and example sentences for Korean words
- **Double-click nodes**: Save words
- **Click "❓ 使用說明"**: View Chinese operation guide

### Learning Games

1. Click "Word Learning Games"
2. Choose game type:
   - **Matching Game**: Flip cards to match words with translations
   - **Typing Game**: Enter correct words based on prompts
3. Game content comes from your saved words

### Manage Collections

- Click "📚 My Collections" to view all saved words
- Filter by language and level
- Delete unwanted words
- Export as CSV file for external use

---

## 🛠️ Deployment Methods

### Railway Deployment (Recommended)

Railway offers free tier quota, suitable for quick deployment.

1. **Preparation**
   - Register a [Railway](https://railway.app/) account
   - Fork this project to your GitHub

2. **Create new project**
   - Log in to Railway
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your forked project

3. **Configure environment variables**

   Add in Railway project's Variables page:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   GEMINI_API_KEY=your_gemini_api_key
   PORT=8080
   ```

4. **Deployment configuration**

   Railway will automatically detect the Python project and use the following settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python railway_app.py`

5. **Complete deployment**
   - Railway will automatically deploy and provide a public URL
   - Example: `https://your-app.railway.app`

6. **Auto deployment**
   - Every push to GitHub main branch
   - Railway will automatically redeploy

### Vercel Deployment (Alternative)

Vercel can also deploy Python Flask applications.

1. **Prepare vercel.json**

   Ensure `vercel.json` exists in project root:
   ```json
   {
     "version": 2,
     "builds": [
       {
         "src": "railway_app.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "railway_app.py"
       }
     ]
   }
   ```

2. **Deploy to Vercel**
   ```bash
   npm i -g vercel
   vercel
   ```

3. **Configure environment variables**

   Add in Vercel Dashboard Settings → Environment Variables:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `GEMINI_API_KEY`

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env to fill in your configuration

# Start development server
python railway_app.py
```

Visit `http://localhost:8080`

---

## 📁 Project Structure

```
12312366/
├── railway_app.py              # Main application (Flask)
├── chinese_analysis.py         # Chinese graph generation
├── korean_analysis.py          # Korean graph generation
├── supabase_utils.py          # Supabase database operations
├── tocfl_loader.py            # TOCFL vocabulary loader
├── translations.py            # Multilingual translations
├── templates/                 # HTML templates
│   ├── dashboard.html         # Main dashboard
│   ├── review22.html          # Collections page
│   ├── games/                 # Game pages
│   └── ...
├── static/                    # Static resources
├── 14452詞語表202504.csv      # TOCFL vocabulary list
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (not committed to Git)
└── README.md                  # This file
```

---

## 🔧 Tech Stack

### Backend
- **Flask**: Web framework
- **Supabase**: Database (PostgreSQL)
- **Google Gemini**: AI vocabulary analysis
- **smolagents**: AI Agent framework

### Frontend
- **D3.js**: Knowledge graph visualization
- **Bootstrap**: UI framework
- **Jinja2**: Template engine

### Deployment
- **Railway**: Primary deployment platform
- **Vercel**: Alternative deployment platform

---

## 🌐 Environment Variables

| Variable Name | Description | Required |
|--------------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | ✅ |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | ✅ |
| `GEMINI_API_KEY` | Google Gemini API key | ✅ |
| `PORT` | Application port (default 8080) | ❌ |

---

## 📝 FAQ

### Q: How to get Gemini API Key?
A: Visit [Google AI Studio](https://makersuite.google.com/app/apikey) to apply for a free API Key.

### Q: How to set up Supabase?
A:
1. Register at [Supabase](https://supabase.com/)
2. Create a new project
3. Find URL and anon key in Settings → API
4. Execute table creation SQL in SQL Editor

### Q: Can't log in after deployment?
A: Verify Supabase environment variables are configured correctly and check if tables have been created.

### Q: Chinese analysis not responding?
A: Check if Gemini API Key is valid and if you have API quota.

### Q: Graph displays blank?
A: Verify browser supports D3.js; recommend using latest Chrome or Firefox.

---

## 📄 License

MIT License

---

## 👨‍💻 Developer

Developed with assistance from Claude Code

---

## 🔗 Related Links

- [Supabase Documentation](https://supabase.com/docs)
- [Railway Documentation](https://docs.railway.app/)
- [Google Gemini API](https://ai.google.dev/)
- [D3.js Documentation](https://d3js.org/)
