# Reports Directory

このディレクトリには**プロジェクトデータとレポート**が含まれています。

## 📁 フォルダ構成

```
reports/
├── exports/    # プロジェクトデータ（JSON、レポート）
├── configs/    # 設定ファイル
└── README.md   # このファイル
```

## 📄 ファイル形式

### プロジェクトデータ（exports/）
- `*_tasks_*.json` - プロジェクトタスクデータ（JSON形式）
- `*_report_*.md` - プロジェクトタスクレポート（Markdown形式）
- `zoho_projects_list.json` - Zoho Projects の一覧データ

### 設定ファイル（configs/）
- 機密情報を含む設定ファイル
- 認証情報やAPIキーなど

## 📊 レポート形式

### タスクレポート（Markdown）
- プロジェクト概要
- 統計情報（ステータス別、担当者別、優先度別）
- 詳細タスク一覧
- 主要タスクの詳細情報

### タスクデータ（JSON）
- 生のAPIレスポンスデータ
- 詳細なタスク情報とメタデータ

## 🔒 セキュリティ

- **重要**: このディレクトリは`.gitignore`で除外されています
- プロジェクトデータには機密情報が含まれる可能性があります
- 外部共有時は十分に注意してください
- ファイル名にはタイムスタンプが含まれています

## 🛠️ ツール連携

このディレクトリは以下のツールで使用されます：
- `tools/get_project_tasks.py` - データ取得・保存
- `tools/generate_task_report.py` - レポート生成
- `tools/export_project_task_details.py` - データエクスポート

## 📋 使用方法

ツールスクリプトを実行する際、環境変数で実際のプロジェクトIDを指定してください：

```bash
export TARGET_PROJECT_ID="実際のプロジェクトID"
export OUTPUT_DIR="reports/exports"
python tools/get_project_tasks.py
```

## ⚠️ 注意事項

- このフォルダ内のファイルは絶対に外部共有しないでください
- バックアップ時も機密情報の取り扱いに注意してください
- 作業完了後は必要に応じてファイルを削除してください 
