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
- `get_project_tasks.py` - プロジェクトタスクデータ取得（MCP経由）
- `generate_task_report.py` - Markdownタスクレポート生成
- `export_project_task_details.py` - 詳細JSONエクスポート

### 📁 WorkDrive関連
- `workdrive_summary.py` - **WorkDrive総合情報表示（推奨）**
- `get_workspace_files.py` - **ワークスペースファイル取得（特化型）**

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
python tools/get_project_tasks.py --project-id YOUR_PROJECT_ID

# レポート生成
python tools/generate_task_report.py

# WorkDrive情報確認（総合）
python tools/workdrive_summary.py

# WorkDrive ワークスペースファイル取得（特化）
python tools/get_workspace_files.py --details
python tools/get_workspace_files.py --team-id YOUR_TEAM_ID --query "検索語"
```

### トラブルシューティング
```bash
# OAuth認証問題の診断
python tools/diagnose_oauth.py

# 設定・動作確認
python tools/verify_setup.py
```

## ✅ ファイル整理完了

重複機能を持つファイルの整理が完了しました：

### 削除されたファイル
- ~~`get_folder_contents.py`~~ - workdrive_summaryに統合  
- ~~`get_folder_files.py`~~ - workdrive_summaryに統合
- ~~`get_team_folders.py`~~ - workdrive_summaryに統合
- ~~`generate_jwt_token.py`~~ - 特殊用途のみ、通常運用では不要

### 復活したファイル
- `get_workspace_files.py` - ワークスペースファイル取得に特化した軽量版

### メリット
✅ **メンテナンス性向上** - 重複コードの削減  
✅ **使いやすさ向上** - 選択肢が明確  
✅ **混乱防止** - 似た機能のツールが複数あることによる混乱を防止  
✅ **特化機能** - 用途別に最適化されたツール  
✅ **ディスク容量節約** - 約40KB程度の節約

現在のtoolsディレクトリは最適化され、必要最小限かつ用途別に特化した機能を提供しています。 