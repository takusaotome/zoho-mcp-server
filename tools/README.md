# Tools Directory

このディレクトリには必要なユーティリティスクリプトのみが含まれています。
重複機能を持つツールは整理により削除されています。

## 📁 ファイル構成

### 🚀 セットアップ・認証関連
- `setup_wizard.py` - **自動セットアップウィザード（推奨）**
- `generate_jwt_secret.py` - JWT秘密鍵生成
- `generate_zoho_auth_url.py` - Zoho OAuth認証URL生成（自動認証対応）

### 🔍 診断・確認
- `diagnose_oauth.py` - OAuth認証問題の詳細診断
- `verify_setup.py` - セットアップ完了後の動作確認

### 📊 データ取得・レポート
- `get_real_portal_and_projects.py` - Portal・プロジェクト情報取得
- `get_project_tasks_via_mcp.py` - プロジェクトタスクデータ取得（MCP経由）
- `generate_task_report.py` - Markdownタスクレポート生成
- `export_project_task_details.py` - 詳細JSONエクスポート

## 🎯 推奨使用順序

### 初回セットアップ
```bash
# 1. 自動セットアップ（推奨）
python tools/setup_wizard.py

# または手動セットアップ
python tools/generate_jwt_secret.py
python tools/generate_zoho_auth_url.py
python tools/verify_setup.py
```

### 日常運用
```bash
# プロジェクト情報確認
python tools/get_real_portal_and_projects.py

# タスクデータ取得
python tools/get_project_tasks_via_mcp.py --project-id YOUR_PROJECT_ID

# レポート生成
python tools/generate_task_report.py
```

### トラブルシューティング
```bash
# OAuth認証問題の診断
python tools/diagnose_oauth.py

# 設定・動作確認
python tools/verify_setup.py
``` 