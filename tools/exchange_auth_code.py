#!/usr/bin/env python3
"""
Zoho OAuth認証コード交換ツール
認証コードをREFRESH_TOKENに交換
"""

import sys
import httpx
import json
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

async def exchange_code_for_tokens(client_id, client_secret, auth_code, redirect_uri=None):
    """認証コードをトークンに交換"""
    if not redirect_uri:
        redirect_uri = "http://localhost:8000/auth/callback"
    
    token_url = "https://accounts.zoho.com/oauth/v2/token"
    
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": auth_code
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data, headers=headers)
            
            print(f"📡 API応答ステータス: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                return {
                    "success": True,
                    "data": token_data
                }
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"error": response.text}
                return {
                    "success": False,
                    "error": error_data,
                    "status_code": response.status_code
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": {"message": str(e)},
            "status_code": None
        }

def update_env_file(refresh_token, access_token=None):
    """新しいトークンで.envファイルを更新"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .envファイルが見つかりません")
        return False
    
    # 現在の.envファイルを読み込み
    lines = []
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # ZOHO_REFRESH_TOKENを更新
    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith('ZOHO_REFRESH_TOKEN='):
            lines[i] = f"ZOHO_REFRESH_TOKEN={refresh_token}\n"
            updated = True
            break
    
    if not updated:
        # 新しい行として追加
        lines.append(f"ZOHO_REFRESH_TOKEN={refresh_token}\n")
    
    # ファイルに書き戻し
    try:
        with open(env_file, 'w') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"❌ .envファイル更新エラー: {e}")
        return False

async def main():
    """メイン処理"""
    print("🔄 Zoho OAuth認証コード交換ツール")
    print("=" * 50)
    
    # コマンドライン引数から認証コードを取得
    if len(sys.argv) < 2:
        print("❌ 使用方法: python exchange_auth_code.py [認証コード]")
        print()
        print("📋 認証コードの取得方法:")
        print("1. generate_zoho_auth_url.py で生成されたURLにアクセス")
        print("2. 認証完了後のリダイレクトURLから code= の値をコピー")
        print("   例: http://localhost:8000/auth/callback?code=1000.abc123...")
        print("       ↑ 'code='以降の値をコピー")
        return
    
    auth_code = sys.argv[1].strip()
    
    # 現在の.env設定を確認
    env_config = load_env_config()
    client_id = env_config.get("ZOHO_CLIENT_ID")
    client_secret = env_config.get("ZOHO_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("❌ 必要な設定が不足しています:")
        if not client_id:
            print("   - ZOHO_CLIENT_ID が未設定")
        if not client_secret:
            print("   - ZOHO_CLIENT_SECRET が未設定")
        print()
        print("📝 .envファイルを確認してください")
        return
    
    print(f"✅ Client ID: {client_id[:20]}...")
    print(f"✅ Client Secret: {client_secret[:10]}...")
    print(f"✅ 認証コード: {auth_code[:20]}...")
    print()
    
    print("🔄 トークン交換処理中...")
    
    # トークン交換実行
    result = await exchange_code_for_tokens(client_id, client_secret, auth_code)
    
    if result["success"]:
        token_data = result["data"]
        
        print("✅ トークン交換成功!")
        print("=" * 30)
        
        # レスポンス内容を表示
        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")
        expires_in = token_data.get("expires_in", 0)
        scope = token_data.get("scope", "")
        
        print(f"🔑 Access Token: {access_token[:20]}... (有効期限: {expires_in}秒)")
        print(f"🔄 Refresh Token: {refresh_token[:20]}...")
        print(f"📋 スコープ: {scope}")
        
        if refresh_token:
            print()
            print("💾 .envファイルを更新中...")
            
            if update_env_file(refresh_token, access_token):
                print("✅ .envファイル更新完了!")
                print()
                print("🎯 次のステップ:")
                print("1. サーバーを再起動してください:")
                print("   Ctrl+C でサーバー停止")
                print("   uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload")
                print()
                print("2. 動作確認:")
                print("   python verify_setup.py")
            else:
                print("❌ .envファイル更新失敗")
                print("📝 手動で以下の値を .env ファイルに設定してください:")
                print(f"ZOHO_REFRESH_TOKEN={refresh_token}")
        else:
            print("⚠️  Refresh Token が取得できませんでした")
            print("💡 access_type=offline が設定されているか確認してください")
            
    else:
        print("❌ トークン交換失敗")
        print("=" * 30)
        
        error = result.get("error", {})
        status_code = result.get("status_code")
        
        if status_code:
            print(f"HTTPステータス: {status_code}")
        
        if isinstance(error, dict):
            error_type = error.get("error", "unknown")
            error_desc = error.get("error_description", error.get("message", "詳細不明"))
            
            print(f"エラータイプ: {error_type}")
            print(f"エラー詳細: {error_desc}")
            
            # 一般的なエラーの解決方法
            if error_type == "invalid_client":
                print("\n💡 解決方法:")
                print("- Client ID と Client Secret を確認")
                print("- Zoho Developer Console でアプリの設定を確認")
            elif error_type == "invalid_grant":
                print("\n💡 解決方法:")
                print("- 認証コードの期限切れ（10分間有効）")
                print("- 新しい認証コードを取得してください")
                print("- python generate_zoho_auth_url.py")
            elif error_type == "access_denied":
                print("\n💡 解決方法:")
                print("- 必要なスコープが設定されていない")
                print("- ユーザーがアクセスを拒否した")
        else:
            print(f"エラー: {error}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 