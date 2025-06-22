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
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_config[key.strip()] = value.strip()

    return env_config

def generate_auth_url(client_id, redirect_uri=None):
    """OAuth認証URLを生成"""
    if not redirect_uri:
        # Self Client方式の場合は urn:ietf:wg:oauth:2.0:oob を使用
        redirect_uri = "urn:ietf:wg:oauth:2.0:oob"

    # 必要なスコープ（正しい形式）
    scopes = [
        "ZohoProjects.projects.read",
        "ZohoProjects.tasks.all",
        "WorkDrive.files.READ",
        "WorkDrive.files.CREATE"
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
    redirect_uri = env_config.get("ZOHO_REDIRECT_URI")

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

    # Redirect URIの選択
    if not redirect_uri:
        print("🔗 Redirect URIを選択してください:")
        print("1. http://localhost:8000/auth/callback (推奨・自動設定)")
        print("2. urn:ietf:wg:oauth:2.0:oob (Self Client標準)")
        print("3. https://accounts.zoho.com/oauth/callback (Zoho標準)")
        print("4. カスタムURIを入力")
        print()

        try:
            choice = input("選択 (1-4): ").strip()
            if choice == "1":
                redirect_uri = "http://localhost:8000/auth/callback"
            elif choice == "2":
                redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
            elif choice == "3":
                redirect_uri = "https://accounts.zoho.com/oauth/callback"
            elif choice == "4":
                redirect_uri = input("Redirect URIを入力してください: ").strip()
                if not redirect_uri:
                    print("❌ Redirect URIが入力されませんでした")
                    return
            else:
                print("❌ 無効な選択です")
                return
        except (KeyboardInterrupt, EOFError):
            print("\n❌ 操作がキャンセルされました")
            return

    print(f"🔗 使用するRedirect URI: {redirect_uri}")
    print("🌐 OAuth認証URL生成中...")

    # 認証URL生成
    auth_url = generate_auth_url(client_id, redirect_uri)

    print()
    print("✅ 認証URL生成完了!")
    print("=" * 50)
    print()
    print("📝 次の手順:")
    print("1. 以下のURLをブラウザで開く")
    print("2. Zohoアカウントでログイン")
    print("3. アプリへのアクセス権限を承認")
    if redirect_uri == "http://localhost:8000/auth/callback":
        print("4. 🚀 自動的にRefresh Tokenが設定されます！")
        print("   （手動でのコード入力は不要です）")
    elif redirect_uri == "urn:ietf:wg:oauth:2.0:oob":
        print("4. 表示される認証コードをコピー")
    elif redirect_uri == "https://accounts.zoho.com/oauth/callback":
        print("4. リダイレクト後のURLから code= の値をコピー")
    else:
        print("4. リダイレクト後のURLまたは表示される認証コードをコピー")
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
    if redirect_uri == "http://localhost:8000/auth/callback":
        print("- 🎯 MCPサーバーが実行中であることを確認してください")
        print("- 認証完了後、自動的に設定が更新されます")
        print("- exchange_auth_code.py の実行は不要です")
    else:
        print("- 認証完了後は exchange_auth_code.py を実行してください")
    print("- エラーが発生した場合は、別のRedirect URIを試してください")
    print("- Zoho Developer ConsoleでRedirect URIの設定を確認してください")

if __name__ == "__main__":
    main()
