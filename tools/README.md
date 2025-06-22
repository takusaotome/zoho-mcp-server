# Tools Directory

このディレクトリには本格的なユーティリティスクリプトが含まれています。
一時的なテスト・デバッグファイルは整理により削除されています。

## ファイル分類

### 認証・設定関連
- `exchange_auth_code.py` - 認証コード交換
- `generate_zoho_auth_url.py` - Zoho 認証URL生成
- `check_configuration.py` - 設定確認

### データ取得スクリプト
- `get_real_portal_and_projects.py` - ポータル・プロジェクト情報取得
- `get_project_tasks_via_mcp.py` - プロジェクトタスクデータ取得（MCP経由）
- `get_zoho_projects_list.py` - Zoho プロジェクト一覧取得
- `get_portal_id.py` - ポータルID取得

### レポート生成・エクスポート
- `generate_task_report.py` - タスクレポート生成
- `export_project_task_details.py` - プロジェクトタスク詳細エクスポート

### 検証・確認
- `verify_setup.py` - セットアップ検証
- `final_verification.py` - 最終検証

## 使用方法

各スクリプトは独立して実行可能です。環境変数が適切に設定されていることを確認してから実行してください。

```bash
# 例：プロジェクト一覧を取得
python tools/get_zoho_projects_list.py

# 例：セットアップを検証  
python tools/verify_setup.py
``` 