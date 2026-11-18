# 中三 Python 互動式程式編寫練習與自動批改平台

香港道教聯合會圓玄學院第二中學 • 中三電腦科 Python 互動式自動批改平台（全套 69 題實戰題庫）。

## 專案檔案結構

```text
├── app.py              # Python Flask 後端伺服器（支援 SSE 即時推播排行榜、讀取 pw.txt、讀寫 leaderboard.txt）
├── index.html          # 前端互動式程式編寫平台（Pyodide Python 3 自動批改、69 題題庫、即時排行榜）
├── pw.txt              # 後端教師密碼設定檔（預設密碼：，可自行修改）
├── leaderboard.txt     # 全級學生進度與排行榜資料儲存檔
├── requirements.txt    # Python 依賴套件清單
├── .gitignore          # Git 忽略規則
└── README.md           # 專案說明文件
```

## 快速啟動指南

1. **安裝依賴套件**：
   ```bash
   pip install -r requirements.txt
   ```

2. **設定教師密碼**：
   開啟 `pw.txt` 並輸入自訂的教師密碼（預設為 ``）。教師密碼僅保存於後端 `pw.txt`，不會暴露在前端網頁原始碼中。

3. **啟動伺服器**：
   ```bash
   python app.py
   ```
   啟動後開啟瀏覽器前往 `http://localhost:5000`（或伺服器區網 IP `http://<IP>:5000`）即可讓全班學生同時使用並即時更新排行榜。
