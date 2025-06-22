# Config Directory

このディレクトリには設定ファイルが含まれています。

## ファイル一覧

- `env.example` - 環境変数設定のテンプレート
- `cursor-mcp-config.example.json` - Cursor MCP設定のテンプレート
- `alternative_port_config.txt` - 代替ポート設定

## ⚠️ セキュリティ強化済み

以下のファイルはシークレット情報を含むため `.gitignore` に追加されています：

- `cursor-mcp-config.json` - 本物の設定（実際のAPIキーを含む）
- `temp_jwt.env` - 一時的なJWT設定
- その他の `*secret*.env` ファイル

## 設定方法

### 1. 環境変数の設定
```bash
# .envファイルを作成
cp config/env.example .env
# .envファイルを編集して実際の値を設定
```

### 2. Cursor MCP設定
```bash
# テンプレートをコピー
cp config/cursor-mcp-config.example.json config/cursor-mcp-config.json
# 実際の値を設定（このファイルはGitで追跡されません）
```

## 🔒 セキュリティ注意事項

- **絶対にシークレット情報をハードコードしないでください**
- 実際の環境変数ファイル（`.env`）は絶対にリポジトリにコミットしないでください
- JWT トークンやAPIキーなどの機密情報は適切に管理してください
- 本番環境では環境変数やシークレット管理サービスを使用してください 