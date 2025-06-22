# Zoho Developer Console - Server-based Application 登録トラブルシューティング

## 🚨 **よくある失敗原因と解決方法**

### **1. Redirect URI（リダイレクトURI）の問題**

#### ❌ **失敗例**
```
- http://localhost:8000/callback
- https://localhost:8000/auth/callback  
- http://127.0.0.1:8000/auth/callback
- http://0.0.0.0:8000/auth/callback
```

#### ✅ **正しい設定**
```
http://localhost:8000/auth/callback
```

**重要**: 必ず `http://` で始める（httpsではない）

### **2. Homepage URL の問題**

#### ❌ **失敗例**
```
- localhost:8000
- https://localhost:8000
- 空欄
```

#### ✅ **正しい設定**
```
http://localhost:8000
```

### **3. Client Name の問題**

#### ❌ **失敗例**
```
- 空欄
- 特殊文字を含む名前（@, #, % など）
- 既存のアプリと同じ名前
```

#### ✅ **正しい設定**
```
Zoho MCP Server
または
My Zoho Integration App
```

### **4. アカウント権限の問題**

#### 症状
- 「アクセス権限がありません」エラー
- 「Developer Console にアクセスできません」

#### 解決方法
1. Zoho管理者権限があるアカウントでログイン
2. または、組織管理者に権限付与を依頼

## 🔧 **段階的な登録手順**

### **Step 1: 事前準備**
1. [Zoho Developer Console](https://api-console.zoho.com/) にアクセス
2. 正しいZohoアカウントでログイン確認
3. ブラウザのキャッシュをクリア（必要に応じて）

### **Step 2: アプリケーション作成**
1. **"Server-based Applications"** を選択
2. 以下の情報を**正確に**入力：

| 項目 | 値 | 
|------|-----|
| **Client Name** | `Zoho MCP Server` |
| **Client Domain** | `localhost` |
| **Homepage URL** | `http://localhost:8000` |
| **Authorized Redirect URIs** | `http://localhost:8000/auth/callback` |

### **Step 3: スコープ設定**
以下のスコープを選択：
```
✅ ZohoProjects.projects.READ
✅ ZohoProjects.tasks.ALL
✅ ZohoProjects.files.READ
✅ ZohoWorkDrive.files.ALL
✅ ZohoWorkDrive.files.READ
```

## 🐛 **具体的なエラーと解決方法**

### **エラー: "Invalid Redirect URI"**
**原因**: リダイレクトURIの形式が間違っている
**解決**: `http://localhost:8000/auth/callback` を使用

### **エラー: "Domain not allowed"**
**原因**: ドメイン設定が間違っている
**解決**: Client Domain に `localhost` を設定

### **エラー: "Application name already exists"**
**原因**: 同じ名前のアプリが既に存在
**解決**: 別の名前を使用（例：`Zoho MCP Server v2`）

### **エラー: "Access denied"**
**原因**: アカウント権限不足
**解決**: 
1. 組織管理者アカウントでログイン
2. または権限付与を依頼

## 🔄 **代替アプローチ**

### **方法1: Self Client を使用**
Developer Consoleで "Self Client" オプションがある場合：
1. 既存のクライアントを使用
2. 追加の認証設定は不要

### **方法2: 異なるアプリケーションタイプ**
Server-basedで失敗する場合：
1. **"Client-based Applications"** を試す
2. 設定は同じだが、若干異なる認証フロー

### **方法3: 段階的登録**
1. 最小限のスコープで登録
2. 動作確認後にスコープを追加

## 🛠️ **登録成功後の確認**

登録が成功すると以下が表示されます：
```
Client ID: 1000.XXXXXXXXXX
Client Secret: xxxxxxxxxxxxxxxx
```

**これらの値を必ず保存してください。**

## 💡 **追加のヒント**

### **ブラウザ関連**
- シークレットモードを試す
- 別のブラウザを使用
- JavaScriptを有効にする

### **ネットワーク関連**
- VPN接続を切断
- 会社のファイアウォール確認
- 異なるネットワークから試す

### **アカウント関連**
- 個人アカウントと組織アカウントの違いを確認
- 無料プランでも基本的な開発は可能 