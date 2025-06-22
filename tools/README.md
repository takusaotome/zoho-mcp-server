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
- `get_workspace_files.py` - **ワークスペースファイル取得（軽量版）**

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
# プロジェクトタスク取得
python tools/get_project_tasks.py

# WorkDriveファイル確認
python tools/workdrive_summary.py
python tools/get_workspace_files.py

# レポート生成
python tools/generate_task_report.py
```

## 📖 各ツールの詳細説明

### 🚀 セットアップ・認証関連

#### `setup_wizard.py`
- **推奨**: 初回セットアップ用ウィザード
- 環境変数設定、OAuth認証、動作確認を自動実行
- 対話形式で簡単セットアップ

#### `generate_jwt_secret.py`
- JWT認証用の秘密鍵生成
- 256-bitランダムキー生成

#### `generate_zoho_auth_url.py`
- Zoho OAuth認証URL生成
- 自動ブラウザ起動とコールバック処理
- 認証フロー完全自動化対応

### 🔍 診断・確認

#### `diagnose_oauth.py`
- OAuth認証問題の詳細診断
- 環境変数、トークン状態、API接続確認
- 問題解決のための詳細レポート生成

#### `verify_setup.py`
- セットアップ完了後の動作確認
- 全機能の統合テスト実行

### 📊 データ取得・レポート

#### `get_real_portal_and_projects.py`
- Zoho Projects Portal・プロジェクト情報取得
- 利用可能なリソース一覧表示

#### `get_project_tasks.py`
- 指定プロジェクトのタスクデータ取得
- MCP経由でのリアルタイムデータ取得

#### `generate_task_report.py`
- プロジェクトタスクのMarkdownレポート生成
- 進捗状況、優先度別サマリー作成

#### `export_project_task_details.py`
- タスクデータの詳細JSONエクスポート
- 外部システム連携用データ出力

### 📁 WorkDrive関連

#### `workdrive_summary.py` ⭐ 推奨
- WorkDrive総合情報表示ツール
- ワークスペース、チーム、ファイル情報を統合表示
- 複数エンドポイントからの包括的情報取得

#### `get_workspace_files.py`
- 軽量版ワークスペースファイル取得ツール
- 特定ワークスペースIDのファイルリスト取得に特化
- シンプルで高速な動作

**使用方法:**
```bash
# デフォルトワークスペースのファイル取得
python tools/get_workspace_files.py

# 特定ワークスペースIDを指定
python tools/get_workspace_files.py <workspace_id>

# 例: 特定のワークスペースID
python tools/get_workspace_files.py hui9647cb257be9684fe294205f6519388d14
```

**機能:**
- 📁 ワークスペースファイル・フォルダリスト表示
- 🎨 カラー付きログ出力
- 📊 ファイル数統計表示
- 🔍 ファイル詳細情報（ID、タイプ、作成日時）

## 🛠️ トラブルシューティング

### よくある問題

1. **認証エラー**
   ```bash
   python tools/diagnose_oauth.py
   ```

2. **セットアップ問題**
   ```bash
   python tools/setup_wizard.py
   ```

3. **WorkDriveアクセス問題**
   ```bash
   python tools/workdrive_summary.py
   ```

### ログレベル
- 🔵 INFO: 一般情報
- 🟢 SUCCESS: 成功
- 🟡 WARNING: 警告
- 🔴 ERROR: エラー
- 🟣 HEADER: セクションヘッダー

## 📝 注意事項

1. **環境要件**: Python 3.9+、必要パッケージインストール済み
2. **認証**: 事前にZoho OAuth認証完了が必要
3. **ネットワーク**: インターネット接続とZoho APIアクセス必要
4. **権限**: 適切なZohoアプリケーション権限設定が必要

## 🎉 整理完了

- ✅ 重複ツール削除済み
- ✅ 機能別分類整理済み  
- ✅ 推奨使用順序明確化
- ✅ 包括的ドキュメント完備
