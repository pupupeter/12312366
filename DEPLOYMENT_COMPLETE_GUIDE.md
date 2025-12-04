# 🚀 完整部署指南 - Vercel + Railway 混合架構

## 📋 部署概覽

你的應用使用**混合部署架構**：

| 平台 | 負責功能 | 部署狀態 |
|------|----------|----------|
| **Vercel** | TTS、用戶認證、Dashboard | ✅ 已部署 |
| **Railway** | 韓文新聞、中文詞彙、單字收藏、遊戲 | 🔄 需要完成 |

## 🎯 完成 Railway 部署（3 步驟）

### 步驟 1：等待 Railway 自動部署

Railway 會自動檢測到你的 GitHub 更新並重新部署。

1. 訪問 Railway Dashboard
2. 查看 "Deployments" 標籤
3. 等待部署完成（約 2-3 分鐘）
4. 看到綠色勾勾 ✅ 表示成功

### 步驟 2：獲取 Railway 網址

1. 在 Railway 項目中，點擊你的服務
2. 點擊 "Settings" 標籤
3. 找到 "Networking" → "Domains"
4. 如果還沒有域名，點擊 "Generate Domain"
5. 複製生成的網址，例如：
   ```
   https://12312366-production.up.railway.app
   ```

### 步驟 3：在 Vercel 設置 Railway 網址

1. 訪問 Vercel Dashboard
2. 選擇你的項目
3. 點擊 "Settings" → "Environment Variables"
4. 添加新變數：
   ```
   變數名：RAILWAY_URL
   值：https://你剛複製的railway網址.up.railway.app
   ```
5. 選擇應用到所有環境（Production, Preview, Development）
6. 點擊 "Save"
7. 重新部署 Vercel（Settings → Deployments → 點擊最新部署的 "..." → "Redeploy"）

## ✅ 測試你的完整系統

### 1️⃣ 測試 Vercel（TTS 功能）

訪問：`https://你的vercel網址.vercel.app`

- [ ] 登入系統
- [ ] 訪問 Dashboard
- [ ] 點擊 "🎙️ AI 語音對話生成器"
- [ ] 測試 TTS 功能（輸入網址或手動輸入）
- [ ] 播放生成的音頻
- [ ] 下載音頻文件

### 2️⃣ 測試 Railway（知識圖譜）

在 Vercel Dashboard 點擊：

**韓文新聞系統：**
- [ ] 點擊 "📰 韓文新聞系統"
- [ ] 應該自動跳轉到 Railway 並登入
- [ ] 測試韓文新聞查詢（需要 Naver API）
- [ ] 測試單字收藏功能
- [ ] 訪問複習頁面

**中文詞彙系統：**
- [ ] 點擊 "📚 中文詞彙系統"
- [ ] 應該自動跳轉到 Railway 並登入
- [ ] 測試中文詞彙查詢
- [ ] 測試單字收藏功能
- [ ] 訪問複習頁面

### 3️⃣ 測試單點登入

- [ ] 在 Vercel 登入
- [ ] 點擊韓文/中文卡片跳轉到 Railway
- [ ] 確認**沒有被要求再次登入**
- [ ] 確認用戶名正確顯示
- [ ] 確認可以正常收藏單字

## 🔑 必須的 API Keys

### Vercel 環境變數（已設置）

```
✅ SUPABASE_URL
✅ SUPABASE_ANON_KEY
✅ SECRET_KEY
✅ GEMINI_API_KEY
🆕 RAILWAY_URL (需要添加)
```

### Railway 環境變數（已設置）

```
✅ SUPABASE_URL
✅ SUPABASE_ANON_KEY
✅ SECRET_KEY
✅ GEMINI_API_KEY
⚠️ NAVER_CLIENT_ID (需要申請)
⚠️ NAVER_CLIENT_SECRET (需要申請)
```

## 📝 申請 Naver API（可選，韓文新聞需要）

### 如果沒有 Naver API：

1. 訪問：https://developers.naver.com/apps/#/register
2. 登入 Naver 帳號
3. 點擊 "애플리케이션 등록"（註冊應用程式）
4. 填寫：
   - 應用名稱：Korean News App（隨意）
   - 使用 API：勾選 "검색"（搜尋）
5. 註冊完成後，複製：
   - **Client ID**
   - **Client Secret**
6. 在 Railway 添加環境變數：
   ```
   NAVER_CLIENT_ID=你的Client ID
   NAVER_CLIENT_SECRET=你的Client Secret
   ```
7. Railway 會自動重新部署

### 如果不需要韓文新聞功能：

- 可以跳過 Naver API
- 中文詞彙系統仍然可以正常運作
- 韓文系統的 AI 對話功能仍然可用（不需要 Naver API）

## 🏗️ 架構說明

### 用戶流程：

```
用戶 → Vercel (登入)
     ↓
  Dashboard
     ├─→ TTS (在 Vercel)
     ├─→ 韓文新聞 (跳轉到 Railway + 自動登入)
     └─→ 中文詞彙 (跳轉到 Railway + 自動登入)
```

### 技術實現：

```
Vercel Dashboard
     │
     ├─→ 點擊韓文卡片
     │      ↓
     │   生成 URL: railway.app/korean?user=你的用戶名
     │      ↓
     │   Railway 接收並驗證用戶
     │      ↓
     │   自動設置 session（無需密碼）
     │      ↓
     │   用戶可以立即使用
     │
     └─→ 點擊中文卡片（同樣流程）
```

### 資料庫：

- 兩個平台**共用同一個 Supabase 資料庫**
- 用戶資料完全同步
- 收藏的單字在兩邊都可以看到

## 🐛 常見問題

### 問題 1：點擊韓文/中文卡片後被要求登入

**原因：** Railway 網址沒有正確設置

**解決：**
1. 檢查 Vercel 的 `RAILWAY_URL` 環境變數
2. 確認 Railway 部署成功
3. 檢查瀏覽器控制台（F12）查看跳轉的 URL 是否正確

### 問題 2：Railway 顯示 "The train has not arrived"

**原因：** Railway 部署失敗或還在進行中

**解決：**
1. 查看 Railway → Deployments → 最新部署的日誌
2. 檢查所有環境變數是否正確設置
3. 確認 `requirements.txt` 中的依賴都能安裝

### 問題 3：韓文新聞無法顯示

**原因：** 缺少 Naver API 或 API 配置錯誤

**解決：**
1. 確認已在 Railway 設置 `NAVER_CLIENT_ID` 和 `NAVER_CLIENT_SECRET`
2. 訪問 `/health` 端點檢查 API 狀態
3. 檢查 Railway 日誌中的錯誤訊息

### 問題 4：收藏的單字看不到

**原因：** Supabase 連接問題或用戶 ID 不匹配

**解決：**
1. 檢查兩個平台的 Supabase 環境變數是否相同
2. 確認用戶在兩邊都有正確的 session
3. 查看瀏覽器控制台的網路請求

## 💰 費用預估

### Vercel（免費方案）
- ✅ 完全免費
- ✅ 每月 100GB 頻寬
- ✅ 無限部署

### Railway（免費方案）
- ✅ 每月 $5 免費額度
- ✅ 足夠輕度到中度使用
- 💡 如果需要更多，升級到 $5/月 Hobby Plan

### Naver API
- ✅ 完全免費
- ✅ 每日 25,000 次請求

### Supabase（免費方案）
- ✅ 500MB 資料庫
- ✅ 足夠個人使用

### Gemini API
- ✅ 免費額度：每分鐘 15 次
- ✅ 足夠個人使用

**總計：完全免費** 🎉

## 🎉 恭喜！

你的多語言知識圖譜系統現在已經完全部署！

**系統功能：**
- ✅ 用戶認證系統
- ✅ AI 語音對話生成器（16 種語言）
- ✅ 韓文新聞知識圖譜
- ✅ 中文詞彙知識圖譜
- ✅ 單字收藏功能
- ✅ 互動式複習遊戲
- ✅ 單點登入體驗

**分享你的應用：**
```
https://你的vercel網址.vercel.app
```

## 📚 相關文檔

- [Vercel 快速部署指南](QUICK_DEPLOY.md)
- [Railway 部署指南](RAILWAY_DEPLOY_GUIDE.md)
- [API 文檔](API_DOCUMENTATION.md)

---

需要幫助？提交 [GitHub Issue](https://github.com/pupupeter/12312366/issues)
