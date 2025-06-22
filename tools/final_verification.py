#!/usr/bin/env python3
"""Zoho MCP Server 最終確認スクリプト"""

import os
import json
import asyncio
import httpx
from dotenv import load_dotenv

# 環境設定読み込み
load_dotenv("temp_jwt.env")

def check_environment_variables():
    """環境変数をチェック"""
    print("🔧 環境変数チェック")
    print("=" * 50)
    
    required_vars = [
        "ZOHO_CLIENT_ID",
        "ZOHO_CLIENT_SECRET", 
        "ZOHO_REFRESH_TOKEN",
        "ZOHO_PORTAL_ID",
        "JWT_SECRET"
    ]
    
    all_good = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:20]}...")
        else:
            print(f"❌ {var}: 未設定")
            all_good = False
    
    return all_good

async def test_server_health():
    """サーバーの健康状態をチェック"""
    print("\n🏥 サーバー健康状態チェック")
    print("=" * 50)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ サーバー稼働中")
                print(f"   Status: {data.get('status')}")
                print(f"   Version: {data.get('version')}")
                return True
            else:
                print(f"❌ サーバーエラー: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ サーバー接続失敗: {e}")
        return False

async def test_zoho_api_direct():
    """Zoho APIに直接接続してテスト"""
    print("\n🔗 Zoho API 直接接続テスト")
    print("=" * 50)
    
    # OAuth token取得
    token_data = {
        "refresh_token": os.getenv("ZOHO_REFRESH_TOKEN"),
        "client_id": os.getenv("ZOHO_CLIENT_ID"),
        "client_secret": os.getenv("ZOHO_CLIENT_SECRET"),
        "grant_type": "refresh_token"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Access token取得
            response = await client.post(
                "https://accounts.zoho.com/oauth/v2/token",
                data=token_data,
                timeout=10.0
            )
            
            if response.status_code == 200:
                token_info = response.json()
                access_token = token_info.get("access_token")
                print(f"✅ Access token取得成功")
                
                # プロジェクト一覧取得テスト
                headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
                portal_id = os.getenv("ZOHO_PORTAL_ID")
                
                projects_response = await client.get(
                    f"https://projectsapi.zoho.com/restapi/portal/{portal_id}/projects/",
                    headers=headers,
                    timeout=10.0
                )
                
                if projects_response.status_code == 200:
                    projects_data = projects_response.json()
                    project_count = len(projects_data.get("projects", []))
                    print(f"✅ プロジェクト取得成功: {project_count}個")
                    return True
                else:
                    print(f"❌ プロジェクト取得失敗: {projects_response.status_code}")
                    print(f"   エラー: {projects_response.text}")
                    return False
            else:
                print(f"❌ Access token取得失敗: {response.status_code}")
                print(f"   エラー: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Zoho API接続失敗: {e}")
        return False

def check_cursor_config():
    """Cursor設定ファイルをチェック"""
    print("\n⚙️  Cursor設定ファイルチェック")
    print("=" * 50)
    
    config_file = "cursor-mcp-config.json"
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            print(f"✅ 設定ファイル存在: {config_file}")
            
            if "mcpServers" in config:
                servers = config["mcpServers"]
                print(f"✅ MCPサーバー設定: {len(servers)}個")
                
                if "zoho-mcp-server" in servers:
                    zoho_config = servers["zoho-mcp-server"]
                    print(f"✅ Zoho MCP Server設定存在")
                    
                    env_vars = zoho_config.get("env", {})
                    required_env = ["ZOHO_CLIENT_ID", "ZOHO_PORTAL_ID", "JWT_SECRET"]
                    
                    for var in required_env:
                        if var in env_vars:
                            print(f"   ✅ {var}: 設定済み")
                        else:
                            print(f"   ❌ {var}: 未設定")
                    
                    return True
                else:
                    print(f"❌ zoho-mcp-server設定が見つかりません")
                    return False
            else:
                print(f"❌ mcpServers設定が見つかりません")
                return False
                
        except Exception as e:
            print(f"❌ 設定ファイル読み込みエラー: {e}")
            return False
    else:
        print(f"❌ 設定ファイルが見つかりません: {config_file}")
        return False

async def main():
    print("🚀 Zoho MCP Server 最終確認")
    print("=" * 80)
    
    results = []
    
    # 1. 環境変数チェック
    env_ok = check_environment_variables()
    results.append(("環境変数", env_ok))
    
    # 2. サーバー健康状態チェック
    server_ok = await test_server_health()
    results.append(("サーバー稼働", server_ok))
    
    # 3. Zoho API直接接続テスト
    if env_ok:
        zoho_ok = await test_zoho_api_direct()
        results.append(("Zoho API接続", zoho_ok))
    else:
        results.append(("Zoho API接続", False))
    
    # 4. Cursor設定チェック
    cursor_ok = check_cursor_config()
    results.append(("Cursor設定", cursor_ok))
    
    # 結果まとめ
    print("\n" + "=" * 80)
    print("📊 最終確認結果")
    print("=" * 80)
    
    for test_name, result in results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name:15} : {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 全てのテストに合格しました！")
        print("\n📋 次のステップ:")
        print("1. Cursorを再起動してください")
        print("2. Cursor設定でMCPサーバーが認識されることを確認")
        print("3. Zoho Projects関連のタスクをCursorで試してください")
        print("\n🔧 利用可能なMCPツール:")
        tools = [
            "listTasks - タスク一覧取得",
            "createTask - タスク作成", 
            "updateTask - タスク更新",
            "getTaskDetail - タスク詳細取得",
            "getProjectSummary - プロジェクト概要取得"
        ]
        for tool in tools:
            print(f"   • {tool}")
    else:
        print("\n⚠️  一部のテストが失敗しました")
        print("失敗した項目を確認して修正してください")

if __name__ == "__main__":
    asyncio.run(main()) 