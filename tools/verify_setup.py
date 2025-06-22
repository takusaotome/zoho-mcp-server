#!/usr/bin/env python3
"""
Zoho MCP Server 設定確認・動作テスト
段階的にサーバーの状態を確認する
"""

import asyncio
import subprocess

import httpx

BASE_URL = "http://0.0.0.0:8000"

async def check_server_status():
    """サーバーの起動状態を確認"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ サーバー起動: OK ({health_data.get('status')})")
                return True
            else:
                print(f"❌ サーバー応答エラー: {response.status_code}")
                return False
    except httpx.RequestError:
        print("❌ サーバー未起動 または 接続不可")
        return False

async def test_authentication():
    """JWT認証テスト"""
    try:
        # JWTトークンを生成
        result = subprocess.run(['python', 'generate_test_token.py'],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ JWTトークン生成失敗")
            return None

        # 出力からトークンを抽出
        lines = result.stdout.split('\n')
        token = None
        for line in lines:
            if line.startswith('eyJ'):  # JWTトークンの開始
                token = line.strip()
                break

        if not token:
            print("❌ JWTトークン抽出失敗")
            return None

        print("✅ JWTトークン生成: OK")
        return token

    except Exception as e:
        print(f"❌ JWT認証エラー: {e}")
        return None

async def test_mcp_protocol(jwt_token):
    """MCPプロトコルテスト"""
    if not jwt_token:
        print("❌ MCPテストスキップ (JWT認証失敗)")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}"
    }

    # ツール一覧取得テスト
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "listTools",
                    "params": {},
                    "id": 1
                },
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                result = response.json()
                if "result" in result and "tools" in result["result"]:
                    tool_count = len(result["result"]["tools"])
                    print(f"✅ MCPプロトコル: OK ({tool_count}個のツール)")
                    return True
                else:
                    print("❌ MCPレスポンス形式エラー")
                    return False
            else:
                print(f"❌ MCP通信エラー: {response.status_code}")
                return False

    except Exception as e:
        print(f"❌ MCPプロトコルエラー: {e}")
        return False

async def test_zoho_api_call(jwt_token):
    """Zoho API呼び出しテスト"""
    if not jwt_token:
        print("❌ Zoho APIテストスキップ (JWT認証失敗)")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "callTool",
                    "params": {
                        "name": "listTasks",
                        "arguments": {
                            "project_id": "test_project_123",
                            "status": "open"
                        }
                    },
                    "id": 2
                },
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                result = response.json()
                if "error" in result and result["error"]:
                    error = result["error"]
                    if "invalid_client" in error.get("message", ""):
                        print("⚠️  Zoho API: OAuth設定不完全 (予想通り)")
                    else:
                        print(f"⚠️  Zoho API: {error.get('message', '').split(':')[0]}")
                else:
                    print("✅ Zoho API: 正常レスポンス")
            else:
                print(f"❌ Zoho API呼び出しエラー: {response.status_code}")

    except Exception as e:
        print(f"❌ Zoho APIテストエラー: {e}")

async def main():
    """メイン確認フロー"""
    print("🔍 Zoho MCP Server 動作確認")
    print("=" * 40)

    # Step 1: 設定診断
    print("\n📋 Step 1: 設定診断")
    print("-" * 20)
    try:
        result = subprocess.run(['python', 'check_configuration.py'],
                              capture_output=True, text=True)
        if "基本設定は完了しています" in result.stdout:
            print("✅ 設定: 基本完了")
        else:
            print("⚠️  設定: 要修正項目あり")
    except Exception as e:
        print(f"❌ 設定診断エラー: {e}")

    # Step 2: サーバー確認
    print("\n🔧 Step 2: サーバー状態確認")
    print("-" * 20)
    server_ok = await check_server_status()

    if not server_ok:
        print("\n💡 サーバー起動方法:")
        print("   uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload")
        return

    # Step 3: 認証確認
    print("\n🔐 Step 3: JWT認証確認")
    print("-" * 20)
    jwt_token = await test_authentication()

    # Step 4: MCPプロトコル確認
    print("\n📡 Step 4: MCPプロトコル確認")
    print("-" * 20)
    mcp_ok = await test_mcp_protocol(jwt_token)

    # Step 5: Zoho API確認
    print("\n🌐 Step 5: Zoho API確認")
    print("-" * 20)
    await test_zoho_api_call(jwt_token)

    # 総合結果
    print("\n" + "=" * 40)
    print("🎯 確認結果サマリー")
    print("-" * 20)

    if server_ok and jwt_token and mcp_ok:
        print("✅ MCP Server基本機能: 正常動作")
        print("💡 次のステップ: Zoho OAuth設定完了で完全機能")
    else:
        print("⚠️  一部機能に問題があります")
        print("📝 上記の診断結果を確認して修正してください")

if __name__ == "__main__":
    asyncio.run(main())
