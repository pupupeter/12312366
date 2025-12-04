# 🚀 Vercel 快速部署指南

## 📋 部署前檢查清單

✅ 代碼已推送到 GitHub
✅ `vercel.json` 已創建
✅ `requirements.txt` 已創建
✅ `api/index.py` 已創建
✅ 環境變數準備好了

## 🎯 快速步驟（5 分鐘內完成）

### 步驟 1：訪問 Vercel

打開瀏覽器，訪問：
```
https://vercel.com
```

### 步驟 2：登入

- 點擊右上角 "Sign Up" 或 "Log In"
- 選擇 "Continue with GitHub"
- 授權 Vercel 訪問你的 GitHub

### 步驟 3：導入項目

1. 在 Vercel Dashboard，點擊 "Add New..." → "Project"
2. 找到並選擇你的倉庫：`pupupeter/12312366`
3. 點擊 "Import"

### 步驟 4：配置項目

**Framework Preset:** 選擇 "Other"

**環境變數（最重要！）**

點擊 "Environment Variables"，添加以下變數：

| Key | Value | 說明 |
|-----|-------|------|
| `SUPABASE_URL` | `你的 Supabase URL` | 從 Supabase Dashboard 獲取 |
| `SUPABASE_ANON_KEY` | `你的 Supabase Key` | 從 Supabase Dashboard 獲取 |
| `SECRET_KEY` | `隨機字串` | 例如：`my-super-secret-key-12345` |

可選（用戶也可在介面輸入）：
| Key | Value | 說明 |
|-----|-------|------|
| `GEMINI_API_KEY` | `你的 Gemini Key` | 從 Google AI Studio 獲取 |

**重要：** 選擇應用到所有環境（Production, Preview, Development）

### 步驟 5：部署

1. 點擊底部的 "Deploy" 按鈕
2. 等待部署完成（約 2-3 分鐘）
3. 看到 "Congratulations!" 表示成功！

### 步驟 6：訪問你的應用

部署成功後，Vercel 會提供一個網址：
```
https://你的項目名.vercel.app
```

點擊即可訪問！

## 🔍 如何獲取環境變數？

### Supabase URL 和 Key

1. 登入 [Supabase](https://supabase.com)
2. 選擇你的項目
3. 左側選單 → Settings → API
4. 複製：
   - **Project URL** → 這是 `SUPABASE_URL`
   - **anon public** → 這是 `SUPABASE_ANON_KEY`

### Gemini API Key（可選）

1. 訪問 [Google AI Studio](https://aistudio.google.com/apikey)
2. 登入 Google 帳號
3. 點擊 "Create API Key"
4. 複製生成的 Key

## ⚠️ 重要提醒

### 1. 韓文/中文應用無法運行

Vercel 部署後，只有以下功能可用：
- ✅ 登入/註冊
- ✅ TTS 功能（完整可用）
- ❌ 韓文新聞系統（需要長運行進程）
- ❌ 中文詞彙系統（需要長運行進程）

### 2. 音頻文件不會永久保存

- 生成的音頻存儲在 `/tmp`
- 只能即時播放和下載
- 函數執行後會自動清除

### 3. 執行時間限制

**免費方案：** 最長 10 秒
- 如果生成過程超時，請：
  - 嘗試較短的網頁
  - 或考慮升級到 Pro Plan

## 🎨 部署後自定義

### 更改域名

1. Vercel Dashboard → Settings → Domains
2. 添加你的自定義域名
3. 按提示配置 DNS

### 查看日誌

1. Vercel Dashboard → Deployments
2. 點擊最新的部署
3. 查看 "Functions" 標籤頁
4. 點擊函數查看日誌

## 🐛 部署問題排查

### 問題：部署失敗

**檢查：**
1. GitHub 代碼是否最新？
2. `requirements.txt` 是否存在？
3. `api/index.py` 是否存在？

### 問題：應用無法訪問

**檢查：**
1. 環境變數是否都設置了？
2. Supabase URL 和 Key 是否正確？
3. 查看 Vercel 的 Functions 日誌

### 問題：TTS 功能報錯

**檢查：**
1. 是否輸入了 Gemini API Key？
2. API Key 是否有效？
3. 是否超過免費額度？

## 📊 測試清單

部署成功後，測試：

- [ ] 訪問首頁
- [ ] 註冊新帳號
- [ ] 登入系統
- [ ] 訪問 `/tts` 頁面
- [ ] 輸入網址生成對話
- [ ] 編輯對話內容
- [ ] 重新生成音頻
- [ ] 播放音頻
- [ ] 下載音頻
- [ ] 登出

## 🎉 完成！

恭喜！你的 TTS 應用現在已經部署到全球 CDN！

**分享你的網址：**
```
https://你的項目名.vercel.app
```

## 📚 更多資源

- [完整部署指南](VERCEL_DEPLOY_GUIDE.md)
- [項目更新日誌](CHANGELOG.md)
- [TTS 整合說明](TTS_INTEGRATION_README.md)
- [Vercel 官方文檔](https://vercel.com/docs)

---

需要幫助？查看 [GitHub Issues](https://github.com/pupupeter/12312366/issues)
