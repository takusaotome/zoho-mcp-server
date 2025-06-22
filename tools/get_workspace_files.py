#!/usr/bin/env python3
"""
ワークスペースファイル取得スクリプト
特定のワークスペースIDを指定してファイルリストを取得します。
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, Optional
import httpx
from datetime import datetime


class WorkspaceFilesClient:
    """ワークスペースファイルを取得するクライアント"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.client = None
        
        # デフォルトワークスペースID
        self.default_workspace_id = "hui9647cb257be9684fe294205f6519388d14"
    
    def log(self, message: str, level: str = "INFO"):
        """ログメッセージ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        colors = {
            "INFO": "\033[36m",    # シアン
            "SUCCESS": "\033[32m", # 緑
            "ERROR": "\033[31m",   # 赤
            "WARNING": "\033[33m", # 黄
            "HEADER": "\033[35m",  # マゼンタ
            "RESET": "\033[0m"     # リセット
        }
        color = colors.get(level, colors["INFO"])
        reset = colors["RESET"]
        print(f"{color}[{timestamp}] [{level}] {message}{reset}")
    
    async def get_workspace_files(self, workspace_id: Optional[str] = None):
        """ワークスペースIDを指定してファイルリストを取得"""
        self.log("📁 ワークスペースファイル取得", "HEADER")
        self.log("=" * 60, "HEADER")
        
        if not workspace_id:
            workspace_id = self.default_workspace_id
            
        self.log(f"🏢 ワークスペースID: {workspace_id}")
        self.log("")
        
        try:
            async with httpx.AsyncClient() as client:
                self.client = client
                
                # ワークスペースのファイルリストを取得
                await self._get_files_list(workspace_id)
                
        except Exception as e:
            self.log(f"❌ エラーが発生しました: {e}", "ERROR")
            raise
    
    async def _get_files_list(self, workspace_id: str):
        """ワークスペースIDを使用してファイルリストを取得"""
        try:
            # Team FolderAPIを使用してファイルリスト取得
            params = {"team_id": workspace_id}
            response = await self.client.get(f"{self.base_url}/api/team-folders", params=params)
            
            if response.status_code != 200:
                self.log(f"❌ ファイルリスト取得エラー: HTTP {response.status_code}", "ERROR")
                return
            
            data = response.json()
            team_folders = data.get('team_folders', [])
            total_count = data.get('total_count', 0)
            
            self.log(f"✅ ファイルリスト取得成功", "SUCCESS")
            self.log(f"📁 アイテム数: {total_count}件")
            
            if team_folders:
                self.log("")
                self._display_files(team_folders)
            else:
                self.log("📭 このワークスペースにファイルが見つかりませんでした", "WARNING")
                
        except Exception as e:
            self.log(f"❌ ファイルリスト取得中にエラーが発生: {e}", "ERROR")
    
    def _display_files(self, files: list):
        """ファイルリストを表示"""
        self.log("📋 ファイル・フォルダリスト:", "SUCCESS")
        self.log("-" * 60)
        
        for i, file_info in enumerate(files, 1):
            file_id = file_info.get('id', '不明')
            file_name = file_info.get('name', '不明')
            file_type = file_info.get('type', '不明')
            created_time = file_info.get('created_time', '不明')
            
            # アイコンを決定
            if file_type == 'files':
                icon = "📁"  # フォルダ
            else:
                icon = "📄"  # ファイル
            
            self.log(f"", "INFO")
            self.log(f"   {i}. {icon} {file_name}", "INFO")
            self.log(f"      📋 ID: {file_id}")
            self.log(f"      🏷️  Type: {file_type}")
            
            if created_time != '不明':
                self.log(f"      📅 作成: {created_time}")
            
            if i < len(files):
                self.log("      " + "-" * 40)


async def main():
    """メイン関数"""
    workspace_client = WorkspaceFilesClient()
    
    try:
        # コマンドライン引数でワークスペースIDを指定可能
        workspace_id = None
        if len(sys.argv) > 1:
            workspace_id = sys.argv[1]
            
        await workspace_client.get_workspace_files(workspace_id)
        
        workspace_client.log("=" * 60, "HEADER")
        workspace_client.log("🎯 取得完了", "SUCCESS")
        
        # 使用方法の表示
        if len(sys.argv) <= 1:
            workspace_client.log("", "INFO")
            workspace_client.log("💡 使用方法:", "INFO")
            workspace_client.log("   python tools/get_workspace_files.py                       # デフォルトワークスペース")
            workspace_client.log("   python tools/get_workspace_files.py <workspace_id>        # 指定ワークスペース")
            workspace_client.log(f"   python tools/get_workspace_files.py {workspace_client.default_workspace_id[:20]}... # 発見されたワークスペース")
        
    except KeyboardInterrupt:
        workspace_client.log("⚠️ 処理が中断されました", "WARNING")
    except Exception as e:
        workspace_client.log(f"❌ 予期しないエラーが発生しました: {e}", "ERROR")


if __name__ == "__main__":
    asyncio.run(main())