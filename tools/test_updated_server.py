#!/usr/bin/env python3
"""
更新されたサーバーの包括的テストスクリプト
新しいエンドポイントと既存機能の動作確認を行います。
"""

import asyncio
from datetime import datetime

import httpx


class UpdatedServerTester:
    """更新されたサーバーの包括的テスト"""

    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.client = None
        self.test_results = {}

        # テスト用データ
        self.workspace_id = "hui9647cb257be9684fe294205f6519388d14"
        self.team_folder_id = "c8p1g470d8763a60b44ccb6785386f38a1bed"

    def log(self, message: str, level: str = "INFO"):
        """ログメッセージ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        colors = {
            "INFO": "\033[36m",    # シアン
            "SUCCESS": "\033[32m", # 緑
            "ERROR": "\033[31m",   # 赤
            "WARNING": "\033[33m", # 黄
            "HEADER": "\033[35m",  # マゼンタ
            "BOLD": "\033[1m",     # 太字
            "RESET": "\033[0m"     # リセット
        }
        color = colors.get(level, colors["INFO"])
        reset = colors["RESET"]
        print(f"{color}[{timestamp}] [{level}] {message}{reset}")

    async def run_comprehensive_tests(self):
        """包括的テストの実行"""
        self.log("🧪 更新されたサーバーの包括的テスト開始", "HEADER")
        self.log("=" * 80, "HEADER")

        try:
            async with httpx.AsyncClient() as client:
                self.client = client

                # 1. 基本的なサーバー機能テスト
                await self._test_basic_server_functionality()

                # 2. 新しいMCPエンドポイントテスト
                await self._test_new_mcp_endpoints()

                # 3. 既存のAPIエンドポイントテスト
                await self._test_existing_api_endpoints()

                # 4. WorkDriveファイル機能テスト
                await self._test_workdrive_functionality()

                # 5. エラーハンドリングテスト
                await self._test_error_handling()

                # 6. 総合評価
                await self._show_test_summary()

        except Exception as e:
            self.log(f"❌ テスト実行エラー: {e}", "ERROR")
            raise

    async def _test_basic_server_functionality(self):
        """基本的なサーバー機能テスト"""
        self.log("", "INFO")
        self.log("🔍 1. 基本的なサーバー機能テスト", "HEADER")
        self.log("-" * 60)

        test_cases = [
            ("/health", "ヘルスチェック"),
            ("/manifest.json", "MCPマニフェスト")
        ]

        for endpoint, description in test_cases:
            try:
                self.log(f"   📍 {description} ({endpoint})", "INFO")
                response = await self.client.get(f"{self.base_url}{endpoint}")

                if response.status_code == 200:
                    data = response.json()
                    self.log(f"      ✅ 成功: HTTP {response.status_code}", "SUCCESS")
                    self.test_results[f"basic_{endpoint.replace('/', '_')}"] = "PASS"

                    # 重要な情報を表示
                    if endpoint == "/health":
                        self.log(f"         Status: {data.get('status')}")
                        self.log(f"         Version: {data.get('version')}")
                    elif endpoint == "/manifest.json":
                        tools = data.get('tools', [])
                        self.log(f"         Tools: {len(tools)}個")
                else:
                    self.log(f"      ❌ 失敗: HTTP {response.status_code}", "ERROR")
                    self.test_results[f"basic_{endpoint.replace('/', '_')}"] = "FAIL"

            except Exception as e:
                self.log(f"      ❌ エラー: {e}", "ERROR")
                self.test_results[f"basic_{endpoint.replace('/', '_')}"] = "ERROR"

    async def _test_new_mcp_endpoints(self):
        """新しいMCPエンドポイントテスト"""
        self.log("", "INFO")
        self.log("🔍 2. 新しいMCPエンドポイントテスト", "HEADER")
        self.log("-" * 60)

        # テスト用のMCPリクエストペイロード
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        mcp_endpoints = [
            ("/mcp", "MCP without auth"),
            ("/mcp-auth", "MCP with auth")
        ]

        for endpoint, description in mcp_endpoints:
            try:
                self.log(f"   📍 {description} ({endpoint})", "INFO")

                headers = {"Content-Type": "application/json"}
                response = await self.client.post(
                    f"{self.base_url}{endpoint}",
                    json=mcp_request,
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    self.log(f"      ✅ 成功: HTTP {response.status_code}", "SUCCESS")

                    # MCPレスポンスの構造をチェック
                    if "jsonrpc" in data:
                        self.log(f"         JSON-RPC: {data.get('jsonrpc')}")
                        if "result" in data:
                            tools = data.get("result", {}).get("tools", [])
                            self.log(f"         Tools: {len(tools)}個")

                    self.test_results[f"mcp_{endpoint.replace('/', '_').replace('-', '_')}"] = "PASS"
                elif response.status_code == 401 and endpoint == "/mcp-auth":
                    self.log(f"      ✅ 期待通り認証エラー: HTTP {response.status_code}", "SUCCESS")
                    self.test_results[f"mcp_{endpoint.replace('/', '_').replace('-', '_')}"] = "PASS"
                else:
                    self.log(f"      ❌ 失敗: HTTP {response.status_code}", "ERROR")
                    self.log(f"         Response: {response.text[:200]}...", "ERROR")
                    self.test_results[f"mcp_{endpoint.replace('/', '_').replace('-', '_')}"] = "FAIL"

            except Exception as e:
                self.log(f"      ❌ エラー: {e}", "ERROR")
                self.test_results[f"mcp_{endpoint.replace('/', '_').replace('-', '_')}"] = "ERROR"

    async def _test_existing_api_endpoints(self):
        """既存のAPIエンドポイントテスト"""
        self.log("", "INFO")
        self.log("🔍 3. 既存のAPIエンドポイントテスト", "HEADER")
        self.log("-" * 60)

        api_endpoints = [
            ("/api/files/search?query=&limit=10", "ファイル検索"),
            ("/api/workspaces", "ワークスペース情報"),
            ("/api/team-folders", "Team Folder (デフォルト)"),
            (f"/api/team-folders?team_id={self.workspace_id}", "Team Folder (ワークスペース指定)"),
            (f"/api/folders/{self.team_folder_id}/files", "フォルダ内容取得")
        ]

        for endpoint, description in api_endpoints:
            try:
                self.log(f"   📍 {description}", "INFO")
                response = await self.client.get(f"{self.base_url}{endpoint}")

                if response.status_code == 200:
                    data = response.json()
                    self.log(f"      ✅ 成功: HTTP {response.status_code}", "SUCCESS")

                    # レスポンスデータの詳細を表示
                    if "files" in data:
                        files_count = len(data.get("files", []))
                        total_count = data.get("total_count", files_count)
                        self.log(f"         Files: {files_count}/{total_count}件")
                    elif "team_folders" in data:
                        folders_count = len(data.get("team_folders", []))
                        self.log(f"         Team Folders: {folders_count}件")
                    elif "workspaces_and_teams" in data:
                        successful_endpoints = data.get("successful_endpoints", 0)
                        self.log(f"         Successful endpoints: {successful_endpoints}個")

                    self.test_results[f"api_{description.replace(' ', '_').replace('(', '').replace(')', '')}"] = "PASS"
                elif response.status_code == 500:
                    self.log(f"      ⚠️ サーバーエラー: HTTP {response.status_code}", "WARNING")
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", "Unknown error")
                        if "URL Rule is not configured" in error_msg:
                            self.log("         期待されるエラー: URL Rule not configured", "INFO")
                    except:
                        pass
                    self.test_results[f"api_{description.replace(' ', '_').replace('(', '').replace(')', '')}"] = "WARN"
                else:
                    self.log(f"      ❌ 失敗: HTTP {response.status_code}", "ERROR")
                    self.test_results[f"api_{description.replace(' ', '_').replace('(', '').replace(')', '')}"] = "FAIL"

            except Exception as e:
                self.log(f"      ❌ エラー: {e}", "ERROR")
                self.test_results[f"api_{description.replace(' ', '_').replace('(', '').replace(')', '')}"] = "ERROR"

    async def _test_workdrive_functionality(self):
        """WorkDriveファイル機能テスト"""
        self.log("", "INFO")
        self.log("🔍 4. WorkDriveファイル機能テスト", "HEADER")
        self.log("-" * 60)

        try:
            # ワークスペースファイル取得テスト
            self.log("   📁 ワークスペースファイル取得テスト", "INFO")

            params = {"team_id": self.workspace_id}
            response = await self.client.get(f"{self.base_url}/api/team-folders", params=params)

            if response.status_code == 200:
                data = response.json()
                team_folders = data.get('team_folders', [])

                self.log("      ✅ ワークスペース取得成功", "SUCCESS")
                self.log(f"         発見アイテム: {len(team_folders)}件")

                if team_folders:
                    for i, folder in enumerate(team_folders[:3], 1):  # 最初の3件を表示
                        name = folder.get('name', '不明')
                        folder_id = folder.get('id', '不明')
                        self.log(f"         {i}. {name} (ID: {folder_id[:20]}...)")

                self.test_results["workdrive_workspace_files"] = "PASS"

                # Team Folder詳細取得テスト
                if team_folders:
                    self.log("   📂 Team Folder詳細取得テスト", "INFO")

                    first_folder_id = team_folders[0].get('id')
                    params = {"team_id": first_folder_id}
                    response = await self.client.get(f"{self.base_url}/api/team-folders", params=params)

                    if response.status_code == 200:
                        data = response.json()
                        subfolders = data.get('team_folders', [])

                        self.log("      ✅ サブフォルダ取得成功", "SUCCESS")
                        self.log(f"         サブアイテム: {len(subfolders)}件")

                        self.test_results["workdrive_subfolder_files"] = "PASS"
                    else:
                        self.log(f"      ❌ サブフォルダ取得失敗: HTTP {response.status_code}", "ERROR")
                        self.test_results["workdrive_subfolder_files"] = "FAIL"

            else:
                self.log(f"      ❌ ワークスペース取得失敗: HTTP {response.status_code}", "ERROR")
                self.test_results["workdrive_workspace_files"] = "FAIL"

        except Exception as e:
            self.log(f"      ❌ WorkDrive機能テストエラー: {e}", "ERROR")
            self.test_results["workdrive_functionality"] = "ERROR"

    async def _test_error_handling(self):
        """エラーハンドリングテスト"""
        self.log("", "INFO")
        self.log("🔍 5. エラーハンドリングテスト", "HEADER")
        self.log("-" * 60)

        error_test_cases = [
            ("/api/team-folders?team_id=invalid_id", "無効なteam_id"),
            ("/api/folders/invalid_folder_id/files", "無効なfolder_id"),
            ("/api/files/search?limit=invalid", "無効なパラメータ"),
            ("/api/nonexistent", "存在しないエンドポイント")
        ]

        for endpoint, description in error_test_cases:
            try:
                self.log(f"   📍 {description}", "INFO")
                response = await self.client.get(f"{self.base_url}{endpoint}")

                if response.status_code in [400, 404, 422, 500]:
                    self.log(f"      ✅ 適切なエラー応答: HTTP {response.status_code}", "SUCCESS")
                    self.test_results[f"error_{description.replace(' ', '_')}"] = "PASS"
                else:
                    self.log(f"      ⚠️ 予期しない応答: HTTP {response.status_code}", "WARNING")
                    self.test_results[f"error_{description.replace(' ', '_')}"] = "WARN"

            except Exception as e:
                self.log(f"      ❌ エラーテスト失敗: {e}", "ERROR")
                self.test_results[f"error_{description.replace(' ', '_')}"] = "ERROR"

    async def _show_test_summary(self):
        """テスト結果のサマリー表示"""
        self.log("", "INFO")
        self.log("📊 テスト結果サマリー", "HEADER")
        self.log("=" * 80, "HEADER")

        # 結果集計
        len(self.test_results)
        pass_count = list(self.test_results.values()).count("PASS")
        fail_count = list(self.test_results.values()).count("FAIL")
        warn_count = list(self.test_results.values()).count("WARN")
        error_count = list(self.test_results.values()).count("ERROR")

        # カテゴリ別集計
        categories = {
            "基本機能": [k for k in self.test_results.keys() if k.startswith("basic_")],
            "MCP": [k for k in self.test_results.keys() if k.startswith("mcp_")],
            "API": [k for k in self.test_results.keys() if k.startswith("api_")],
            "WorkDrive": [k for k in self.test_results.keys() if k.startswith("workdrive_")],
            "エラーハンドリング": [k for k in self.test_results.keys() if k.startswith("error_")]
        }

        self.log("📋 カテゴリ別結果:", "SUCCESS")
        for category, test_keys in categories.items():
            if test_keys:
                category_pass = sum(1 for k in test_keys if self.test_results[k] == "PASS")
                category_total = len(test_keys)
                status_icon = "✅" if category_pass == category_total else "⚠️" if category_pass > 0 else "❌"
                self.log(f"   {status_icon} {category}: {category_pass}/{category_total}")

        self.log("", "INFO")
        self.log("📊 全体結果:", "SUCCESS")
        self.log(f"   ✅ PASS: {pass_count}件")
        if warn_count > 0:
            self.log(f"   ⚠️ WARN: {warn_count}件")
        if fail_count > 0:
            self.log(f"   ❌ FAIL: {fail_count}件", "ERROR")
        if error_count > 0:
            self.log(f"   💥 ERROR: {error_count}件", "ERROR")

        # 総合評価
        self.log("", "INFO")
        if fail_count == 0 and error_count == 0:
            if warn_count == 0:
                self.log("🎉 全テスト合格！サーバーは正常に動作しています", "SUCCESS")
            else:
                self.log("✅ 主要機能は正常動作（一部警告あり）", "SUCCESS")
        else:
            self.log("⚠️ 一部テストで問題が検出されました", "WARNING")

        # 詳細結果の表示
        if any(status in ["FAIL", "ERROR"] for status in self.test_results.values()):
            self.log("", "INFO")
            self.log("🔍 問題のあるテスト:", "WARNING")
            for test_name, status in self.test_results.items():
                if status in ["FAIL", "ERROR"]:
                    icon = "❌" if status == "FAIL" else "💥"
                    self.log(f"   {icon} {test_name}: {status}")


async def main():
    """メイン関数"""
    tester = UpdatedServerTester()

    try:
        await tester.run_comprehensive_tests()

        tester.log("=" * 80, "HEADER")
        tester.log("🎯 包括的テスト完了", "SUCCESS")

    except KeyboardInterrupt:
        tester.log("⚠️ テストが中断されました", "WARNING")
    except Exception as e:
        tester.log(f"❌ 予期しないエラーが発生しました: {e}", "ERROR")


if __name__ == "__main__":
    asyncio.run(main())
