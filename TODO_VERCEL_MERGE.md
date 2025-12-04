# 待辦：合併 Flask 應用以部署 Vercel

## 目標
將 3 個 Flask 應用合併成 1 個，讓專案可以部署到 Vercel。

## 需要合併的檔案

| 檔案 | 行數 | 說明 |
|------|------|------|
| auth_app.py | 838 行 | 主應用（認證、dashboard） |
| web_app.py | 787 行 | 韓文新聞系統 |
| web_app22.py | 919 行 | 中文詞彙系統 |
| **總計** | **2544 行** | |

## 執行步驟

### 1. 建立合併後的主檔案
- 建立 `api/index.py`（Vercel 入口）
- 將 auth_app.py 的路由複製進去
- 將 web_app.py 的路由加上 `/korean-app` 前綴後複製進去
- 將 web_app22.py 的路由加上 `/chinese-app` 前綴後複製進去

### 2. 移除不需要的程式碼
- 移除 subprocess 相關（start_web_app, start_web_app22, start_streamlit）
- 移除代理路由（proxy_korean, proxy_chinese）
- 移除進程管理相關（stop_all_services, signal_handler）

### 3. 建立 Vercel 設定檔
- 建立 `vercel.json`
- 建立 `requirements.txt`

### 4. 設定環境變數
在 Vercel Dashboard 設定：
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `GEMINI_API_KEY`
- `SECRET_KEY`

## 預估時間
由 Claude 執行：約 **20-30 分鐘**

## 如何開始
直接跟 Claude 說：**「做 TODO_VERCEL_MERGE.md 的內容」**

---

## 替代方案（不用改程式碼）

如果不想合併，可以用 **Railway** 部署：
- 支援多進程
- 現有程式碼不用改
- 只需建立 Procfile 和設定環境變數

要用 Railway 的話，跟 Claude 說：**「幫我部署到 Railway」**
