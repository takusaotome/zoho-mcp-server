# Zoho Developer Console - スコープ設定ガイド

## 🎯 **スコープ設定の場所と手順**

### **現在の状況**
✅ アプリケーション「Mcp Server Saotome」作成完了
✅ Client Details設定完了
🔄 **次のステップ**: スコープ設定

## 📋 **Step 1: Settings タブに移動**

現在のスクリーンショットで：
1. **「Settings」タブ**をクリック
2. スコープ設定セクションを探す

## 🔍 **Step 2: スコープ設定を見つける**

Settingsタブ内で以下のセクションを探してください：
- **「Scope」**
- **「API Permissions」** 
- **「Service Permissions」**
- **「OAuth Scopes」**

## ✅ **Step 3: 必要なスコープを選択**

以下のスコープを**すべて**選択してください：

### **Zoho Projects 関連**
```
✅ ZohoProjects.projects.READ
✅ ZohoProjects.tasks.ALL
✅ ZohoProjects.files.READ
✅ ZohoProjects.milestones.READ
✅ ZohoProjects.timesheets.READ
```

### **Zoho WorkDrive 関連**
```
✅ ZohoWorkDrive.files.ALL
✅ ZohoWorkDrive.files.READ
✅ ZohoWorkDrive.files.CREATE
✅ ZohoWorkDrive.workspace.READ
```

### **基本スコープ**
```
✅ AaaServer.profile.READ
✅ ZohoProjects.portals.READ
```

## 🔄 **別の設定場所の可能性**

### **方法1: アプリケーション編集**
1. 左側の「Applications」リストで「Mcp Server Saotome」をクリック
2. **「Edit」**または**「Configure」**ボタンを探す
3. スコープ設定画面に移動

### **方法2: Scope設定の専用ページ**
1. Developer Console のメインメニューで**「Scopes」**を探す
2. アプリケーション別のスコープ管理画面にアクセス

### **方法3: Client Secret タブの確認**
1. **「Client Secret」タブ**をクリック
2. スコープ設定がそこにある場合もあります

## 📝 **スコープ設定が見つからない場合**

### **代替手順A: アプリケーション再作成**
1. より詳細な設定オプションで再作成
2. 作成時にスコープを選択

### **代替手順B: API コンソールの別セクション**
1. メインナビゲーションで**「Services」**を確認
2. **「Permissions」**セクションを確認

## 🎯 **設定完了の確認**

スコープ設定後、以下を確認：
```
✅ 設定したスコープが一覧に表示される
✅ 「Save」または「Update」ボタンをクリック済み
✅ 成功メッセージが表示される
```

## 💡 **重要な注意事項**

### **スコープの重要性**
- スコープが設定されていないとAPI呼び出しが失敗
- 後からスコープを追加/変更可能
- 最小限の権限から始めて段階的に追加推奨

### **アクセス権限**
- 組織アカウントの場合、管理者承認が必要な場合がある
- 一部のスコープは有料プランでのみ利用可能

## 🆘 **トラブルシューティング**

### **スコープ設定が見つからない**
1. ブラウザを更新
2. 別のブラウザを試す
3. アプリケーションタイプを確認（Server-based vs Client-based）

### **権限エラー**
1. アカウントの管理者権限を確認
2. 組織管理者に権限付与を依頼
3. 個人アカウントでの作成を検討 