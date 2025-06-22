# 📚 Zoho MCP Server ガイド集

シンプルで分かりやすいガイドのみを厳選しました。

## 🚀 **セットアップガイド**

### ⭐ **推奨方法**
- **[`zoho_self_client_setup.md`](zoho_self_client_setup.md)** - **Self Client設定ガイド** 
  - 🕐 **10分で完了**
  - 🎯 **最も簡単**
  - ✅ **初心者向け**

### 🔧 **従来方法**
- [`zoho_oauth_setup_guide.md`](zoho_oauth_setup_guide.md) - 従来のOAuth設定ガイド
  - ⚠️ 複雑な手順
  - 🏢 企業向け

## 🆘 **トラブルシューティング**

問題が発生した場合のみ参照してください：

- [`fix_reauth_required.md`](fix_reauth_required.md) - **認証エラー**の解決
- [`fix_400_error_guide.md`](fix_400_error_guide.md) - **400エラー**の修正
- [`zoho_registration_troubleshooting.md`](zoho_registration_troubleshooting.md) - **Zoho登録**時の問題

## 📋 参考情報
- `zoho_correct_scopes.txt` - 正しいZohoスコープ設定
- `zoho_self_client_scopes.txt` - セルフクライアント用スコープ
- `zoho_simple_scope_test.txt` - シンプルなスコープテスト
- `zoho_exact_values.txt` - 正確な設定値
- `manual_portal_id_guide.txt` - ポータルID手動設定ガイド
- `quick_reauth_steps.txt` - 再認証の手順

## 💡 拡張提案
- `user_management_proposal.md` - ユーザー管理機能提案

## ✅ **使用手順**

### 🎯 **新規セットアップ（推奨）**
1. **[`zoho_self_client_setup.md`](zoho_self_client_setup.md)** だけを読む
2. 10分でセットアップ完了
3. 問題があればトラブルシューティングを参照

### 💡 **迷った時は**
- まず **Self Client設定ガイド** を試してください
- うまくいかない場合のみ他のガイドを参照
- 自動セットアップツール: `python tools/setup_wizard.py` 