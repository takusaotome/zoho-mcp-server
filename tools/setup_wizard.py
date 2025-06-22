#!/usr/bin/env python3
"""
Zoho MCP Server Setup Wizard

このツールは初回セットアップを自動化します。
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from dotenv import load_dotenv

def print_header():
    print("🧙‍♂️ Zoho MCP Server セットアップウィザード")
    print("=" * 60)
    print("このツールがセットアップを自動化します！")
    print("=" * 60)

def check_prerequisites():
    """前提条件をチェック"""
    print("\n📋 前提条件チェック中...")
    
    # Python バージョンチェック
    python_version = sys.version_info
    if python_version < (3, 8):
        print("❌ Python 3.8以上が必要です")
        return False
    print(f"✅ Python {python_version.major}.{python_version.minor}")
    
    # Redis チェック
    try:
        result = subprocess.run(['redis-cli', 'ping'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'PONG' in result.stdout:
            print("✅ Redis サーバー稼働中")
        else:
            print("⚠️  Redis サーバーが応答しません")
            print("   以下のコマンドでRedisを起動してください:")
            print("   brew services start redis  # macOS")
            print("   sudo systemctl start redis  # Linux")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("⚠️  Redis がインストールされていません")
        print("   インストール方法: brew install redis")
    
    return True

def setup_env_file():
    """環境ファイルをセットアップ"""
    print("\n🔧 環境ファイルセットアップ中...")
    
    env_path = Path(".env")
    env_example_path = Path("config/env.example")
    
    if not env_path.exists():
        if env_example_path.exists():
            import shutil
            shutil.copy2(env_example_path, env_path)
            print("✅ .envファイルを作成しました")
        else:
            print("❌ config/env.exampleが見つかりません")
            return False
    else:
        print("✅ .envファイルが既に存在します")
    
    return True

def generate_jwt_secret():
    """JWT Secretを生成"""
    print("\n🔐 JWT Secret生成中...")
    
    try:
        # JWT Secret生成ツールを実行
        result = subprocess.run([
            sys.executable, 'tools/generate_jwt_secret.py', '--auto-save'
        ], capture_output=True, text=True, input='y\n')
        
        if result.returncode == 0:
            print("✅ JWT Secret生成完了")
            return True
        else:
            print(f"❌ JWT Secret生成失敗: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ JWT Secret生成エラー: {e}")
        return False

def collect_zoho_credentials():
    """Zoho認証情報を収集"""
    print("\n🔐 Zoho認証情報の設定")
    print("-" * 40)
    
    print("Zoho API Consoleから以下の情報を取得してください:")
    print("URL: https://api-console.zoho.com")
    print()
    
    client_id = input("ZOHO_CLIENT_ID: ").strip()
    client_secret = input("ZOHO_CLIENT_SECRET: ").strip()
    
    if not client_id or not client_secret:
        print("❌ Client IDとClient Secretは必須です")
        return None
    
    return {
        'ZOHO_CLIENT_ID': client_id,
        'ZOHO_CLIENT_SECRET': client_secret
    }

def update_env_file(credentials):
    """環境ファイルを更新"""
    print("\n📝 .envファイル更新中...")
    
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .envファイルが見つかりません")
        return False
    
    # 既存の.envファイルを読み込み
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 認証情報を更新
    for i, line in enumerate(lines):
        for key, value in credentials.items():
            if line.strip().startswith(f'{key}='):
                lines[i] = f"{key}={value}\n"
                break
    
    # ファイルに書き戻し
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("✅ 認証情報を更新しました")
    return True

def run_oauth_setup():
    """OAuth認証セットアップ"""
    print("\n🌐 OAuth認証セットアップ")
    print("-" * 40)
    
    print("MCPサーバーを起動してOAuth認証を行います...")
    
    # サーバー起動確認
    try:
        import httpx
        response = httpx.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ MCPサーバーが稼働中です")
        else:
            print("⚠️  MCPサーバーを手動で起動してください:")
            print("   uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload")
            input("サーバー起動後、Enterを押してください...")
    except:
        print("⚠️  MCPサーバーを手動で起動してください:")
        print("   uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload")
        input("サーバー起動後、Enterを押してください...")
    
    # OAuth認証URL生成
    try:
        print("\nOAuth認証URL生成中...")
        result = subprocess.run([
            sys.executable, 'tools/generate_zoho_auth_url.py'
        ], input='1\ny\n', text=True, capture_output=True)
        
        if result.returncode == 0:
            print("✅ OAuth認証URL生成完了")
            print("ブラウザで認証を完了してください")
            input("認証完了後、Enterを押してください...")
            return True
        else:
            print(f"❌ OAuth認証URL生成失敗: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ OAuth認証エラー: {e}")
        return False

def get_project_info():
    """プロジェクト情報を取得"""
    print("\n📊 プロジェクト情報取得中...")
    
    try:
        result = subprocess.run([
            sys.executable, 'tools/get_real_portal_and_projects.py'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ プロジェクト情報取得完了")
            print(result.stdout)
            
            # ユーザーにプロジェクトIDの入力を求める
            print("\n上記のプロジェクト一覧から使用するプロジェクトを選択してください:")
            portal_id = input("Portal ID: ").strip()
            project_id = input("Project ID: ").strip()
            
            if portal_id and project_id:
                return {
                    'ZOHO_PORTAL_ID': portal_id,
                    'TARGET_PROJECT_ID': project_id
                }
        else:
            print("❌ プロジェクト情報取得失敗")
            print("手動で設定してください:")
            portal_id = input("Portal ID: ").strip()
            project_id = input("Project ID: ").strip()
            
            if portal_id and project_id:
                return {
                    'ZOHO_PORTAL_ID': portal_id,
                    'TARGET_PROJECT_ID': project_id
                }
    except Exception as e:
        print(f"❌ プロジェクト情報取得エラー: {e}")
    
    return None

def final_test():
    """最終テスト"""
    print("\n🧪 最終テスト実行中...")
    
    try:
        result = subprocess.run([
            sys.executable, 'tools/get_project_tasks.py'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ 最終テスト成功！")
            print("セットアップが完了しました！")
            return True
        else:
            print("❌ 最終テスト失敗")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ 最終テストエラー: {e}")
        return False

def main():
    print_header()
    
    # Step 1: 前提条件チェック
    if not check_prerequisites():
        print("\n❌ 前提条件が満たされていません")
        sys.exit(1)
    
    # Step 2: 環境ファイルセットアップ
    if not setup_env_file():
        print("\n❌ 環境ファイルセットアップ失敗")
        sys.exit(1)
    
    # Step 3: JWT Secret生成
    if not generate_jwt_secret():
        print("\n❌ JWT Secret生成失敗")
        sys.exit(1)
    
    # Step 4: Zoho認証情報収集
    credentials = collect_zoho_credentials()
    if not credentials:
        print("\n❌ Zoho認証情報の収集失敗")
        sys.exit(1)
    
    # Step 5: 環境ファイル更新
    if not update_env_file(credentials):
        print("\n❌ 環境ファイル更新失敗")
        sys.exit(1)
    
    # Step 6: OAuth認証セットアップ
    if not run_oauth_setup():
        print("\n❌ OAuth認証セットアップ失敗")
        sys.exit(1)
    
    # Step 7: プロジェクト情報取得
    project_info = get_project_info()
    if project_info:
        if not update_env_file(project_info):
            print("\n❌ プロジェクト情報更新失敗")
            sys.exit(1)
    
    # Step 8: 最終テスト
    if not final_test():
        print("\n⚠️  最終テストに失敗しましたが、手動で確認してください")
    
    print("\n" + "=" * 60)
    print("🎉 セットアップウィザード完了！")
    print("=" * 60)
    print("次の手順:")
    print("1. MCPサーバーを起動: uvicorn server.main:app --reload")
    print("2. テスト実行: python tools/get_project_tasks.py")
    print("3. 詳細は README.md を参照")

if __name__ == "__main__":
    main() 