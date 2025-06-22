#!/usr/bin/env python3
"""
JWT Secret Generator

This tool generates a secure JWT secret key for the Zoho MCP Server.
"""

import secrets
import string
import sys
import argparse
from pathlib import Path

def generate_jwt_secret(length: int = 64) -> str:
    """Generate a secure JWT secret key."""
    # Use a mix of letters, digits, and some safe symbols
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def update_env_file(jwt_secret: str, env_path: Path = Path(".env")) -> bool:
    """Update .env file with new JWT_SECRET."""
    try:
        if not env_path.exists():
            print(f"❌ {env_path} ファイルが見つかりません。")
            return False
        
        # Create backup first
        backup_path = env_path.with_suffix('.env.backup')
        import shutil
        shutil.copy2(env_path, backup_path)
        print(f"📦 バックアップを作成しました: {backup_path}")
        
        # Read existing .env
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Check if JWT_SECRET already exists
        jwt_secret_exists = False
        jwt_secret_line = None
        for i, line in enumerate(lines):
            if line.strip().startswith('JWT_SECRET='):
                jwt_secret_line = line.strip()
                lines[i] = f"JWT_SECRET={jwt_secret}\n"
                jwt_secret_exists = True
                break
        
        if jwt_secret_exists and jwt_secret_line:
            print(f"🔄 既存のJWT_SECRETを更新します")
            print(f"   旧: {jwt_secret_line[:20]}...")
            print(f"   新: JWT_SECRET={jwt_secret[:20]}...")
        
        # Add if not exists
        if not jwt_secret_exists:
            lines.append(f"\n# JWT Secret for authentication\nJWT_SECRET={jwt_secret}\n")
            print("➕ 新しいJWT_SECRETを追加しました")
        
        # Write back
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return True
        
    except Exception as e:
        print(f"❌ .envファイルの更新に失敗しました: {e}")
        # Restore backup if exists
        backup_path = env_path.with_suffix('.env.backup')
        if backup_path.exists():
            import shutil
            shutil.copy2(backup_path, env_path)
            print(f"🔄 バックアップから復元しました")
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate JWT Secret for Zoho MCP Server")
    parser.add_argument("--length", "-l", type=int, default=64, choices=[32, 64, 128],
                       help="Secret length (32, 64, or 128 characters)")
    parser.add_argument("--auto-save", "-s", action="store_true",
                       help="Automatically save to .env file without prompting")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Quiet mode - only output the secret")
    
    args = parser.parse_args()
    
    if not args.quiet:
        print("🔐 JWT Secret Generator for Zoho MCP Server")
        print("=" * 50)
    
    # Generate secret
    jwt_secret = generate_jwt_secret(args.length)
    
    if args.quiet:
        print(jwt_secret)
        return
    
    # Get description for length
    length_descriptions = {
        32: "最小推奨長",
        64: "推奨長（デフォルト）", 
        128: "高セキュリティ"
    }
    description = length_descriptions.get(args.length, "カスタム長")
    
    print(f"\n✅ JWT Secret生成完了！ ({args.length}文字 - {description})")
    print("=" * 50)
    print(f"JWT_SECRET={jwt_secret}")
    print("=" * 50)
    
    # Handle auto-save or prompt
    env_path = Path(".env")
    should_save = False
    
    if env_path.exists():
        if args.auto_save:
            # Even with auto-save, confirm if file exists
            print(f"\n⚠️  既存の{env_path}ファイルが見つかりました。")
            save_choice = input("💾 JWT_SECRETを更新しますか？ (バックアップを作成します) (y/N): ").strip().lower()
            should_save = save_choice in ['y', 'yes']
        else:
            save_choice = input("\n💾 .envファイルに自動追加しますか？ (バックアップを作成します) (y/N): ").strip().lower()
            should_save = save_choice in ['y', 'yes']
    elif not env_path.exists():
        print("\n💡 .envファイルが見つかりません。")
        print("config/env.exampleをコピーして.envファイルを作成し、")
        print("上記のJWT_SECRETを追加してください。")
        return
    
    if should_save:
        if update_env_file(jwt_secret, env_path):
            print("✅ .envファイルに保存しました！")
        else:
            print("手動で上記のJWT_SECRETを.envファイルに追加してください。")
    
    if not args.auto_save:
        print("\n📝 使用方法:")
        print("1. 上記のJWT_SECRETを.envファイルに追加")
        print("2. サーバーを再起動")
        print("3. 完了！")
        
        print("\n🔒 セキュリティ注意事項:")
        print("- このシークレットは絶対に他人と共有しないでください")
        print("- GitHubなどの公開リポジトリにコミットしないでください")
        print("- 定期的に更新することを推奨します")

if __name__ == "__main__":
    main() 