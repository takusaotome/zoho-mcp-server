#!/usr/bin/env python3
"""
Zoho MCP Server設定確認ツール
現在の設定状況と問題点を診断する
"""

import os
import sys
from pathlib import Path

def main():
    """設定確認のメイン関数"""
    print("🔍 Zoho MCP Server 設定診断")
    print("=" * 50)
    
    # 1. .envファイルの存在確認
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .envファイル: 存在")
        
        # .envファイルの内容を読み込み
        env_vars = {}
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            print(f"❌ .envファイル読み込みエラー: {e}")
            return
    else:
        print("❌ .envファイル: 見つかりません")
        return
    
    print("\n📋 設定項目チェック:")
    print("-" * 30)
    
    # 2. 必須設定項目の確認
    required_settings = {
        "ZOHO_CLIENT_ID": "Zoho OAuth Client ID",
        "ZOHO_CLIENT_SECRET": "Zoho OAuth Client Secret", 
        "ZOHO_REFRESH_TOKEN": "Zoho Refresh Token",
        "ZOHO_PORTAL_ID": "Zoho Portal ID",
        "JWT_SECRET": "JWT秘密鍵",
        "REDIS_URL": "Redis接続URL"
    }
    
    issues = []
    
    for key, description in required_settings.items():
        value = env_vars.get(key, "")
        
        if not value:
            print(f"❌ {key}: 未設定")
            issues.append(f"{key}が未設定")
        elif value.startswith("your_") or value.startswith("placeholder_"):
            print(f"⚠️  {key}: デフォルト値（要設定）")
            issues.append(f"{key}がデフォルト値のまま")
        else:
            # 設定値の長さチェック
            if key == "JWT_SECRET" and len(value) < 32:
                print(f"⚠️  {key}: 設定済み（セキュリティ警告: 32文字未満）")
                issues.append(f"{key}が短すぎる（32文字以上推奨）")
            else:
                masked_value = value[:8] + "..." if len(value) > 8 else value
                print(f"✅ {key}: 設定済み ({masked_value})")
    
    # 3. オプション設定の確認
    print(f"\n📊 オプション設定:")
    print("-" * 30)
    
    optional_settings = {
        "ENVIRONMENT": ("development", "環境設定"),
        "DEBUG": ("true", "デバッグモード"),
        "LOG_LEVEL": ("INFO", "ログレベル"),
        "RATE_LIMIT_PER_MINUTE": ("100", "レート制限")
    }
    
    for key, (default_val, description) in optional_settings.items():
        value = env_vars.get(key, default_val)
        print(f"📌 {key}: {value} ({description})")
    
    # 4. Redis設定の確認
    print(f"\n🔄 Redis設定:")
    print("-" * 30)
    redis_url = env_vars.get("REDIS_URL", "redis://localhost:6379/0")
    redis_ssl = env_vars.get("REDIS_SSL", "false")
    print(f"📌 REDIS_URL: {redis_url}")
    print(f"📌 REDIS_SSL: {redis_ssl}")
    
    if redis_ssl.lower() == "true":
        print("⚠️  SSL有効 - ローカル開発では通常false")
    
    # 5. 問題の要約
    print(f"\n🎯 診断結果:")
    print("=" * 50)
    
    if not issues:
        print("✅ 基本設定は完了しています")
        print("💡 次のステップ: サーバーを再起動してテスト")
    else:
        print("❌ 以下の問題を修正してください:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    
    # 6. 修正手順の提示
    print(f"\n📝 修正方法:")
    print("-" * 30)
    print("1. .envファイルを編集:")
    print("   nano .env  または  code .env")
    print()
    
    if "ZOHO_REFRESH_TOKEN" in [issue.split("が")[0] for issue in issues]:
        print("2. Zoho OAuth設定が必要な場合:")
        print("   - Zoho Developer Console でアプリ作成")
        print("   - OAuth スコープ設定:")
        print("     * ZohoProjects.tasks.ALL")
        print("     * ZohoProjects.files.READ")
        print("     * ZohoWorkDrive.files.ALL")
        print("   - リフレッシュトークン取得")
        print()
    
    print("3. 設定完了後:")
    print("   - サーバー再起動: uvicorn server.main:app --reload")
    print("   - テスト実行: python test_zoho_mock.py")

if __name__ == "__main__":
    main() 