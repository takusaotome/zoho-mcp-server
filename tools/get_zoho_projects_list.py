#!/usr/bin/env python3
"""Zoho Projectsのリストを取得するスクリプト"""

import asyncio
import httpx
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# 環境設定読み込み
load_dotenv("temp_jwt.env")

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
PORTAL_ID = os.getenv("ZOHO_PORTAL_ID")

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
            return token_info.get("access_token")
        else:
            print(f"❌ Access token取得失敗: {response.status_code}")
            print(response.text)
            return None

async def get_projects_list(access_token):
    """プロジェクト一覧を取得"""
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    
    async with httpx.AsyncClient() as client:
        url = f"https://projectsapi.zoho.com/restapi/portal/{PORTAL_ID}/projects/"
        response = await client.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ プロジェクト取得失敗: {response.status_code}")
            print(response.text)
            return None

def format_project_info(project):
    """プロジェクト情報を整形"""
    name = project.get('name', 'N/A')
    project_id = project.get('id', 'N/A')
    status = project.get('status', 'N/A')
    owner = project.get('owner_name', 'N/A')
    created_date = project.get('created_date', 'N/A')
    
    # 日付を整形
    if created_date != 'N/A':
        try:
            # Zohoの日付形式を解析して整形
            date_obj = datetime.strptime(created_date, '%m-%d-%Y')
            created_date = date_obj.strftime('%Y年%m月%d日')
        except:
            pass
    
    return {
        'name': name,
        'id': project_id,
        'status': status,
        'owner': owner,
        'created_date': created_date
    }

async def main():
    print("📂 Zoho Projects リスト取得")
    print("=" * 60)
    print(f"Portal ID: {PORTAL_ID}")
    print("=" * 60)
    
    # Step 1: Access token取得
    access_token = await get_access_token()
    if not access_token:
        print("❌ アクセストークンが取得できませんでした")
        return
    
    print("✅ Access token取得成功")
    
    # Step 2: プロジェクト一覧取得
    projects_data = await get_projects_list(access_token)
    if not projects_data:
        print("❌ プロジェクトデータが取得できませんでした")
        return
    
    projects = projects_data.get('projects', [])
    print(f"✅ プロジェクト取得成功: {len(projects)}個")
    
    # Step 3: プロジェクト一覧を表示
    print("\n" + "=" * 60)
    print("📋 プロジェクト一覧")
    print("=" * 60)
    
    for i, project in enumerate(projects, 1):
        formatted = format_project_info(project)
        print(f"\n【{i:2d}】 {formatted['name']}")
        print(f"     ID: {formatted['id']}")
        print(f"     ステータス: {formatted['status']}")
        print(f"     オーナー: {formatted['owner']}")
        print(f"     作成日: {formatted['created_date']}")
    
    # Step 4: 統計情報
    print("\n" + "=" * 60)
    print("📊 統計情報")
    print("=" * 60)
    
    # ステータス別集計
    status_count = {}
    for project in projects:
        status = project.get('status', 'Unknown')
        status_count[status] = status_count.get(status, 0) + 1
    
    print("ステータス別プロジェクト数:")
    for status, count in status_count.items():
        print(f"  • {status}: {count}個")
    
    # オーナー別集計（上位5名）
    owner_count = {}
    for project in projects:
        owner = project.get('owner_name', 'Unknown')
        owner_count[owner] = owner_count.get(owner, 0) + 1
    
    print("\nオーナー別プロジェクト数（上位5名）:")
    sorted_owners = sorted(owner_count.items(), key=lambda x: x[1], reverse=True)
    for owner, count in sorted_owners[:5]:
        print(f"  • {owner}: {count}個")
    
    # Step 5: JSONファイルに保存
    output_file = "zoho_projects_list.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(projects_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 詳細データを保存しました: {output_file}")
    
    print("\n" + "=" * 60)
    print("✅ プロジェクト一覧取得完了")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main()) 