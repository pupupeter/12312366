# Vercel 部署指南

## 📦 準備工作

### 1. 已完成的配置

✅ 所有必要的配置文件已創建：
- `vercel.json` - Vercel 配置
- `requirements.txt` - Python 依賴
- `api/index.py` - Vercel 無伺服器函數入口
- `.gitignore` - 忽略不必要的文件

### 2. 環境變數準備

你需要在 Vercel 設置以下環境變數：

**必須設置：**
- `SUPABASE_URL` - 你的 Supabase 項目 URL
- `SUPABASE_ANON_KEY` - 你的 Supabase 匿名密鑰
- `SECRET_KEY` - Flask session 密鑰（任意隨機字串）

**可選設置：**
- `GEMINI_API_KEY` - Gemini API 密鑰（用戶也可在介面輸入）

## 🚀 部署步驟

### 方法一：通過 Vercel 網站部署（推薦）

#### 步驟 1：推送代碼到 GitHub

代碼已經在 GitHub 上：
```
https://github.com/pupupeter/12312366
```

#### 步驟 2：登入 Vercel

1. 訪問 [vercel.com](https://vercel.com)
2. 使用 GitHub 帳號登入

#### 步驟 3：導入項目

1. 點擊 "Add New..." → "Project"
2. 選擇你的 GitHub 倉庫：`pupupeter/12312366`
3. 點擊 "Import"

#### 步驟 4：配置項目

**Framework Preset:**
- 選擇 "Other"（Vercel 會自動檢測到 Python）

**Root Directory:**
- 保持默認（留空）

**Build Settings:**
- Build Command: `# 留空`
- Output Directory: `# 留空`
- Install Command: `pip install -r requirements.txt`

#### 步驟 5：設置環境變數

在 "Environment Variables" 部分，添加：

```
SUPABASE_URL = 你的_Supabase_URL
SUPABASE_ANON_KEY = 你的_Supabase_Key
SECRET_KEY = 任意隨機字串（例如：your-super-secret-key-12345）
```

可選：
```
GEMINI_API_KEY = 你的_Gemini_API_Key
```

**重要：** 確保這些環境變數應用到所有環境（Production, Preview, Development）

#### 步驟 6：部署

1. 點擊 "Deploy"
2. 等待部署完成（通常 2-3 分鐘）
3. 部署成功後會顯示網址

### 方法二：使用 Vercel CLI

#### 安裝 Vercel CLI

```bash
npm install -g vercel
```

#### 登入

```bash
vercel login
```

#### 部署

```bash
vercel
```

按照提示操作：
1. 確認項目設置
2. 輸入環境變數
3. 等待部署完成

## ⚠️ 重要注意事項

### 1. 子進程問題

**問題：** Vercel 無伺服器環境不支援啟動子進程（`subprocess.Popen`）

**影響：**
- `web_app.py` (韓文新聞) - ❌ 無法在 Vercel 上運行
- `web_app22.py` (中文詞彙) - ❌ 無法在 Vercel 上運行
- TTS 功能 - ✅ 可以正常運行

**解決方案：**
你需要選擇以下方案之一：

#### 選項 A：分開部署（推薦）

1. **Vercel 部署** - 只部署 TTS 功能
   - 使用 `api/index.py`（已創建）
   - 移除 `web_app.py` 和 `web_app22.py` 的啟動代碼

2. **其他平台部署** - 韓文和中文應用
   - Railway.app
   - Render.com
   - Fly.io
   - 或任何支持長運行進程的平台

#### 選項 B：整合所有功能到單一應用

將 `web_app.py` 和 `web_app22.py` 的路由整合到 `api/index.py`
- 需要較多重構工作
- 但可以在 Vercel 上運行所有功能

#### 選項 C：只部署 TTS 到 Vercel

簡化版本，只包含：
- 登入/註冊
- TTS 功能
- 不包含韓文/中文應用

### 2. 文件存儲

**問題：** Vercel 無伺服器函數的文件系統是只讀的（除了 `/tmp`）

**解決：**
- 已將音頻文件保存到 `/tmp` 目錄
- `/tmp` 文件在函數執行後會被清除
- 生成的音頻只能即時播放和下載，不會永久保存

**如需永久存儲：**
- 使用 Vercel Blob Storage
- 或使用 S3/CloudFlare R2 等對象存儲

### 3. 函數執行時間限制

**Hobby Plan（免費）：**
- 最長執行時間：10 秒
- 可能不足以完成 URL → 對話 → TTS 的完整流程

**Pro Plan：**
- 最長執行時間：60 秒
- 足夠處理大部分請求

**建議：**
- 先測試看看是否在 10 秒內完成
- 如果超時，考慮升級或優化流程

## 🔧 部署後的配置建議

### 創建精簡版 TTS 應用（推薦）

如果你只想在 Vercel 上部署 TTS 功能，可以：

1. 創建一個新的分支：
```bash
git checkout -b vercel-tts-only
```

2. 移除 `api/index.py` 中的子進程啟動代碼

3. 簡化 dashboard，移除韓文和中文應用的卡片

4. 推送到 GitHub 並部署到 Vercel

## 📊 部署後測試清單

部署成功後，測試以下功能：

- [ ] 訪問首頁（應重定向到登入頁）
- [ ] 註冊新帳號
- [ ] 登入
- [ ] 訪問 TTS 頁面
- [ ] 輸入網址生成對話
- [ ] 編輯對話
- [ ] 重新生成音頻
- [ ] 播放音頻
- [ ] 下載音頻
- [ ] 登出

## 🐛 常見問題

### 問題 1：部署失敗 - Python 版本

**解決：** 在項目根目錄創建 `runtime.txt`：
```
python-3.11
```

### 問題 2：找不到模組

**解決：** 確認 `requirements.txt` 包含所有依賴

### 問題 3：環境變數未設置

**解決：**
1. 在 Vercel Dashboard → Settings → Environment Variables
2. 重新部署：Dashboard → Deployments → 三點選單 → Redeploy

### 問題 4：函數超時

**解決：**
- 優化代碼
- 考慮升級到 Pro Plan
- 或將長時間任務分解為多步驟

## 📱 自定義域名（可選）

部署成功後，你會得到一個 Vercel 域名：
```
your-app.vercel.app
```

如需自定義域名：
1. Settings → Domains
2. 添加你的域名
3. 根據提示配置 DNS

## 🎉 完成！

部署成功後，你的 TTS 應用將可以在全球訪問！

分享你的網址給朋友試用吧！🚀
