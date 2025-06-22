# Zoho MCP Server ガイド集

このディレクトリには設定ガイドやトラブルシューティング情報が含まれています。

## 🚀 セットアップガイド

### 推奨方法
- **⭐ `zoho_self_client_setup.md`** - **Self Client設定ガイド** (簡単・高速)

### 従来方法
- `zoho_oauth_setup_guide.md` - Zoho OAuth設定ガイド (複雑)
- `zoho_scope_setup_guide.md` - Zoho スコープ設定ガイド
- `zoho_scope_location_guide.md` - Zoho スコープ場所ガイド

## 🔧 トラブルシューティング
- `fix_reauth_required.md` - 認証エラー解決
- `fix_400_error_guide.md` - 400エラー修正ガイド
- `zoho_registration_troubleshooting.md` - Zoho登録時のトラブルシューティング

## 📋 参考情報
- `zoho_correct_scopes.txt` - 正しいZohoスコープ設定
- `zoho_self_client_scopes.txt` - セルフクライアント用スコープ
- `zoho_simple_scope_test.txt` - シンプルなスコープテスト
- `zoho_exact_values.txt` - 正確な設定値
- `manual_portal_id_guide.txt` - ポータルID手動設定ガイド
- `quick_reauth_steps.txt` - 再認証の手順

## 💡 拡張提案
- `user_management_proposal.md` - ユーザー管理機能提案

## ✅ 使用手順

### 新規セットアップ (推奨)
1. **`zoho_self_client_setup.md`** を最初に読んでください
2. Self Client方式で10分程度でセットアップ完了
3. 問題があればトラブルシューティングガイドを参照

### 従来方式
1. `zoho_oauth_setup_guide.md` で詳細な手順を確認
2. スコープ設定ガイドで権限を正しく設定
3. 各種参考ファイルで設定値を確認 