# GPTFlow

基於 Python 3.12+ 與 Clean Architecture 的非同步 ChatGPT Web 客戶端與 CLI 工具。

---

## 快速開始

### 1. 安裝環境
```bash
uv sync
```

### 2. 匯入憑證
在瀏覽器開啟 `https://chatgpt.com`，於開發者工具（F12）網路標籤頁匯出包含登入態的 HAR 檔案：
```bash
uv run gptflow auth import "路徑/封包.har"
```

---

## CLI 指令說明

### chat (問答與多輪對話)
發送提示詞並以串流格式即時輸出回答。

語法：`gptflow chat [OPTIONS] PROMPT`

| 參數 / 選項 | 類型 | 預設值 | 說明 |
| :--- | :---: | :---: | :--- |
| `PROMPT` | `str` | (必填) | 提問內容 |
| `-m, --model` | `str` | `auto` | 模型型號 (`auto`, `o1`, `o3-mini`, `gpt-4o`) |
| `-t, --thinking` | `flag` | `False` | 開啟思考鏈模式 (Thinking / CoT) |
| `-s, --session` | `str` | `None` | 接續既有會話 ID |
| `-d, --debug` | `flag` | `False` | 開啟詳細除錯日誌 |

範例：
```bash
# 基本問答
uv run gptflow chat "請說明什麼是量子糾纏？"

# 開啟思考模式
uv run gptflow chat "請分析 13*14 的心算方式" -t

# 指定會話 ID 接續對話
uv run gptflow chat "那 17*18 呢？" -s <會話ID>
```

---

### auth (憑證管理)
管理身分認證、查看登入態與刷新 Token。

| 子指令 | 語法 | 說明 | 範例 |
| :--- | :--- | :--- | :--- |
| `import` | `gptflow auth import <FILE>` | 匯入 HAR 或 JSON 憑證 | `uv run gptflow auth import path/to/file.har` |
| `status` | `gptflow auth status` | 查看帳號、方案與 Token 有效性 | `uv run gptflow auth status` |
| `refresh` | `gptflow auth refresh [--debug]` | 使用 Session Cookie 刷新 Access Token | `uv run gptflow auth refresh` |

---

### session (會話管理)
檢視本地儲存的對話紀錄。

| 子指令 | 語法 | 說明 | 範例 |
| :--- | :--- | :--- | :--- |
| `list` | `gptflow session list` | 列出所有本地會話 ID 與訊息數 | `uv run gptflow session list` |
| `show` | `gptflow session show <SESSION_ID>` | 顯示指定會話的完整問答紀錄 | `uv run gptflow session show <會話ID>` |

---

## Token 與 Cookie 機制

| 憑證類型 | 預估效期 | 機制與處置方式 |
| :--- | :---: | :--- |
| **Sentinel Token** | 約 3 分鐘 | 背景 Token 池自動運算 PoW 換發，使用者無感。 |
| **Access Token** | 10~14 天 | 過期時系統自動透過 Session 端點刷新；亦可手動執行 `auth refresh`。 |
| **Session Cookie** | 30~90 天 | 每次呼叫自動滾動續期。若主動登出或過期，需重新匯入 HAR。 |
| **Cloudflare Cookie** | 浮動 | 與外網 IP 強綁定。若 IP 變更遭遇 403 阻擋，需在瀏覽器重整並重新匯入 HAR。 |

---

## 測試與代碼檢查

```bash
uv run pytest        # 執行單元測試
uv run ruff check .  # 靜態代碼檢查
uv run ruff format . # 代碼格式化
```
