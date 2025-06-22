#!/usr/bin/env python3
"""
Zoho OAuth認証URL生成ツール
REFRESH_TOKEN取得の第一段階
"""

import urllib.parse
import webbrowser
from pathlib import Path

def load_env_config():
    """現在の.env設定を読み込み"""
    env_config = {}
    env_file = Path(".env")
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_config[key.strip()] = value.strip()
    
    return env_config

def generate_auth_url(client_id, redirect_uri=None):
    """OAuth認証URLを生成"""
    if not redirect_uri:
        redirect_uri = "http://localhost:8000/auth/callback"
    
    # 必要なスコープ
    scopes = [
        "ZohoProjects.projects.READ",
        "ZohoProjects.tasks.ALL", 
        "ZohoProjects.files.READ",
        "ZohoWorkDrive.files.ALL",
        "ZohoWorkDrive.files.READ"
    ]
    
    # OAuth認証URLのパラメータ
    params = {
        "scope": ",".join(scopes),
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "access_type": "offline",  # リフレッシュトークンを取得するために必要
        "prompt": "consent"  # 毎回同意画面を表示
    }
    
    base_url = "https://accounts.zoho.com/oauth/v2/auth"
    query_string = urllib.parse.urlencode(params)
    auth_url = f"{base_url}?{query_string}"
    
    return auth_url

def main():
    """メイン処理"""
    print("🔐 Zoho OAuth認証URL生成ツール")
    print("=" * 50)
    
    # 現在の.env設定を確認
    env_config = load_env_config()
    client_id = env_config.get("ZOHO_CLIENT_ID")
    
    if not client_id:
        print("❌ ZOHO_CLIENT_IDが.envファイルに設定されていません")
        print()
        print("📋 手順:")
        print("1. Zoho Developer Console でアプリを作成")
        print("2. Client ID を .env ファイルに設定")
        print("3. このスクリプトを再実行")
        return
    
    if client_id.startswith("1000."):
        print(f"✅ Client ID: {client_id[:20]}...")
    else:
        print("⚠️  Client IDの形式が正しくない可能性があります")
        print(f"   現在の値: {client_id}")
        print("   正しい形式: 1000.XXXXXXXXXX")
    
    print()
    print("🌐 OAuth認証URL生成中...")
    
    # 認証URL生成
    auth_url = generate_auth_url(client_id)
    
    print()
    print("✅ 認証URL生成完了!")
    print("=" * 50)
    print()
    print("📝 次の手順:")
    print("1. 以下のURLをブラウザで開く")
    print("2. Zohoアカウントでログイン")
    print("3. アプリへのアクセス権限を承認")
    print("4. リダイレクト後のURLから code= の値をコピー")
    print()
    print("🔗 認証URL:")
    print("-" * 30)
    print(auth_url)
    print()
    
    # 自動でブラウザを開くか確認
    try:
        response = input("ブラウザを自動で開きますか？ (y/n): ").strip().lower()
        if response in ['y', 'yes', 'はい']:
            webbrowser.open(auth_url)
            print("✅ ブラウザで認証ページを開きました")
        else:
            print("💡 上記URLを手動でブラウザにコピーしてください")
    except (KeyboardInterrupt, EOFError):
        print("\n💡 上記URLを手動でブラウザにコピーしてください")
    
    print()
    print("⚠️  重要な注意事項:")
    print("- 認証コードは10分間で期限切れになります")
    print("- 認証完了後は exchange_auth_code.py を実行してください")
    print("- エラーが発生した場合は、スコープ設定を確認してください")

if __name__ == "__main__":
    main() 