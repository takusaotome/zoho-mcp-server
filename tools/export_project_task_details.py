#!/usr/bin/env python3
"""サンプルプロジェクトプロジェクトのタスク詳細をエクスポート"""

import asyncio
import httpx
import json
import jwt
import os
import ast
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 環境設定読み込み
load_dotenv("temp_jwt.env")

JWT_SECRET = os.getenv("JWT_SECRET")
MCP_SERVER_URL = "http://localhost:8000"

# サンプルプロジェクトプロジェクトのID
PROJECT_ID = "1790933000004263341"

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
                return response.json()
            else:
                print(f"❌ HTTP エラー: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"❌ 接続エラー: {e}")
            return None

def parse_mcp_response(response_data):
    """MCPレスポンスを解析"""
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
                        return json.loads(text)
                    except json.JSONDecodeError:
                        pass
                    
                    # Python辞書形式として試行
                    try:
                        return ast.literal_eval(text)
                    except (ValueError, SyntaxError):
                        print(f"❌ 解析失敗: {text[:100]}...")
                        return None
    
    return None

def format_task_detail(task):
    """タスク詳細情報を整形"""
    # 基本情報
    task_detail = {
        "id": str(task.get('id', 'N/A')),
        "name": task.get('name', 'N/A'),
        "description": task.get('description', ''),
        "created_date": task.get('created_date', 'N/A'),
        "updated_date": task.get('updated_date', 'N/A'),
        "due_date": task.get('due_date', 'N/A'),
        "priority": task.get('priority', 'Normal'),
        "percent_complete": task.get('percent_complete', 0),
        "url": task.get('url', 'N/A')
    }
    
    # ステータス情報
    status_info = task.get('status', {})
    if isinstance(status_info, dict):
        task_detail["status"] = {
            "name": status_info.get('name', 'Unknown'),
            "id": status_info.get('id', 'N/A'),
            "color_code": status_info.get('color_code', 'N/A')
        }
    else:
        task_detail["status"] = {
            "name": str(status_info) if status_info else 'Unknown',
            "id": 'N/A',
            "color_code": 'N/A'
        }
    
    # 担当者情報
    owner_info = task.get('owner', {})
    if isinstance(owner_info, dict):
        task_detail["owner"] = {
            "name": owner_info.get('name', 'Unassigned'),
            "id": owner_info.get('id', 'N/A'),
            "email": owner_info.get('email', 'N/A')
        }
    else:
        task_detail["owner"] = {
            "name": str(owner_info) if owner_info else 'Unassigned',
            "id": 'N/A',
            "email": 'N/A'
        }
    
    return task_detail

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

async def get_task_details(task_id):
    """個別タスクの詳細を取得"""
    response = await call_mcp_tool("getTaskDetail", {
        "task_id": task_id
    })
    
    task_detail = parse_mcp_response(response)
    return task_detail

async def export_task_details():
    """タスク詳細をエクスポート"""
    print("🎯 サンプルプロジェクト タスク詳細エクスポート")
    print("=" * 70)
    print(f"プロジェクトID: {PROJECT_ID}")
    print("=" * 70)
    
    # Step 1: プロジェクトサマリー取得
    summary = await get_project_summary()
    
    # Step 2: 全タスク取得
    all_tasks = await get_all_tasks()
    
    if not all_tasks:
        print("❌ タスクが取得できませんでした")
        return
    
    # Step 3: 各タスクの詳細情報を整形
    print("\n📝 タスク詳細情報を整形中...")
    detailed_tasks = []
    
    for i, task in enumerate(all_tasks, 1):
        print(f"   [{i:2d}/{len(all_tasks)}] {task.get('name', 'N/A')[:50]}...")
        
        # 基本タスク情報を整形
        formatted_task = format_task_detail(task)
        
        # より詳細な情報が必要な場合はgetTaskDetailを呼び出し
        # (今回は基本情報で十分なのでスキップ)
        
        detailed_tasks.append(formatted_task)
    
    # Step 4: エクスポートデータを構築
    export_data = {
        "export_info": {
            "project_id": PROJECT_ID,
            "project_name": "サンプルプロジェクト",
            "export_date": datetime.now().isoformat(),
            "total_tasks": len(detailed_tasks)
        },
        "project_summary": summary if summary else {},
        "tasks": detailed_tasks,
        "statistics": {
            "status_breakdown": {},
            "owner_breakdown": {},
            "priority_breakdown": {}
        }
    }
    
    # Step 5: 統計情報を計算
    for task in detailed_tasks:
        # ステータス別集計
        status = task["status"]["name"]
        export_data["statistics"]["status_breakdown"][status] = \
            export_data["statistics"]["status_breakdown"].get(status, 0) + 1
        
        # 担当者別集計
        owner = task["owner"]["name"]
        export_data["statistics"]["owner_breakdown"][owner] = \
            export_data["statistics"]["owner_breakdown"].get(owner, 0) + 1
        
        # 優先度別集計
        priority = task["priority"]
        export_data["statistics"]["priority_breakdown"][priority] = \
            export_data["statistics"]["priority_breakdown"].get(priority, 0) + 1
    
    # Step 6: ファイルに出力
    # reports/exportsディレクトリを作成
    export_dir = "reports/exports"
    os.makedirs(export_dir, exist_ok=True)
    
    output_filename = f"project_tasks_tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_filepath = os.path.join(export_dir, output_filename)
    
    print(f"\n💾 ファイル出力中: {output_filepath}")
    
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ ファイル出力完了: {output_filepath}")
        
        # ファイルサイズを表示
        file_size = os.path.getsize(output_filepath)
        print(f"   ファイルサイズ: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
    except Exception as e:
        print(f"❌ ファイル出力失敗: {e}")
        return
    
    # Step 7: サマリー表示
    print("\n" + "=" * 70)
    print("📊 エクスポートサマリー")
    print("=" * 70)
    print(f"総タスク数: {len(detailed_tasks)}個")
    
    print("\nステータス別タスク数:")
    for status, count in sorted(export_data["statistics"]["status_breakdown"].items()):
        print(f"  • {status}: {count}個")
    
    print("\n担当者別タスク数:")
    owner_stats = export_data["statistics"]["owner_breakdown"]
    for owner, count in sorted(owner_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  • {owner}: {count}個")
    
    if len(owner_stats) > 10:
        print(f"  ... 他 {len(owner_stats) - 10} 名")
    
    print("\n優先度別タスク数:")
    for priority, count in sorted(export_data["statistics"]["priority_breakdown"].items()):
        print(f"  • {priority}: {count}個")
    
    print(f"\n✅ エクスポート完了: {output_filepath}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(export_task_details()) 