#!/usr/bin/env python3
"""JSONファイルからMarkdown形式のタスクレポートを生成"""

import json
import os
from datetime import datetime


def load_task_data(json_filename):
    """JSONファイルからタスクデータを読み込み"""
    try:
        with open(json_filename, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ JSONファイル読み込み失敗: {e}")
        return None

def generate_markdown_report(data, output_filename):
    """Markdownレポートを生成"""

    export_info = data.get("export_info", {})
    project_summary = data.get("project_summary", {})
    tasks = data.get("tasks", [])
    statistics = data.get("statistics", {})

    # Markdownコンテンツを構築
    md_content = []

    # ヘッダー
    md_content.append("# プロジェクトタスクレポート")
    md_content.append("")
    md_content.append(f"**生成日時**: {export_info.get('export_date', 'N/A')}")
    md_content.append(f"**プロジェクトID**: {export_info.get('project_id', 'N/A')}")
    md_content.append(f"**総タスク数**: {export_info.get('total_tasks', 0)}個")
    md_content.append("")

    # 目次
    md_content.append("## 📋 目次")
    md_content.append("")
    md_content.append("1. [プロジェクト概要](#プロジェクト概要)")
    md_content.append("2. [統計情報](#統計情報)")
    md_content.append("3. [タスク一覧](#タスク一覧)")
    md_content.append("   - [オープンタスク](#オープンタスク)")
    md_content.append("   - [進行中タスク](#進行中タスク)")
    md_content.append("   - [完了タスク](#完了タスク)")
    md_content.append("")

    # プロジェクト概要
    md_content.append("## 📊 プロジェクト概要")
    md_content.append("")
    md_content.append("| 項目 | 値 |")
    md_content.append("|------|-----|")
    md_content.append(f"| プロジェクト名 | {project_summary.get('project_name', 'N/A')} |")
    md_content.append(f"| 総タスク数 | {project_summary.get('total_tasks', 0)}個 |")
    md_content.append(f"| 完了率 | {project_summary.get('completion_rate', 0)}% |")
    md_content.append(f"| オープンタスク | {project_summary.get('open_count', 0)}個 |")
    md_content.append(f"| 進行中タスク | {project_summary.get('closed_count', 0)}個 |")
    md_content.append(f"| 完了タスク | {project_summary.get('overdue_count', 0)}個 |")
    md_content.append("")

    # 統計情報
    md_content.append("## 📈 統計情報")
    md_content.append("")

    # ステータス別統計
    status_stats = statistics.get("status_breakdown", {})
    if status_stats:
        md_content.append("### ステータス別タスク数")
        md_content.append("")
        md_content.append("| ステータス | タスク数 | 割合 |")
        md_content.append("|-----------|---------|------|")
        total_tasks = sum(status_stats.values())
        for status, count in sorted(status_stats.items()):
            percentage = (count / total_tasks * 100) if total_tasks > 0 else 0
            md_content.append(f"| {status} | {count}個 | {percentage:.1f}% |")
        md_content.append("")

    # 担当者別統計
    owner_stats = statistics.get("owner_breakdown", {})
    if owner_stats:
        md_content.append("### 担当者別タスク数")
        md_content.append("")
        md_content.append("| 担当者 | タスク数 |")
        md_content.append("|--------|---------|")
        for owner, count in sorted(owner_stats.items(), key=lambda x: x[1], reverse=True):
            md_content.append(f"| {owner} | {count}個 |")
        md_content.append("")

    # 優先度別統計
    priority_stats = statistics.get("priority_breakdown", {})
    if priority_stats:
        md_content.append("### 優先度別タスク数")
        md_content.append("")
        md_content.append("| 優先度 | タスク数 |")
        md_content.append("|--------|---------|")
        for priority, count in sorted(priority_stats.items()):
            md_content.append(f"| {priority} | {count}個 |")
        md_content.append("")

    # ステータス別タスク一覧
    md_content.append("## 📝 タスク一覧")
    md_content.append("")

    # ステータス別にタスクを分類
    tasks_by_status = {}
    for task in tasks:
        status = task["status"]["name"]
        if status not in tasks_by_status:
            tasks_by_status[status] = []
        tasks_by_status[status].append(task)

    # 各ステータスのタスクを表示
    status_icons = {
        "Open": "🔓",
        "In Progress": "🔄",
        "Closed": "✅"
    }

    for status in ["Open", "In Progress", "Closed"]:
        if status in tasks_by_status:
            icon = status_icons.get(status, "📋")
            md_content.append(f"### {icon} {status}タスク")
            md_content.append("")

            status_tasks = tasks_by_status[status]
            md_content.append("| # | タスク名 | 担当者 | 優先度 | 完了率 |")
            md_content.append("|---|---------|--------|--------|--------|")

            for i, task in enumerate(status_tasks, 1):
                task_name = task["name"]
                owner = task["owner"]["name"]
                priority = task["priority"]
                percent = task["percent_complete"]

                # タスク名が長い場合は省略
                if len(task_name) > 50:
                    task_name = task_name[:47] + "..."

                md_content.append(f"| {i} | {task_name} | {owner} | {priority} | {percent}% |")

            md_content.append("")

    # 詳細タスク情報
    md_content.append("## 📋 詳細タスク情報")
    md_content.append("")
    md_content.append("### 主要タスクの詳細")
    md_content.append("")

    # 進行中のタスクと重要そうなタスクを詳細表示
    important_tasks = []

    # 進行中のタスクを追加
    if "In Progress" in tasks_by_status:
        important_tasks.extend(tasks_by_status["In Progress"][:5])

    # オープンタスクも追加
    if "Open" in tasks_by_status:
        important_tasks.extend(tasks_by_status["Open"][:3])

    for task in important_tasks:
        md_content.append(f"#### {task['name']}")
        md_content.append("")
        md_content.append(f"- **ID**: {task['id']}")
        md_content.append(f"- **ステータス**: {task['status']['name']}")
        md_content.append(f"- **担当者**: {task['owner']['name']}")
        md_content.append(f"- **優先度**: {task['priority']}")
        md_content.append(f"- **完了率**: {task['percent_complete']}%")
        md_content.append(f"- **期限**: {task['due_date'] if task['due_date'] else '未設定'}")

        if task['description']:
            # HTMLタグを除去して説明を表示
            description = task['description'].replace('<div>', '').replace('</div>', '\n').replace('<br />', '\n')
            description = description.replace('<span style="', '').replace('</span>', '')
            # 簡単なHTMLタグ除去（完全ではないが読みやすくする）
            import re
            description = re.sub(r'<[^>]+>', '', description)
            description = description.strip()

            if description:
                md_content.append(f"- **説明**: {description[:200]}{'...' if len(description) > 200 else ''}")

        md_content.append("")

    # フッター
    md_content.append("---")
    md_content.append("")
    md_content.append(f"*このレポートは {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')} に生成されました*")
    md_content.append("")
    md_content.append("**生成元**: Zoho MCP Server")

    # ファイルに書き込み
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_content))
        return True
    except Exception as e:
        print(f"❌ Markdownファイル書き込み失敗: {e}")
        return False

def main():
    # データディレクトリを設定
    data_dir = os.getenv("DATA_DIR", "reports/exports")
    output_dir = os.getenv("OUTPUT_DIR", "reports")

    # ディレクトリを作成
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # 最新のJSONファイルを検索
    json_files = [f for f in os.listdir(data_dir) if f.startswith('project_tasks_tasks_') and f.endswith('.json')]

    if not json_files:
        print("❌ JSONファイルが見つかりません")
        return

    # 最新のファイルを選択
    latest_json = sorted(json_files)[-1]
    latest_json_path = os.path.join(data_dir, latest_json)
    print(f"📄 JSONファイル: {latest_json_path}")

    # データを読み込み
    data = load_task_data(latest_json_path)
    if not data:
        return

    # Markdownレポートを生成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = os.path.join(output_dir, f"project_tasks_report_{timestamp}.md")

    print(f"📝 Markdownレポート生成中: {output_filename}")

    if generate_markdown_report(data, output_filename):
        print(f"✅ Markdownレポート生成完了: {output_filename}")

        # ファイルサイズを表示
        file_size = os.path.getsize(output_filename)
        print(f"   ファイルサイズ: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    else:
        print("❌ Markdownレポート生成失敗")

if __name__ == "__main__":
    main()
