# Zoho OAuth設定ガイド - REFRESH_TOKEN取得方法

## 📋 **前提条件**
- Zohoアカウント（無料でも可）
- Zoho Projects または WorkDrive へのアクセス権限

## 🚀 **Step 1: Zoho Developer Console でアプリ作成**

### 1.1 アプリケーション作成
1. [Zoho Developer Console](https://api-console.zoho.com/) にアクセス
2. **"Server-based Applications"** を選択 ✅
   - これがMCP Serverに最適な選択
3. アプリケーション情報を入力：
   - **Client Name**: `Zoho MCP Server`（任意の名前）
   - **Homepage URL**: `http://localhost:8000`
   - **Authorized Redirect URIs**: `http://localhost:8000/auth/callback`

### 1.2 必要なスコープ設定
以下のスコープを選択：
```
✅ ZohoProjects.projects.READ
✅ ZohoProjects.tasks.ALL
✅ ZohoProjects.files.READ
✅ ZohoWorkDrive.files.ALL
✅ ZohoWorkDrive.files.READ
```

### 1.3 Client ID と Client Secret を保存
アプリ作成後に表示される値をメモ：
- **Client ID**: `1000.XXXXXXXXXX`
- **Client Secret**: `xxxxxxxxxxxxxxxx`

## 🔐 **Step 2: REFRESH_TOKEN 取得**

### 2.1 認証URL生成（自動化スクリプト）
```bash
python generate_zoho_auth_url.py
```

### 2.2 手動での認証フロー
1. 生成されたURLをブラウザで開く
2. Zohoアカウントでログイン
3. アプリのアクセス権限を承認
4. リダイレクトされたURLから `code=` パラメータを取得

### 2.3 認証コードをトークンに交換
**方法A: 自動認証（推奨）**
```bash
python tools/generate_zoho_auth_url.py
# オプション1を選択してブラウザで認証完了
```

**方法B: 手動設定**
- 取得した認証コードを`.env`ファイルの`ZOHO_REFRESH_TOKEN=`に直接設定

## 📝 **Step 3: .env ファイル更新**
取得した値を .env ファイルに設定：
```env
ZOHO_CLIENT_ID=1000.XXXXXXXXXX
ZOHO_CLIENT_SECRET=xxxxxxxxxxxxxxxx
ZOHO_REFRESH_TOKEN=1000.YYYYYYYYYY.ZZZZZZZZ
PORTAL_ID=your_portal_id_from_zoho_projects
```

## 🎯 **Portal ID の取得方法**
1. [Zoho Projects](https://projects.zoho.com/) にアクセス
2. 任意のプロジェクトを開く
3. URLから Portal ID を確認：
   ```
   https://projects.zoho.com/portal/[PORTAL_ID]/projects/[PROJECT_ID]
                                   ↑ここがPortal ID
   ```

## ⚠️ **注意事項**
- Refresh Tokenは長期間有効（通常無期限）
- Client SecretとRefresh Tokenは安全に保管
- 開発用と本番用で別々のアプリを作成推奨

## 🔧 **トラブルシューティング**
- **invalid_client**: Client IDまたはClient Secretが間違い
- **access_denied**: スコープが不足またはユーザーが拒否
- **invalid_grant**: 認証コードが期限切れ（10分間有効） 