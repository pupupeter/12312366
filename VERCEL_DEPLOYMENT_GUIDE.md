# Vercel 部署指南

## 專案概述

本專案包含多個 Flask 應用：
- `auth_app.py` - 主應用（用戶認證、代理路由）運行於 port 8080
- `web_app.py` - 韓文新聞系統，運行於 port 5000
- `web_app22.py` - 中文詞彙系統，運行於 port 5001
- `gemini_tts_auth_app.py` - Streamlit TTS 應用，運行於 port 8501

## 重要限制

### Vercel 的限制
1. **Serverless 架構** - Vercel 是無伺服器平台，無法同時運行多個持久性進程
2. **無法使用 subprocess** - 目前 `auth_app.py` 使用 subprocess 啟動其他服務，這在 Vercel 上不可行
3. **執行時間限制** - 免費版最長 10 秒，Pro 版最長 60 秒
4. **無持久性文件系統** - 無法寫入本地檔案

---

## 部署方案

### 方案 A：合併為單一應用（推薦）

將所有功能合併到一個 Flask 應用中，這樣只需部署一個服務。

#### 步驟 1：建立 `api/index.py`

```python
# api/index.py
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from auth_app import app

# Vercel 需要這個
app = app
```

#### 步驟 2：建立 `vercel.json`

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

#### 步驟 3：建立 `requirements.txt`

```txt
flask==3.0.0
python-dotenv==1.0.0
supabase==2.0.0
requests==2.31.0
google-genai==0.3.0
smolagents==0.1.0
markdownify==0.11.6
```

#### 步驟 4：重構應用

需要將 `web_app.py` 和 `web_app22.py` 的路由整合到 `auth_app.py` 中，移除 subprocess 的使用。

---

### 方案 B：使用多個 Vercel 專案

將每個應用分開部署到不同的 Vercel 專案。

| 應用 | Vercel 專案 | 用途 |
|------|------------|------|
| auth_app.py | your-app-auth | 主應用、認證 |
| web_app.py | your-app-korean | 韓文系統 |
| web_app22.py | your-app-chinese | 中文系統 |

**缺點**：需要處理跨域（CORS）和不同域名間的 session 共享。

---

### 方案 C：使用其他平台（更適合本專案）

由於專案架構複雜，以下平台可能更適合：

| 平台 | 優點 | 缺點 |
|------|------|------|
| **Railway** | 支援多進程、Docker | 免費額度有限 |
| **Render** | 免費 tier、支援多服務 | 冷啟動較慢 |
| **Fly.io** | 全球部署、Docker 支援 | 設定較複雜 |
| **Heroku** | 簡單部署 | 已無免費方案 |

---

## 推薦：方案 A 詳細步驟

### 1. 建立必要檔案

#### `api/index.py`
```python
import sys
import os

# 將專案根目錄加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
import hashlib
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from supabase_utils import (
    get_user_by_username,
    create_user,
    update_user,
    update_user_password,
    update_user_language,
    update_last_login,
    check_email_exists,
    get_korean_words,
    add_korean_word,
    delete_korean_word,
    get_chinese_words,
    add_chinese_word,
    delete_chinese_word
)

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# ... 將 auth_app.py 的路由複製到這裡
# ... 將 web_app.py 的路由整合（改 prefix 為 /korean-app/）
# ... 將 web_app22.py 的路由整合（改 prefix 為 /chinese-app/）
```

#### `vercel.json`
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ],
  "env": {
    "SUPABASE_URL": "@supabase_url",
    "SUPABASE_ANON_KEY": "@supabase_anon_key",
    "GEMINI_API_KEY": "@gemini_api_key",
    "SECRET_KEY": "@secret_key"
  }
}
```

#### `requirements.txt`
```txt
flask==3.0.0
python-dotenv==1.0.0
supabase==2.0.0
requests==2.31.0
google-genai==0.3.0
smolagents==0.1.0
markdownify==0.11.6
litellm==1.0.0
```

### 2. 設定環境變數

在 Vercel Dashboard 中設定：
- `SUPABASE_URL` - 你的 Supabase URL
- `SUPABASE_ANON_KEY` - 你的 Supabase Anon Key
- `GEMINI_API_KEY` - 你的 Gemini API Key
- `SECRET_KEY` - Flask session 加密金鑰

### 3. 需要修改的程式碼

#### 移除 subprocess 相關
```python
# 刪除這些代碼
web_app_process = None
web_app22_process = None
streamlit_process = None

def start_web_app():
    ...

def start_web_app22():
    ...

def start_streamlit():
    ...
```

#### 修改代理路由為直接路由
原本使用 requests 代理到其他 port 的方式需要改為直接處理：

```python
# 原本（代理方式）
@app.route('/korean-app/<path:path>')
def proxy_korean(path):
    resp = requests.get(f'http://localhost:5000/{path}')
    ...

# 修改為（直接整合）
@app.route('/korean-app/')
def korean_index():
    return render_template('index.html')

@app.route('/korean-app/api/saved-words')
def korean_saved_words():
    user_id = session.get('user_id', 'default')
    words = get_korean_words(user_id)
    return jsonify({'words': words})
```

---

## 部署前檢查清單

- [ ] 建立 `api/index.py`
- [ ] 建立 `vercel.json`
- [ ] 建立 `requirements.txt`
- [ ] 移除所有 subprocess 相關程式碼
- [ ] 將 web_app.py 和 web_app22.py 的路由整合
- [ ] 移除代理路由，改為直接路由
- [ ] 在 Vercel 設定環境變數
- [ ] 確保 templates 和 static 路徑正確
- [ ] 測試所有 API 端點

---

## 預估工作量

| 任務 | 預估時間 |
|------|----------|
| 建立 Vercel 配置檔 | 30 分鐘 |
| 整合三個 Flask 應用 | 2-3 小時 |
| 移除 subprocess/代理邏輯 | 1-2 小時 |
| 測試與除錯 | 1-2 小時 |
| **總計** | **5-8 小時** |

---

## 替代方案：Railway 部署（推薦）

如果不想大幅修改程式碼，Railway 是更好的選擇：

### 步驟
1. 建立 `Procfile`：
   ```
   web: python auth_app.py
   ```

2. 建立 `railway.json`：
   ```json
   {
     "$schema": "https://railway.app/railway.schema.json",
     "build": {
       "builder": "NIXPACKS"
     },
     "deploy": {
       "startCommand": "python auth_app.py",
       "restartPolicyType": "ON_FAILURE"
     }
   }
   ```

3. 在 Railway 設定環境變數

4. Railway 支援多進程，所以 subprocess 的方式可以繼續使用

---

## 下一步

請告訴我你想採用哪個方案，我可以幫你：
1. **方案 A** - 整合所有應用到單一 Flask app 並部署到 Vercel
2. **方案 C** - 部署到 Railway（最少修改）
3. 其他平台

選擇後我會幫你建立所需的檔案和修改程式碼。
