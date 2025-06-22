#!/usr/bin/env python3
"""
Zoho Portal ID取得ツール
現在の設定を使ってPortal IDを自動取得
"""

import asyncio
import httpx
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

async def get_zoho_access_token(client_id, client_secret, refresh_token):
    """リフレッシュトークンからアクセストークンを取得"""
    token_url = "https://accounts.zoho.com/oauth/v2/token"
    
    data = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                print(f"❌ トークン取得エラー: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"❌ API呼び出しエラー: {e}")
        return None

async def get_portal_info(access_token):
    """Zoho Projects APIからポータル情報を取得"""
    portals_url = "https://projectsapi.zoho.com/restapi/portals/"
    
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(portals_url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Portal情報取得エラー: {response.status_code}")
                print(f"レスポンス: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Portal API呼び出しエラー: {e}")
        return None

def update_env_with_portal_id(portal_id):
    """Portal IDで.envファイルを更新"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .envファイルが見つかりません")
        return False
    
    # 現在の.envファイルを読み込み
    lines = []
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # PORTAL_IDを更新
    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith('PORTAL_ID='):
            lines[i] = f"PORTAL_ID={portal_id}\n"
            updated = True
            break
    
    if not updated:
        # 新しい行として追加
        lines.append(f"PORTAL_ID={portal_id}\n")
    
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
    print("🔍 Zoho Portal ID 取得ツール")
    print("=" * 40)
    
    # 設定読み込み
    env_config = load_env_config()
    client_id = env_config.get("ZOHO_CLIENT_ID")
    client_secret = env_config.get("ZOHO_CLIENT_SECRET")
    refresh_token = env_config.get("ZOHO_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        print("❌ 必要な設定が不足しています")
        print("   ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN")
        return
    
    print("✅ OAuth設定確認完了")
    print()
    
    # アクセストークン取得
    print("🔄 アクセストークン取得中...")
    access_token = await get_zoho_access_token(client_id, client_secret, refresh_token)
    
    if not access_token:
        print("❌ アクセストークン取得に失敗しました")
        return
    
    print("✅ アクセストークン取得成功")
    print()
    
    # Portal情報取得
    print("🔄 Portal情報取得中...")
    portal_info = await get_portal_info(access_token)
    
    if not portal_info:
        print("❌ Portal情報取得に失敗しました")
        print("💡 手動でPortal IDを設定してください:")
        print("   1. https://projects.zoho.com/ にアクセス")
        print("   2. URLのportal/[PORTAL_ID]/部分を確認")
        print("   3. .envファイルのPORTAL_ID=に設定")
        return
    
    # Portal ID抽出
    if "portals" in portal_info and len(portal_info["portals"]) > 0:
        portal = portal_info["portals"][0]
        portal_id = portal.get("id")
        portal_name = portal.get("name", "Unknown")
        
        print("✅ Portal情報取得成功!")
        print(f"📋 Portal Name: {portal_name}")
        print(f"🆔 Portal ID: {portal_id}")
        print()
        
        # .envファイル更新
        print("💾 .envファイル更新中...")
        if update_env_with_portal_id(portal_id):
            print("✅ .envファイル更新完了!")
            print()
            print("🎯 次のステップ:")
            print("1. サーバー再起動:")
            print("   uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload")
            print("2. 完全動作確認:")
            print("   python verify_setup.py")
        else:
            print("❌ .envファイル更新失敗")
            print(f"📝 手動設定: PORTAL_ID={portal_id}")
    else:
        print("⚠️  Portal情報が見つかりませんでした")
        print("💡 手動でPortal IDを設定してください")

if __name__ == "__main__":
    asyncio.run(main()) 