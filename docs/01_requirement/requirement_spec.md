# Zoho MCP Server – Requirements Specification (Draft v0.1)

> **作成日** 2025‑06‑17   **作成者** ChatGPT (draft for review)  
> 本書は *Cursor IDE / Claude など MCP 対応クライアント* から自然言語で Zoho アプリケーションを操作できる社内共通 “MCP ハブ” を Render に構築するための **要求仕様書** です。今後のレビューに基づき改訂します。

***

## 1. 背景と目的

- プロジェクト管理データが **Zoho Projects**（タスク、マイルストーン、WorkDrive ファイル）に分散している。

- 開発者はローカルの **Cursor IDE**／**Claude** で作業しており、タスク登録や進捗確認を **自然言語** だけで行いたい。

- その橋渡しとして **Model Context Protocol (MCP)** を採用し、標準 JSON‑RPC 経由で安全に Zoho API を呼び出すハブを構築する。

## 2. スコープ

| フェーズ              | 対象 Zoho アプリ                   | 主要機能                                                           |
| ----------------- | ----------------------------- | -------------------------------------------------------------- |
| **Phase 1 (MVP)** | **Zoho Projects** / WorkDrive | • タスク CRUD • タスクリスト取得・進捗集計 • WorkDrive ファイル DL/UL • Webhook 連携 |
| **Phase 2**       | Books • CRM                   | 見積・請求書取得、取引先情報 CRUD など                                         |

> 本書では **Phase 1** の詳細を定義し、Phase 2 は将来拡張要件として記載。

## 3. システム概要

```mermaid
flowchart TD
  subgraph Client
    C1[Cursor IDE]
    C2[Claude]
  end
  C1 -- JSON‑RPC --> S[MCP Server @Render]
  C2 -- JSON‑RPC --> S
  S -- OAuth2 --> ZP[Zoho Projects REST]
  S -- OAuth2 --> ZD[Zoho WorkDrive REST]
  ZP -. Webhook .-> S
  S --> GH[GitHub Repo]  %% Markdown 同期 (任意)
```

- **言語** : Python 3.12, FastAPI, `fastapi‑mcp`

- **ホスティング** : Render (plan Starter, region=Oregon) – Blueprint 管理

- **認証** : Zoho OAuth2 *Server‑based* flow。MCP 自体は Bearer JWT + IP 制限

## 4. 機能要求 (Phase 1)

| ID      | 機能                  | 説明                                                | 優先度            |
| ------- | ------------------- | ------------------------------------------------- | -------------- |
| **F‑1** | `listTasks`         | 指定プロジェクトのタスク一覧を取得（status フィルタ可）                   | High           |
| **F‑2** | `createTask`        | タスク名／担当／期日で新規タスクを生成                               | High           |
| **F‑3** | `updateTask`        | 既存タスクの status, dueDate, owner を変更                 | High           |
| **F‑4** | `getProjectSummary` | タスク完了率・遅延数を集計し JSON 返却                            | High           |
| **F‑5** | `downloadFile`      | WorkDrive フォルダからファイル取得（レビュー用）                     | Medium         |
| **F‑6** | `uploadReviewSheet` | 指摘事項表 (xlsx/md) を WorkDrive にアップロード               | Medium         |
| **F‑7** | `searchFiles`       | キーワードで WorkDrive 内を検索                             | Medium         |
| **F‑8** | Webhook 受信          | Zoho Projects の task.updated → GitHub Markdown 同期 | Low (optional) |
| **F‑9** | `getTaskDetail`     | タスク / バグ ID を指定して詳細情報（説明・コメント・履歴）を取得              | High           |

### 4.1 MCP Manifest 主要ツール定義 MCP Manifest 主要ツール定義

```jsonc
{
  "name": "listTasks",
  "parameters": {"project_id":"string","status":{"type":"string","enum":["open","closed","overdue"]}}
}
```

*(createTask / updateTask / downloadFile などは別紙 API 対応表を参照)*

## 5. 非機能要求

| 区分           | 要件                                                                    |
| ------------ | --------------------------------------------------------------------- |
| **性能**       | 通常操作: 95% < 500 ms (Render Starter 1 x CPU)                           |
| **スケーラビリティ** | Render Auto‑scale ON (max 3 instances)                                |
| **可用性**      | 99.5 % / 月 (Render Starter SLA)                                       |
| **セキュリティ**   | • TLS 1.2+ • Zoho OAuth scope 最小 • JWT 認証 • IP allow‑list (社内 VPN 範囲) |
| **監査**       | `callTool`, `error` を Render Logs → BigQuery へ 90 日保管                 |
| **国際化**      | クライアントからの locale 指定で日本語/英語応答切替                                        |
| **バックアップ**   | Refresh Token は Render Secrets + 1Password 冗長保管                       |

## 6. インタフェース仕様

### 6.1 MCP エンドポイント

- `POST /mcp` – JSON‑RPC 2.0

- `GET /manifest.json` – ツールメタ

### 6.2 Zoho API マッピング

| MCP Tool     | Zoho Endpoint              | Method |
| ------------ | -------------------------- | ------ |
| listTasks    | `/projects/{id}/tasks/`    | GET    |
| createTask   | 同上                         | POST   |
| updateTask   | `/tasks/{task_id}/`        | PUT    |
| downloadFile | `/workdrive/v1/files/{id}` | GET    |

### 6.3 Webhook

- **URL** : `/webhook/task-updated`

- **認証** : Zoho HMAC header 検証

## 7. データモデル (抜粋)

```yaml
task:
  id: string
  name: string
  owner: string
  status: enum(open,closed,overdue)
  due_date: date
```

## 8. デプロイ & 環境設定

- `render.yaml` で **Web Service + Cron Job** を IaC 管理。

- 環境変数 (secret) : `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`, `JWT_SECRET`, `PORTAL_ID`。

- CI/CD: GitHub Actions → `render.yaml` auto deploy。

## 9. 運用・監視

| 項目       | 内容                                                             |
| -------- | -------------------------------------------------------------- |
| **監視**   | Render Health Check `/health` + Prometheus exporter (optional) |
| **アラート** | 5xx > 2 % / 5 min → Slack `#mcp-alerts` 通知                     |
| **ログ保管** | Cloud Storage (30 days) → BigQuery (90 days)                   |

## 10. 制約・前提

- Zoho API レート制限 120 req/min — MCP 側で <100 req/min にスロットル。

- Render Free プランではアイドル 15 min でスリープ→ **Starter 以上必須**。

- WorkDrive API は 1 GB/req リミット。大容量ファイルは Phase 2 で検討。

## 11. 拡張ロードマップ (Phase 2+)

1. **Zoho Books** – 見積/請求書 CRUD (`listInvoices`, `createInvoice` …)。

2. **Zoho CRM** – 取引先・商談 CRUD (`listDeals`, `updateDealStage` …)。

3. **Vector DB 埋め込み** による全文検索／Q\&A。

## 12. 受入れ基準 (MVP)

| 試験項目          | 合格条件                                     |
| ------------- | ---------------------------------------- |
| 単体 #T‑001     | `createTask` ツール → Zoho でタスクが生成され ID が返る |
| 結合 #I‑003     | Cursor から自然言語「**新規タスク作成**」→ MCP 呼び出し成功   |
| 非機能 #N‑002    | 100 連続 `listTasks` で 5xx エラー率 0 %        |
| セキュリティ #S‑001 | 無認証アクセスで 401 が返る                         |

## 13. 体制 & スケジュール (Phase 1)

| 週  | 主タスク                                    | 担当           |
| -- | --------------------------------------- | ------------ |
| W1 | 要件確定・リポジトリ初期化                           | PM, Lead Dev |
| W2 | Zoho OAuth, `list/create/updateTask` 実装 | Backend Dev  |
| W3 | WorkDrive download/upload, Webhook      | Backend Dev  |
| W4 | JWT Auth, Render デプロイ, CI/CD            | DevOps       |
| W5 | テスト・ドキュメント整備                            | QA           |
| W6 | UAT / リリース                              | PM           |

## 14. 用語集

| 略語        | 意味                                     |
| --------- | -------------------------------------- |
| MCP       | Model Context Protocol – LLM↔外部ツール連携規格 |
| WorkDrive | Zoho ドライブ型ストレージサービス                    |
| JWT       | JSON Web Token                         |

***

### 次のアクション

1. 本ドラフトの **抜け漏れ・優先度** を確認し、コメントを追記してください。

2. Phase 1 内で **必須 / 任意** 機能の再確認。

3. 各担当者・スケジュールのアサイン決定。
