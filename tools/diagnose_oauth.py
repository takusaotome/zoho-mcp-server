#!/usr/bin/env python3
"""
OAuth診断ツール - Zoho OAuth認証の問題を詳細に分析
"""

import asyncio
import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv


def load_env_config() -> dict[str, str]:
    """環境変数を読み込み"""
    load_dotenv()
    return {
        "ZOHO_CLIENT_ID": os.getenv("ZOHO_CLIENT_ID", ""),
        "ZOHO_CLIENT_SECRET": os.getenv("ZOHO_CLIENT_SECRET", ""),
        "ZOHO_REFRESH_TOKEN": os.getenv("ZOHO_REFRESH_TOKEN", ""),
        "ZOHO_PORTAL_ID": os.getenv("ZOHO_PORTAL_ID", ""),
    }


async def test_token_refresh(client_id: str, client_secret: str, refresh_token: str) -> dict[str, Any]:
    """Refresh Tokenのテスト"""
    print("\n🔄 Refresh Token テスト中...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://accounts.zoho.com/oauth/v2/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                },
                timeout=30.0
            )

            response_data = response.json()

            result = {
                "status_code": response.status_code,
                "response": response_data,
                "success": response.status_code == 200 and "error" not in response_data,
                "headers": dict(response.headers)
            }

            if result["success"]:
                print("✅ Refresh Token 有効 - アクセストークン取得成功")
                print(f"   📍 API Domain: {response_data.get('api_domain', 'N/A')}")
                print(f"   ⏰ 有効期限: {response_data.get('expires_in', 'N/A')} 秒")
                print(f"   📝 スコープ: {response_data.get('scope', 'N/A')}")
            else:
                print("❌ Refresh Token エラー")
                print(f"   📊 ステータス: {response.status_code}")
                print(f"   🚨 エラー: {response_data.get('error', '不明')}")
                print(f"   📄 詳細: {response_data.get('error_description', 'N/A')}")

            return result

    except Exception as e:
        error_result = {
            "status_code": 0,
            "response": {"error": "network_error", "error_description": str(e)},
            "success": False,
            "exception": str(e)
        }
        print(f"❌ ネットワークエラー: {e}")
        return error_result


async def test_token_info(access_token: str) -> dict[str, Any]:
    """アクセストークンの情報取得テスト"""
    print("\n🔍 アクセストークン情報取得中...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://accounts.zoho.com/oauth/v2/token/info",
                data={"access_token": access_token},
                timeout=30.0
            )

            response_data = response.json()

            result = {
                "status_code": response.status_code,
                "response": response_data,
                "success": response.status_code == 200,
            }

            if result["success"]:
                print("✅ トークン情報取得成功")
                print(f"   👤 ユーザーID: {response_data.get('user_id', 'N/A')}")
                print(f"   📅 有効期限: {response_data.get('expires_in', 'N/A')} 秒")
                print(f"   📝 スコープ: {response_data.get('scope', 'N/A')}")
            else:
                print("❌ トークン情報取得エラー")
                print(f"   📊 ステータス: {response.status_code}")
                print(f"   🚨 エラー: {response_data.get('error', '不明')}")

            return result

    except Exception as e:
        error_result = {
            "status_code": 0,
            "response": {"error": "network_error", "error_description": str(e)},
            "success": False,
            "exception": str(e)
        }
        print(f"❌ ネットワークエラー: {e}")
        return error_result


async def test_api_call(access_token: str, portal_id: str) -> dict[str, Any]:
    """実際のAPI呼び出しテスト"""
    print("\n🔗 Zoho Projects API テスト中...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://projectsapi.zoho.com/restapi/portal/{portal_id}/projects/",
                headers={
                    "Authorization": f"Zoho-oauthtoken {access_token}",
                },
                timeout=30.0
            )

            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            result = {
                "status_code": response.status_code,
                "response": response_data,
                "success": response.status_code == 200,
            }

            if result["success"]:
                projects = response_data.get("projects", [])
                print(f"✅ API呼び出し成功 - {len(projects)} プロジェクト取得")
            else:
                print("❌ API呼び出しエラー")
                print(f"   📊 ステータス: {response.status_code}")
                print(f"   🚨 エラー: {response_data.get('error', response.text[:100])}")

            return result

    except Exception as e:
        error_result = {
            "status_code": 0,
            "response": {"error": "network_error", "error_description": str(e)},
            "success": False,
            "exception": str(e)
        }
        print(f"❌ ネットワークエラー: {e}")
        return error_result


def print_oauth_recommendations(config: dict[str, str], results: dict[str, Any]) -> None:
    """推奨事項の表示"""
    print("\n" + "="*60)
    print("📋 OAuth診断結果と推奨事項")
    print("="*60)

    # 設定確認
    missing_configs = [key for key, value in config.items() if not value]
    if missing_configs:
        print("❌ 設定不足:")
        for key in missing_configs:
            print(f"   • {key} が設定されていません")
        print("\n💡 対処法:")
        print("   1. config/env.example から .env ファイルを作成")
        print("   2. Zoho API Console で認証情報を取得")
        print("   3. Self Client方式の利用を推奨")
        print("   📖 詳細: docs/guides/zoho_self_client_setup.md")
        return

    # Refresh Token診断
    refresh_result = results.get("refresh_token", {})
    if not refresh_result.get("success"):
        error = refresh_result.get("response", {}).get("error", "unknown")
        print("❌ Refresh Token エラー:")

        if error == "invalid_code":
            print("   🔄 Refresh Token が無効または期限切れです")
            print("\n💡 対処法:")
            print("   1. 新しいRefresh Tokenを生成してください")
            print("   2. Self Client方式を使用:")
            print("      - Zoho API Console → Self Client")
            print("      - 必要なスコープを選択")
            print("      - 生成されたコードで新しいトークンを取得")
            print("   3. python tools/exchange_auth_code.py [コード] を実行")

        elif error == "invalid_client":
            print("   🔑 Client IDまたはClient Secretが間違っています")
            print("\n💡 対処法:")
            print("   1. Zoho API Console で認証情報を再確認")
            print("   2. .env ファイルの設定を更新")

        else:
            print(f"   🚨 予期しないエラー: {error}")
            print("   📄 詳細:", refresh_result.get("response", {}).get("error_description", "N/A"))

    # API呼び出し診断
    api_result = results.get("api_call", {})
    if api_result and not api_result.get("success"):
        status = api_result.get("status_code", 0)
        print(f"\n❌ API呼び出しエラー (Status: {status}):")

        if status == 401:
            print("   🔐 認証エラー - Portal IDまたはスコープの問題")
            print("\n💡 対処法:")
            print("   1. Portal IDが正しいか確認")
            print("   2. 必要なスコープが設定されているか確認")
            print("   3. python tools/get_portal_id.py でPortal ID取得")

        elif status == 403:
            print("   🚫 アクセス権限なし - スコープ不足")
            print("\n💡 対処法:")
            print("   1. 以下のスコープが必要です:")
            print("      - ZohoProjects.projects.READ")
            print("      - ZohoProjects.tasks.ALL")
            print("   2. 新しいRefresh Tokenを適切なスコープで生成")

    # 成功時の案内
    if refresh_result.get("success"):
        print("✅ OAuth認証は正常に機能しています！")

        if api_result and api_result.get("success"):
            print("✅ Zoho Projects APIアクセスも正常です！")
            print("\n🚀 次のステップ:")
            print("   1. MCPサーバーを起動: uvicorn server.main:app --port 8000")
            print("   2. プロジェクトタスクを取得: python tools/get_project_tasks.py")
        else:
            print("\n⚠️  OAuth認証は成功していますが、API呼び出しに問題があります")


async def main():
    """メイン診断処理"""
    print("🔍 Zoho OAuth 詳細診断ツール")
    print("=" * 40)

    # 設定読み込み
    config = load_env_config()

    # 設定表示
    print("\n📋 現在の設定:")
    for key, value in config.items():
        if value:
            masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else value
            print(f"   ✅ {key}: {masked_value}")
        else:
            print(f"   ❌ {key}: (未設定)")

    results = {}

    # Refresh Tokenテスト
    if config["ZOHO_CLIENT_ID"] and config["ZOHO_CLIENT_SECRET"] and config["ZOHO_REFRESH_TOKEN"]:
        refresh_result = await test_token_refresh(
            config["ZOHO_CLIENT_ID"],
            config["ZOHO_CLIENT_SECRET"],
            config["ZOHO_REFRESH_TOKEN"]
        )
        results["refresh_token"] = refresh_result

        # アクセストークンが取得できた場合の追加テスト
        if refresh_result.get("success"):
            access_token = refresh_result["response"]["access_token"]

            # トークン情報テスト
            token_info_result = await test_token_info(access_token)
            results["token_info"] = token_info_result

            # API呼び出しテスト (Portal IDが設定されている場合)
            if config["ZOHO_PORTAL_ID"]:
                api_result = await test_api_call(access_token, config["ZOHO_PORTAL_ID"])
                results["api_call"] = api_result

    # 結果の分析と推奨事項
    print_oauth_recommendations(config, results)

    # 詳細結果をJSONで保存
    output_file = "oauth_diagnosis_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "config": {k: "***" if v else "" for k, v in config.items()},  # 機密情報をマスク
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 詳細結果を {output_file} に保存しました")


if __name__ == "__main__":
    asyncio.run(main())
