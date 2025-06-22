# Zoho Self Client設定ガイド - 簡単なRefresh Token取得方法

## 📋 概要

Zoho API Console の **Self Client** 機能を使用することで、従来の複雑な認証フローを経ずに、簡単にRefresh Tokenを取得できます。

## ✨ Self Clientの利点

- ✅ **簡単**: 複雑なOAuth フローが不要
- ✅ **迅速**: 最大10分でコード生成完了
- ✅ **安全**: アプリケーション作成なしで直接アクセス

## 🚀 手順

### Step 1: Zoho API Console にアクセス

1. [Zoho API Console](https://api-console.zoho.com/) にアクセス
2. Zohoアカウントでログイン

### Step 2: Self Client を選択

1. 「**Self Client**」オプションを選択
2. 「**Generate Code**」をクリック

### Step 3: スコープを設定

以下のスコープを選択してください：

```
✅ ZohoProjects.projects.READ
✅ ZohoProjects.tasks.ALL  
✅ ZohoProjects.files.READ
✅ ZohoWorkDrive.files.ALL
✅ ZohoWorkDrive.files.READ
```

### Step 4: Time Duration設定

- **Time Duration**: `10 minutes` を選択
- **Scope Description**: 任意（プロジェクト名など）

### Step 5: コード生成とRefresh Token取得

1. 「**CREATE**」ボタンをクリック
2. 生成された**認証コード**をコピー
3. 以下のコマンドでRefresh Tokenに変換：

```bash
python tools/exchange_auth_code.py [認証コード]
```

## 📝 例

### 生成される認証コード形式
```
1000.abcd1234efgh5678ijkl9012mnop3456.qrst7890uvwx1234yzab5678cdef9012
```

### 変換コマンド例
```bash
python tools/exchange_auth_code.py 1000.abcd1234efgh5678ijkl9012mnop3456.qrst7890uvwx1234yzab5678cdef9012
```

### 成功時の出力
```
✅ トークン交換成功!
🔑 Access Token: 1000.xxxxxxxx...
🔄 Refresh Token: 1000.yyyyyyyy...
💾 .envファイル更新完了!
```

## ⚠️ 重要な注意事項

### セキュリティ
- **認証コードは10分で期限切れ** - 生成後すぐに使用してください
- **Refresh Tokenは安全に保管** - `.env`ファイルは`.gitignore`で除外されています
- **スコープは必要最小限** - 上記のスコープのみを選択してください

### トラブルシューティング
- **コード期限切れ**: 新しいコードを再生成してください
- **スコープエラー**: 必要なスコープが選択されているか確認してください
- **API制限**: しばらく待ってから再試行してください

## 🔧 設定確認

### .envファイル確認
```bash
python tools/check_configuration.py
```

### 接続テスト
```bash
python tools/final_verification.py
```

## 📚 関連ドキュメント

- [従来のOAuth設定ガイド](zoho_oauth_setup_guide.md) (複雑な手順)
- [スコープ設定ガイド](zoho_scope_setup_guide.md)
- [トラブルシューティング](zoho_registration_troubleshooting.md)

## ❓ よくある質問

**Q: Self ClientとServer-based Applicationの違いは？**
A: Self Clientは個人開発向けで設定が簡単、Server-basedは本格的なアプリケーション向けです。

**Q: Refresh Tokenの有効期限は？**
A: 通常は無期限ですが、長期間未使用の場合は無効になることがあります。

**Q: 複数のプロジェクトで使用できますか？**
A: はい、同じRefresh Tokenで複数のZohoプロジェクトにアクセス可能です。 