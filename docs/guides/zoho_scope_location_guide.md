# Zoho Developer Console - スコープ設定ガイド

## 🔍 **スコープ設定の場所**

### **現在の状況**
- ✅ アプリケーション「Mcp Server Saotome」作成済み
- ❓ スコープ設定がまだ完了していない
- 📍 Settings タブには Multi-DC 設定のみ表示

## 🚀 **スコープ設定の手順**

### **方法1: Scope設定タブを探す**

#### **Step 1: すべてのタブを確認**
現在表示されているタブ：
- Client Details ✅
- Client Secret ✅  
- Settings ✅

**他にタブがないか確認してください：**
- **Scope** タブ
- **API Access** タブ
- **Permissions** タブ
- **Services** タブ

#### **Step 2: 左側メニューを確認**
左側の「Applications」セクションで：
1. 「Mcp Server Saotome」をクリック
2. 新しいメニューが表示されるか確認

### **方法2: スコープを追加設定**

#### **2.1 Client Details タブから**
1. **Client Details** タブに戻る
2. ページの下部にスクロール
3. **「Add Scope」**ボタンを探す

#### **2.2 新しいスコープ追加**
もし「Add Scope」ボタンがある場合：

**必要なスコープ一覧：**
```
✅ ZohoProjects.projects.READ
✅ ZohoProjects.tasks.ALL
✅ ZohoProjects.files.READ
✅ ZohoWorkDrive.files.ALL
✅ ZohoWorkDrive.files.READ
```

### **方法3: 既存アプリの確認**

#### **3.1 Self Clientを使用**
左側に「Self Client」が表示されています：
1. **Self Client** をクリック
2. こちらでスコープ設定ができるか確認

#### **3.2 Self Clientの利点**
- 設定が簡単
- 即座に使用可能
- 開発/テスト用途に最適

## 🔧 **具体的な確認手順**

### **Step 1: Client Secretタブを確認**
1. **「Client Secret」タブ**をクリック
2. Client ID と Client Secret を確認
3. スコープ関連の設定があるかチェック

### **Step 2: ページ全体をスクロール**
各タブで：
- ページを最下部までスクロール
- 隠れているセクションがないか確認

### **Step 3: アプリケーション再編集**
1. アプリケーションリストに戻る
2. 「Mcp Server Saotome」の**編集ボタン**（鉛筆アイコン）をクリック
3. 編集画面でスコープ設定を探す

## 🎯 **期待する画面**

スコープ設定が見つかると、以下のような画面が表示されます：

```
Scope Configuration
├── ZohoProjects
│   ├── ☐ ZohoProjects.projects.READ
│   ├── ☐ ZohoProjects.tasks.ALL
│   └── ☐ ZohoProjects.files.READ
└── ZohoWorkDrive  
    ├── ☐ ZohoWorkDrive.files.ALL
    └── ☐ ZohoWorkDrive.files.READ
```

## 🔄 **代替アプローチ**

### **Self Clientを使用する場合**
1. **Self Client** をクリック
2. 設定を確認
3. こちらの方が設定が簡単な場合が多い

### **新しいアプリを作成する場合**
1. 「Create Application」で新規作成
2. 作成プロセスでスコープを設定
3. より確実にスコープが設定される

## 💡 **次のステップ**

1. **まず**: 上記の場所でスコープ設定を探す
2. **見つからない場合**: Self Client を確認
3. **それでも不明**: 新しいアプリケーション作成を検討 