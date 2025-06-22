# Zoho Developer Console 400 エラー解決ガイド

## 🚨 **HTTP 400 Bad Request エラーの原因と解決**

### **最も一般的な原因**

#### **1. Redirect URI の形式問題**
❌ **間違った形式**
```
- https://localhost:8000/auth/callback  (httpsは不可)
- http://localhost:8000/callback        (pathが違う)  
- http://127.0.0.1:8000/auth/callback   (127.0.0.1は不可)
- localhost:8000/auth/callback          (スキーマ不足)
```

✅ **正しい形式**
```
http://localhost:8000/auth/callback
```

#### **2. 必須フィールドの不備**
以下のフィールドは**必須**です：
- Client Name: 空欄不可
- Homepage URL: 正しいURL形式
- Redirect URI: 正しいURL形式

#### **3. URL形式の詳細ルール**
- **プロトコル**: 必ず `http://` で開始
- **ポート**: `:8000` を明示的に指定
- **パス**: `/auth/callback` を正確に入力
- **特殊文字**: スペースや日本語は使用不可

## 🔧 **段階的な修正手順**

### **Step 1: ブラウザをリフレッシュ**
1. ページを完全にリロード (Ctrl+F5 / Cmd+Shift+R)
2. ブラウザの開発者ツールでエラー詳細を確認
3. キャッシュをクリア

### **Step 2: 入力値を確認**
以下の値を**正確に**コピー&ペーストしてください：

| 項目 | 正確な値 |
|------|----------|
| **Client Name** | `ZohoMCPServer` |
| **Client Domain** | `localhost` |
| **Homepage URL** | `http://localhost:8000` |
| **Authorized Redirect URIs** | `http://localhost:8000/auth/callback` |

### **Step 3: 1つずつフィールドを入力**
1. Client Name を入力
2. Homepage URL を入力・検証
3. Redirect URI を入力・検証
4. 各フィールドでエラーが出ないことを確認

## 🐛 **具体的なエラーパターンと対処**

### **パターン1: "Invalid URL format"**
```
原因: URLの形式が間違っている
対処: http:// で始まることを確認
```

### **パターン2: "Domain not allowed"**
```
原因: localhostが許可されていない
対処: Client Domain に "localhost" を設定
```

### **パターン3: "Redirect URI mismatch"**
```
原因: パスの不一致
対処: 正確に "/auth/callback" を使用
```

## 🔄 **代替解決方法**

### **方法1: 最小設定で作成**
```
Client Name: TestApp
Homepage URL: http://localhost:8000
Redirect URI: http://localhost:8000/auth/callback
```

### **方法2: 異なるポート番号**
```
Homepage URL: http://localhost:3000
Redirect URI: http://localhost:3000/auth/callback
```
※ サーバー起動時のポートも変更する必要があります

### **方法3: Self Clientを使用**
Developer Consoleで "Self Client" が表示される場合：
1. 既存のクライアントを使用
2. 新規作成は不要

## 🛠️ **ブラウザ別対処法**

### **Chrome**
1. デベロッパーツール (F12)
2. Network タブでリクエスト詳細を確認
3. Response で具体的なエラー内容を確認

### **Firefox**  
1. ウェブ開発ツール (F12)
2. ネットワークタブで400エラーの詳細を確認

### **Safari**
1. 開発メニューを有効化
2. ウェブインスペクタでネットワーク分析

## 📝 **エラー時のチェックリスト**

- [ ] URLに余分なスペースが含まれていない
- [ ] httpとhttpsを間違えていない  
- [ ] ポート番号(:8000)が含まれている
- [ ] パス(/auth/callback)が正確
- [ ] 特殊文字を使用していない
- [ ] 必須フィールドがすべて入力済み
- [ ] ブラウザのJavaScriptが有効
- [ ] ネットワーク接続が安定している

## 💡 **最終手段**

### **完全リセット**
1. ブラウザを完全に閉じる
2. キャッシュとCookieをクリア
3. 別のブラウザで試す
4. シークレット/プライベートモードを使用

### **Zohoサポートに連絡**
上記の方法で解決しない場合：
1. エラーのスクリーンショット
2. 入力した値の詳細
3. ブラウザとOSの情報
を添えてサポートに連絡 