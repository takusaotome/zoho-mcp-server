#!/usr/bin/env python3
"""MCP Server経由で指定プロジェクトのタスクを取得"""

import asyncio
import httpx
import json
import jwt
import os
import sys
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 環境設定読み込み
load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
MCP_SERVER_URL = "http://localhost:8000"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "reports/exports")

def get_project_id():
    """コマンドライン引数または環境変数からプロジェクトIDを取得"""
    parser = argparse.ArgumentParser(description="Zoho Projects のタスクを取得")
    parser.add_argument("--project-id", "-p", type=str,
                       help="プロジェクトID (例: 1790933000004263341)")
    
    args = parser.parse_args()
    
    # コマンドライン引数が優先
    if args.project_id:
        return args.project_id
    
    # 環境変数から取得
    project_id = os.getenv("TARGET_PROJECT_ID")
    if project_id and project_id != "YOUR_PROJECT_ID_HERE":
        return project_id
    
    # どちらも設定されていない場合
    print("❌ プロジェクトIDが指定されていません")
    print("\n📝 指定方法:")
    print("1. コマンドライン引数: python tools/get_project_tasks_via_mcp.py --project-id 1790933000004263341")
    print("2. 環境変数: .envファイルに TARGET_PROJECT_ID=1790933000004263341 を追加")
    sys.exit(1)

# プロジェクトID取得
PROJECT_ID = get_project_id()

def generate_jwt_token():
    """MCP Server用JWTトークンを生成"""
    payload = {
        "sub": "test_user",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

async def call_mcp_tool(tool_name, arguments):
    """MCPツールを呼び出し"""
    token = generate_jwt_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "method": "callTool",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{MCP_SERVER_URL}/mcp",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"❌ HTTP エラー: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"❌ 接続エラー: {e}")
            return None

def parse_mcp_response(response_data):
    """MCPレスポンスを解析してタスクデータを取得"""
    import ast
    
    if not response_data:
        return None
    
    if "error" in response_data and response_data["error"]:
        print(f"❌ MCPエラー: {response_data['error']['message']}")
        return None
    
    if "result" not in response_data or not response_data["result"]:
        print("❌ 結果が空です")
        return None
    
    result = response_data["result"]
    
    # MCP形式のレスポンスを解析
    if isinstance(result, dict) and "content" in result:
        content = result["content"]
        if isinstance(content, list) and len(content) > 0:
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text = item["text"]
                    
                    # まずJSONとして試行
                    try:
                        parsed_data = json.loads(text)
                        return parsed_data
                    except json.JSONDecodeError:
                        pass
                    
                    # Python辞書形式として試行
                    try:
                        parsed_data = ast.literal_eval(text)
                        return parsed_data
                    except (ValueError, SyntaxError):
                        print(f"❌ 解析失敗: {text[:100]}...")
                        return None
    
    return None

def format_task_info(task):
    """タスク情報を整形"""
    task_id = task.get('id', 'N/A')
    name = task.get('name', 'N/A')
    
    # ステータス情報を取得
    status_info = task.get('status', {})
    if isinstance(status_info, dict):
        status = status_info.get('name', 'Unknown')
    else:
        status = str(status_info) if status_info else 'Unknown'
    
    # 担当者情報
    owner_info = task.get('owner', {})
    if isinstance(owner_info, dict):
        owner = owner_info.get('name', 'Unassigned')
    else:
        owner = str(owner_info) if owner_info else 'Unassigned'
    
    # 優先度
    priority = task.get('priority', 'Normal')
    
    # 期限
    due_date = task.get('due_date', 'N/A')
    if due_date != 'N/A':
        try:
            # 日付を整形
            date_obj = datetime.strptime(due_date, '%m-%d-%Y')
            due_date = date_obj.strftime('%Y年%m月%d日')
        except:
            pass
    
    # 作成日
    created_date = task.get('created_date', 'N/A')
    if created_date != 'N/A':
        try:
            date_obj = datetime.strptime(created_date, '%m-%d-%Y')
            created_date = date_obj.strftime('%Y年%m月%d日')
        except:
            pass
    
    return {
        'id': task_id,
        'name': name,
        'status': status,
        'owner': owner,
        'priority': priority,
        'due_date': due_date,
        'created_date': created_date
    }

async def get_project_summary():
    """プロジェクトサマリーを取得"""
    print("📊 プロジェクトサマリー取得中...")
    
    response = await call_mcp_tool("getProjectSummary", {
        "project_id": PROJECT_ID
    })
    
    summary_data = parse_mcp_response(response)
    if summary_data:
        print("✅ プロジェクトサマリー取得成功")
        return summary_data
    else:
        print("❌ プロジェクトサマリー取得失敗")
        return None

async def get_all_tasks():
    """全てのタスクを取得"""
    print("📋 全タスク取得中...")
    
    response = await call_mcp_tool("listTasks", {
        "project_id": PROJECT_ID
    })
    
    tasks_data = parse_mcp_response(response)
    if tasks_data and "tasks" in tasks_data:
        print(f"✅ タスク取得成功: {len(tasks_data['tasks'])}個")
        return tasks_data["tasks"]
    else:
        print("❌ タスク取得失敗")
        return []

async def get_open_tasks():
    """オープンなタスクのみ取得"""
    print("🔓 オープンタスク取得中...")
    
    response = await call_mcp_tool("listTasks", {
        "project_id": PROJECT_ID,
        "status": "open"
    })
    
    tasks_data = parse_mcp_response(response)
    if tasks_data and "tasks" in tasks_data:
        print(f"✅ オープンタスク取得成功: {len(tasks_data['tasks'])}個")
        return tasks_data["tasks"]
    else:
        print("❌ オープンタスク取得失敗")
        return []

async def main():
    print("🎯 サンプルプロジェクト タスク取得 (MCP Server経由)")
    print("=" * 70)
    print(f"プロジェクトID: {PROJECT_ID}")
    print("=" * 70)
    
    # Step 1: プロジェクトサマリー取得
    summary = await get_project_summary()
    if summary:
        print(f"\n📊 プロジェクト概要:")
        project_info = summary.get('project', {})
        print(f"   名前: {project_info.get('name', 'N/A')}")
        print(f"   ステータス: {project_info.get('status', 'N/A')}")
        print(f"   オーナー: {project_info.get('owner_name', 'N/A')}")
    
    print("\n" + "=" * 70)
    
    # Step 2: 全タスク取得
    all_tasks = await get_all_tasks()
    
    print("\n" + "-" * 70)
    
    # Step 3: オープンタスク取得
    open_tasks = await get_open_tasks()
    
    # Step 4: 結果表示
    print("\n" + "=" * 70)
    print("📋 タスク一覧")
    print("=" * 70)
    
    if all_tasks:
        for i, task in enumerate(all_tasks, 1):
            formatted = format_task_info(task)
            print(f"\n【{i:2d}】 {formatted['name']}")
            print(f"     ID: {formatted['id']}")
            print(f"     ステータス: {formatted['status']}")
            print(f"     担当者: {formatted['owner']}")
            print(f"     優先度: {formatted['priority']}")
            print(f"     期限: {formatted['due_date']}")
            print(f"     作成日: {formatted['created_date']}")
    else:
        print("タスクが見つかりませんでした")
    
    # Step 5: 統計情報
    if all_tasks:
        print("\n" + "=" * 70)
        print("📊 統計情報")
        print("=" * 70)
        
        # ステータス別集計
        status_count = {}
        for task in all_tasks:
            formatted = format_task_info(task)
            status = formatted['status']
            status_count[status] = status_count.get(status, 0) + 1
        
        print("ステータス別タスク数:")
        for status, count in status_count.items():
            print(f"  • {status}: {count}個")
        
        # 担当者別集計
        owner_count = {}
        for task in all_tasks:
            formatted = format_task_info(task)
            owner = formatted['owner']
            owner_count[owner] = owner_count.get(owner, 0) + 1
        
        print("\n担当者別タスク数:")
        for owner, count in sorted(owner_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {owner}: {count}個")
    
    print("\n" + "=" * 70)
    print("✅ タスク取得完了 (MCP Server経由)")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main()) 