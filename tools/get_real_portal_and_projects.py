#!/usr/bin/env python3
"""Zoho Projects Portal IDと実際のプロジェクト一覧を取得するスクリプト"""

import json
import asyncio
import httpx
from urllib.parse import urlencode

# Zoho OAuth設定（環境変数から取得）
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("❌ 環境変数が設定されていません")
    print("必要な環境変数: ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN")
    exit(1)

async def get_access_token():
    """リフレッシュトークンからアクセストークンを取得"""
    token_data = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://accounts.zoho.com/oauth/v2/token",
            data=token_data
        )
        
        if response.status_code == 200:
            token_info = response.json()
            print(f"✅ Access token 取得成功")
            return token_info.get("access_token")
        else:
            print(f"❌ Access token取得失敗: {response.status_code}")
            print(response.text)
            return None

async def get_portals(access_token):
    """利用可能なPortal一覧を取得"""
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    
    async with httpx.AsyncClient() as client:
        # まず汎用URLで試す
        response = await client.get(
            "https://projectsapi.zoho.com/restapi/portals/",
            headers=headers
        )
        
        print(f"Portal API レスポンス: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Portal情報取得成功:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        else:
            print(f"❌ Portal取得失敗: {response.text}")
            return None

async def get_projects_with_portal(access_token, portal_id):
    """指定されたPortal IDでプロジェクト一覧を取得"""
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    
    async with httpx.AsyncClient() as client:
        url = f"https://projectsapi.zoho.com/restapi/portal/{portal_id}/projects/"
        response = await client.get(url, headers=headers)
        
        print(f"Projects API レスポンス ({portal_id}): {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ プロジェクト情報取得成功 (Portal: {portal_id}):")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        else:
            print(f"❌ プロジェクト取得失敗 (Portal: {portal_id}): {response.text}")
            return None

async def try_different_project_endpoints(access_token):
    """異なるエンドポイントでプロジェクト情報を試行"""
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    
    endpoints = [
        "https://projectsapi.zoho.com/restapi/projects/",
        "https://projectsapi.zoho.com/restapi/portal/projects/",
        "https://projects.zoho.com/restapi/projects/",
    ]
    
    async with httpx.AsyncClient() as client:
        for endpoint in endpoints:
            try:
                print(f"🔍 試行中: {endpoint}")
                response = await client.get(endpoint, headers=headers)
                print(f"   レスポンス: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ 成功! データ:")
                    print(f"   {json.dumps(data, indent=4, ensure_ascii=False)}")
                    return endpoint, data
                else:
                    print(f"   ❌ 失敗: {response.text[:200]}")
                    
            except Exception as e:
                print(f"   ❌ エラー: {e}")
    
    return None, None

async def main():
    print("🚀 Zoho Projects Portal ID とプロジェクト情報を取得中...")
    print("=" * 60)
    
    # Step 1: Access token取得
    access_token = await get_access_token()
    if not access_token:
        print("❌ アクセストークンが取得できませんでした")
        return
    
    print("\n" + "=" * 60)
    print("📋 Step 1: Portal情報を取得")
    print("=" * 60)
    
    # Step 2: Portal情報取得
    portals = await get_portals(access_token)
    
    print("\n" + "=" * 60)
    print("📂 Step 2: プロジェクト情報を取得（複数エンドポイント試行）")
    print("=" * 60)
    
    # Step 3: 複数のエンドポイントでプロジェクト情報を試行
    success_endpoint, projects_data = await try_different_project_endpoints(access_token)
    
    print("\n" + "=" * 60)
    print("📝 結果まとめ")
    print("=" * 60)
    
    if portals:
        print("✅ Portal情報: 取得成功")
        if isinstance(portals, dict) and 'portals' in portals:
            for portal in portals['portals']:
                print(f"   Portal ID: {portal.get('id', 'N/A')}")
                print(f"   Portal Name: {portal.get('name', 'N/A')}")
    else:
        print("❌ Portal情報: 取得失敗")
    
    if success_endpoint and projects_data:
        print(f"✅ プロジェクト情報: 取得成功")
        print(f"   成功したエンドポイント: {success_endpoint}")
        
        # プロジェクト一覧を表示
        if isinstance(projects_data, dict):
            if 'projects' in projects_data:
                print(f"   プロジェクト数: {len(projects_data['projects'])}")
                for i, project in enumerate(projects_data['projects'][:3]):  # 最初の3つだけ表示
                    print(f"   [{i+1}] ID: {project.get('id', 'N/A')}, Name: {project.get('name', 'N/A')}")
            else:
                print(f"   データ構造: {list(projects_data.keys())}")
    else:
        print("❌ プロジェクト情報: 取得失敗")
    
    # 環境変数設定のヒント
    print("\n" + "=" * 60)
    print("🔧 環境変数設定のヒント")
    print("=" * 60)
    
    if portals and isinstance(portals, dict) and 'portals' in portals:
        portal_id = portals['portals'][0].get('id') if portals['portals'] else None
        if portal_id:
            print(f"ZOHO_PORTAL_ID={portal_id}")
    
    if projects_data and isinstance(projects_data, dict) and 'projects' in projects_data:
        project_id = projects_data['projects'][0].get('id') if projects_data['projects'] else None
        if project_id:
            print(f"# テスト用プロジェクトID: {project_id}")

if __name__ == "__main__":
    asyncio.run(main()) 