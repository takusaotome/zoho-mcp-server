#!/usr/bin/env python3
"""
テスト用JWTトークン生成ツール
設定確認やデバッグ用にJWTトークンを生成する
"""

import sys
import os
from datetime import datetime, timedelta

# プロジェクトルートを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.auth.jwt_handler import JWTHandler
from server.core.config import settings


def generate_test_token():
    """テスト用のJWTトークンを生成"""
    try:
        # JWT ハンドラーを初期化
        jwt_handler = JWTHandler()
        
        # テストユーザー情報
        test_subject = "test_user"
        
        # トークンを生成（デフォルトの有効期限を使用）
        token = jwt_handler.create_token(subject=test_subject)
        
        print("🔑 テスト用JWTトークンを生成しました")
        print("=" * 50)
        print(f"Subject: {test_subject}")
        print(f"Expires: {datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)}")
        print(f"Algorithm: {settings.jwt_algorithm}")
        print()
        print("JWT Token:")
        print(token)
        print()
        print("💡 このトークンをAuthorizationヘッダーで使用:")
        print(f"Authorization: Bearer {token}")
        
        return token
        
    except Exception as e:
        print(f"❌ トークン生成エラー: {e}")
        print()
        print("💡 考えられる原因:")
        print("  - JWT_SECRETが設定されていない")
        print("  - 設定ファイル (.env) が不正")
        print("  - 依存関係のインストール不備")
        return None


def verify_test_token(token: str):
    """生成したトークンを検証"""
    try:
        jwt_handler = JWTHandler()
        payload = jwt_handler.verify_token(token)
        
        print("✅ トークン検証成功")
        print(f"Subject: {payload.get('sub')}")
        print(f"Issued At: {datetime.fromtimestamp(payload.get('iat', 0))}")
        print(f"Expires At: {datetime.fromtimestamp(payload.get('exp', 0))}")
        
        return True
        
    except Exception as e:
        print(f"❌ トークン検証エラー: {e}")
        return False


def main():
    """メイン処理"""
    # 環境設定確認
    if not settings.jwt_secret:
        print("❌ JWT_SECRET が設定されていません")
        print("💡 .env ファイルに JWT_SECRET を設定してください")
        print("   例: JWT_SECRET=your-secret-key-32-chars-long")
        sys.exit(1)
    
    # トークン生成
    token = generate_test_token()
    
    if token:
        print()
        print("🔍 生成したトークンを検証中...")
        print("-" * 30)
        verify_test_token(token)
        
        # 使用例も表示
        print()
        print("📋 使用例:")
        print("-" * 20)
        print("curl -H 'Authorization: Bearer " + token + "' \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"jsonrpc\":\"2.0\",\"method\":\"listTools\",\"id\":1}' \\")
        print("     http://localhost:8000/mcp")


if __name__ == "__main__":
    main()