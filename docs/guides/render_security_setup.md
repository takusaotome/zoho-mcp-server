# Render本番環境セキュリティ設定ガイド

> **⚠️ 重要**: Renderにデプロイする前に必ずこのセキュリティ設定を完了してください

## 🚨 セキュリティリスクについて

Renderにそのままデプロイすると、**誰でもあなたのZohoアカウントにアクセス可能**になってしまいます！
以下の設定で適切にセキュリティを確保しましょう。

## 🛡️ セキュリティ対策一覧

### 1. IP制限の設定（推奨）

#### Option A: 特定IPのみ許可
```bash
# あなたのオフィス・自宅IPを設定
ALLOWED_IPS=203.0.113.1,198.51.100.0/24,::1

# 複数の場所からアクセスする場合
ALLOWED_IPS=203.0.113.1,198.51.100.1,192.0.2.0/24
```

#### Option B: Cloudflareを経由（推奨）
```bash
# Cloudflare IP ranges（DDoS保護付き）
ALLOWED_IPS=173.245.48.0/20,103.21.244.0/22,103.22.200.0/22,103.31.4.0/22,141.101.64.0/18,108.162.192.0/18,190.93.240.0/20,188.114.96.0/20,197.234.240.0/22,198.41.128.0/17,162.158.0.0/15,172.64.0.0/13,131.0.72.0/22,104.16.0.0/13,104.24.0.0/14
```

### 2. JWT認証の強化

#### 強力なJWT_SECRETの設定
```bash
# 128文字の強力なシークレット
python tools/generate_jwt_secret.py --length 128

# Render環境変数に設定
JWT_SECRET=your_super_long_128_character_secret_here
JWT_EXPIRE_HOURS=1  # 短い有効期限（1時間）
```

#### JWTトークンの配布方法
```bash
# 開発チーム用トークン生成
python tools/generate_jwt_token.py --user "team_member_1" --expires-hours 24

# 一時的なアクセス用
python tools/generate_jwt_token.py --user "temp_access" --expires-hours 1
```

### 3. OAuth設定の本番化

#### Zoho API Console設定変更
1. [Zoho API Console](https://api-console.zoho.com)にアクセス
2. あなたのアプリケーションを編集
3. **Authorized Redirect URIs**を更新:
   ```
   https://your-app-name.onrender.com/auth/callback
   ```

#### 環境変数の更新
```bash
# Render環境変数に設定
ZOHO_CLIENT_ID=1000.XXXXXXXXXX
ZOHO_CLIENT_SECRET=your_client_secret
ZOHO_REFRESH_TOKEN=your_refresh_token
ZOHO_PORTAL_ID=your_portal_id

# 本番環境設定
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
```

### 4. 追加セキュリティ設定

#### Rate Limiting（レート制限）
```bash
# 厳しいレート制限
RATE_LIMIT_PER_MINUTE=20  # 1分間に20リクエストまで
```

#### CORS設定
```bash
# 特定のドメインのみ許可
CORS_ORIGINS=https://your-frontend.com,https://your-company.com
CORS_CREDENTIALS=true
```

#### Redis認証
```bash
# Redis認証（Render Redis使用時）
REDIS_URL=rediss://username:password@host:port/db
REDIS_SSL=true
```

## 🔧 Render環境変数設定手順

### 1. Renderダッシュボードで設定

1. **Renderダッシュボード**にアクセス
2. あなたのサービスを選択
3. **Environment**タブをクリック
4. 以下の環境変数を追加:

```bash
# 必須セキュリティ設定
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# IP制限（あなたのIPに変更）
ALLOWED_IPS=your.office.ip.address,your.home.ip.address

# JWT設定（強力なシークレット）
JWT_SECRET=your_128_character_super_secure_secret_here
JWT_EXPIRE_HOURS=1

# Zoho設定
ZOHO_CLIENT_ID=1000.XXXXXXXXXX
ZOHO_CLIENT_SECRET=your_client_secret
ZOHO_REFRESH_TOKEN=your_refresh_token
ZOHO_PORTAL_ID=your_portal_id
TARGET_PROJECT_ID=your_project_id

# Rate Limiting
RATE_LIMIT_PER_MINUTE=20

# CORS（必要な場合のみ）
CORS_ORIGINS=https://your-allowed-domain.com
```

### 2. IPアドレスの確認方法

#### あなたの現在のIPを確認
```bash
# ターミナルで実行
curl ifconfig.me
# または
curl ipinfo.io/ip
```

#### 会社・自宅の固定IPを確認
- インターネットプロバイダーに確認
- 固定IPサービスを利用
- VPN経由でのアクセスを検討

## 🔐 高度なセキュリティ設定

### 1. VPN経由アクセス（最高セキュリティ）

```bash
# VPNサーバーのIPのみ許可
ALLOWED_IPS=vpn.server.ip.address/32

# または企業VPNの範囲
ALLOWED_IPS=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
```

### 2. Basic認証の追加（二重認証）

```python
# server/auth/basic_auth.py に追加実装
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# 環境変数
BASIC_AUTH_USERNAME=your_username
BASIC_AUTH_PASSWORD=your_secure_password
```

### 3. API キー認証の追加

```bash
# 追加のAPI Key認証
API_KEY_HEADER=X-API-Key
API_KEY=your_super_secret_api_key_here
```

## 🚨 緊急時の対応

### アクセス停止方法
1. **Render**: サービスを一時停止
2. **環境変数**: `ALLOWED_IPS=127.0.0.1` に変更（全アクセス拒否）
3. **Zoho**: API Consoleでアプリを無効化

### セキュリティインシデント対応
1. **即座にアクセス停止**
2. **ログの確認** (`/logs` エンドポイント)
3. **Refresh Tokenの再生成**
4. **JWT_SECRETの変更**

## ✅ セキュリティチェックリスト

デプロイ前に以下を確認:

- [ ] IP制限を適切に設定
- [ ] JWT_SECRETを128文字以上に設定
- [ ] 本番環境フラグ（`ENVIRONMENT=production`）
- [ ] デバッグモード無効（`DEBUG=false`）
- [ ] レート制限を厳しく設定
- [ ] OAuth Redirect URIを本番URLに変更
- [ ] ログレベルを`WARNING`以上に設定
- [ ] 不要なCORSオリジンを削除
- [ ] Redis認証を有効化

## 🎯 推奨セキュリティレベル

### Level 1: 基本（最低限）
- IP制限 + JWT認証

### Level 2: 標準（推奨）
- IP制限 + JWT認証 + Rate Limiting + 短い有効期限

### Level 3: 高度（企業用）
- VPN + IP制限 + JWT認証 + Basic認証 + API Key + 監査ログ

---

**⚠️ 重要**: セキュリティ設定なしでの本番デプロイは絶対に避けてください！ 