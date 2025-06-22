# Zoho MCP Server

Model Context Protocol (MCP) server for Zoho Projects and WorkDrive integration.

## 📖 Table of Contents

- [🚀 Quick Start Guide](#-quick-start-guide)
  - [📋 Prerequisites](#-prerequisites)
  - [🔧 Step 1: Installation](#-step-1-installation)
  - [🔐 Step 2: Zoho OAuth Setup](#-step-2-zoho-oauth-setup)
  - [⚙️ Step 3: Initial Setup Verification](#️-step-3-initial-setup-verification)
  - [🔍 Step 4: Find Your Portal & Project IDs](#-step-4-find-your-portal--project-ids)
  - [✅ Step 5: Final Testing](#-step-5-final-testing)
  - [🎯 Step 6: Start Using](#-step-6-start-using)
- [⚙️ Advanced Configuration](#️-advanced-configuration)
- [🛠 Available Tools](#-available-tools)
- [💻 Usage Examples](#-usage-examples)
- [🧪 Development](#-development)
- [🚀 Deployment](#-deployment)
- [🔍 Troubleshooting](#-troubleshooting)

## Overview

**⚡ 5分でZoho Projects APIを使い始められる！**

This server enables natural language interaction with Zoho applications through MCP-compatible clients like Cursor IDE and Claude. It provides secure access to Zoho Projects tasks and WorkDrive files via JSON-RPC protocol.

### ✨ Key Features
- **🎯 Easy Setup**: 5-minute OAuth setup with automatic token management
- **🔐 Secure**: JWT authentication, IP allowlisting, rate limiting  
- **🚀 Fast**: Redis caching, async processing
- **📊 Comprehensive**: Task management, file operations, project analytics
- **🤖 AI-Ready**: Perfect for Cursor IDE, Claude, and other MCP clients

### 🎬 What You Can Do
- 📝 **Create and manage tasks** with natural language
- 📊 **Generate project reports** and analytics
- 🔍 **Search across projects** and files
- 📁 **Upload/download files** to WorkDrive
- 🔔 **Real-time webhooks** for task updates

## Project Structure

```
zoho-mcp-server/
├── server/                 # Main application code
├── tests/                  # Test suites
├── docs/                   # Documentation & guides
│   ├── requirement/        # Requirements documentation
│   ├── plan/               # Project planning documents
│   ├── design/             # Design documents
│   └── guides/             # Setup guides & troubleshooting
├── tools/                  # Development & utility scripts
├── config/                 # Configuration files
├── reports/                # Generated reports & project data
└── temp/                   # Temporary files
```

### Directory Details

- **`server/`** - Main application code (handlers, auth, storage, etc.)
- **`tests/`** - Test suites (unit, integration, e2e, security)
- **`docs/`** - Documentation and guides
  - **`guides/`** - Setup guides and troubleshooting documentation
- **`tools/`** - Development tools, test scripts, and utilities
- **`config/`** - Configuration templates and settings
- **`reports/`** - Generated task reports, project data, and exports (gitignored)
- **`temp/`** - Temporary files (coverage reports, logs, etc.)

## Features

### Phase 1 (MVP)
- **Task Management**: Create, read, update tasks in Zoho Projects
- **Project Analytics**: Get completion rates and progress summaries  
- **File Operations**: Download and upload files in WorkDrive
- **Search**: Find files and tasks across projects
- **Webhooks**: Real-time notifications for task updates

### Security
- JWT authentication with IP allowlisting
- Rate limiting (100 req/min)
- CORS protection
- OAuth2 integration with Zoho

## 🚀 Quick Start Guide

> **⏱️ 所要時間: 約5分** | **💡 初回セットアップのみ必要**

### 🧙‍♂️ Option A: 自動セットアップ（推奨）

**最も簡単な方法！ウィザードが全て自動化します：**

```bash
# 1. 依存関係をインストール
pip install -r requirements-dev.txt

# 2. セットアップウィザードを実行
python tools/setup_wizard.py
```

ウィザードが以下を自動実行：
- ✅ 前提条件チェック（Python, Redis）
- ✅ .envファイル作成
- ✅ JWT_SECRET自動生成
- ✅ Zoho認証情報の設定
- ✅ OAuth認証フロー
- ✅ Portal ID・Project ID取得
- ✅ 最終テスト実行

**5分で完了！** 🎉

---

### 📖 Option B: 手動セットアップ

詳細を理解したい場合の手動セットアップ：

### 📋 Prerequisites
- **Python 3.12+** (with pip)
- **Redis server** (local or cloud)
- **Zoho account** (Projects and WorkDrive access)

### 🔧 Step 1: Installation

1. **Clone and setup**:
```bash
git clone <repository-url>
cd zoho-mcp-server
pip install -r requirements-dev.txt
```

2. **Start Redis** (if not running):
```bash
# macOS (Homebrew)
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis

# Windows (WSL recommended)
sudo service redis-server start
```

### 🔐 Step 2: Zoho OAuth Setup

**Choose one of the following methods:**

#### 🌟 Method A: Automatic Setup (Recommended)

1. **Create Zoho Application**:
   - Go to [Zoho API Console](https://api-console.zoho.com)
   - Click "ADD CLIENT" → "Server-based Applications"
   - Fill in:
     - **Client Name**: `MCP Server`
     - **Homepage URL**: `http://localhost:8000`
     - **Authorized Redirect URIs**: `http://localhost:8000/auth/callback`

2. **Configure Environment**:
```bash
cp config/env.example .env
```

3. **Edit `.env` file** with your Zoho credentials:
```bash
# Required: Copy from Zoho API Console
ZOHO_CLIENT_ID=1000.XXXXXXXXXXXXXXXXXX
ZOHO_CLIENT_SECRET=your_client_secret_here

# Required: Generate JWT Secret (see step 3.1 below)
JWT_SECRET=your_generated_jwt_secret_here

# Required: Your Portal ID (see step 5.2 below)
ZOHO_PORTAL_ID=your_portal_id

# Required: Default Project ID for testing (see step 5.3 below)
TARGET_PROJECT_ID=your_project_id_here

# Redis (default for local)
REDIS_URL=redis://localhost:6379/0
```

   **3.1. Generate JWT Secret** (簡単！):
   ```bash
   python tools/generate_jwt_secret.py
   ```
   - 自動で安全なJWT_SECRETを生成
   - .envファイルに自動追加オプション
   - ✅ 30秒で完了！

4. **Start the server**:
```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

5. **Run OAuth authentication** (automatic setup):
```bash
python tools/generate_zoho_auth_url.py
```
   - Select option **1** (推奨・自動設定)
   - Follow the browser authentication
   - ✅ **Done!** Refresh token is automatically saved

6. **Test your setup**:
```bash
# Quick verification
python tools/verify_setup.py

# Test API access (optional)
python tools/get_project_tasks_via_mcp.py
```
   - ✅ If successful, you'll see your projects and tasks!

#### 📖 Method B: Manual Setup (Self Client)

For simpler setup without server configuration:

1. **Use Self Client**:
   - Go to [Zoho API Console](https://api-console.zoho.com)
   - Click "Self Client" tab
   - Select scopes: `ZohoProjects.projects.read`, `ZohoProjects.tasks.all`
   - Generate code (10-minute expiry)

2. **Convert to Refresh Token**:
```bash
python tools/exchange_auth_code.py "YOUR_GENERATED_CODE"
```

### ⚙️ Step 3: Initial Setup Verification

1. **Basic setup verification**:
```bash
python tools/verify_setup.py
```

### 🔍 Step 4: Find Your Portal & Project IDs

2. **Get your Portal ID and available projects**:
```bash
python tools/get_real_portal_and_projects.py
```
   - 📋 利用可能なプロジェクト一覧が表示されます
   - 📝 Portal IDとProject IDをメモしてください

3. **Update `.env` file with your IDs**:
```bash
# .envファイルを編集して以下を更新:
ZOHO_PORTAL_ID=your_actual_portal_id
TARGET_PROJECT_ID=your_actual_project_id
```

### ✅ Step 5: Final Testing

4. **Complete API test**:
```bash
python tools/get_project_tasks_via_mcp.py
```
   - ✅ 成功すると、プロジェクトのタスク一覧が表示されます

5. **Alternative: Test with specific project**:
```bash
python tools/get_project_tasks_via_mcp.py --project-id YOUR_PROJECT_ID
```

### 🎯 Step 6: Start Using

Your MCP server is now ready! The server provides:

- **MCP Endpoint**: `http://localhost:8000/mcp`
- **Health Check**: `http://localhost:8000/health`
- **API Docs**: `http://localhost:8000/docs` (debug mode)

### 🔧 Quick Troubleshooting

**❌ "Invalid OAuth Scope" error**
```bash
# Remove problematic scope and retry
python tools/generate_zoho_auth_url.py
# Select option 1 and re-authenticate
```

**❌ "Invalid Redirect Uri" error**
```bash
# Check Zoho API Console settings:
# Redirect URI must be: http://localhost:8000/auth/callback
```

**❌ Redis connection error**
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG
```

**❌ JWT_SECRET missing or invalid**
```bash
# Generate new JWT secret
python tools/generate_jwt_secret.py
# Select option to auto-add to .env file
```

**❌ "JWT_SECRET too short" error**
```bash
# JWT_SECRET must be at least 32 characters
# Use the generator tool for secure secret:
python tools/generate_jwt_secret.py
```

For detailed troubleshooting, see: [`docs/guides/`](docs/guides/)

## ⚙️ Advanced Configuration

### Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ZOHO_CLIENT_ID` | Zoho OAuth Client ID | ✅ Yes | - |
| `ZOHO_CLIENT_SECRET` | Zoho OAuth Client Secret | ✅ Yes | - |
| `ZOHO_REFRESH_TOKEN` | OAuth Refresh Token (auto-generated) | ✅ Yes | - |
| `ZOHO_PORTAL_ID` | Your Zoho Portal ID | ⚠️ Recommended | - |
| `JWT_SECRET` | JWT signing secret (use `tools/generate_jwt_secret.py`) | ✅ Yes | - |
| `REDIS_URL` | Redis connection URL | ✅ Yes | `redis://localhost:6379/0` |
| `ALLOWED_IPS` | IP allowlist (comma-separated) | ❌ No | `127.0.0.1,::1` |
| `RATE_LIMIT_PER_MINUTE` | Request rate limit | ❌ No | `100` |
| `DEBUG` | Enable debug mode | ❌ No | `false` |

### Required Zoho Scopes

The following scopes are automatically configured:
- **`ZohoProjects.projects.read`** - Read project information
- **`ZohoProjects.tasks.all`** - Full task management access

### Additional Setup Guides

- 📖 **Detailed OAuth Guide**: [`docs/guides/zoho_oauth_setup_guide.md`](docs/guides/zoho_oauth_setup_guide.md)
- 🔧 **Self Client Method**: [`docs/guides/zoho_self_client_setup.md`](docs/guides/zoho_self_client_setup.md)
- 🔍 **Troubleshooting**: [`docs/guides/fix_400_error_guide.md`](docs/guides/fix_400_error_guide.md)

## API Endpoints

### MCP Protocol
- `POST /mcp` - JSON-RPC 2.0 endpoint
- `GET /manifest.json` - Tool manifest

### Health & Monitoring  
- `GET /health` - Health check
- `POST /webhook/task-updated` - Webhook receiver

## 🛠 Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `listTasks` | List project tasks | `project_id`, `status?` |
| `createTask` | Create new task | `project_id`, `name`, `owner?`, `due_date?` |
| `updateTask` | Update existing task | `task_id`, `status?`, `due_date?`, `owner?` |
| `getTaskDetail` | Get task details | `task_id` |
| `getProjectSummary` | Get project metrics | `project_id`, `period?` |
| `downloadFile` | Download WorkDrive file | `file_id` |
| `uploadReviewSheet` | Upload review file | `project_id`, `folder_id`, `name`, `content_base64` |
| `searchFiles` | Search files | `query`, `folder_id?` |

## 💻 Usage Examples

### List Tasks
```json
{
  "jsonrpc": "2.0",
  "method": "callTool",
  "params": {
    "name": "listTasks",
    "arguments": {
      "project_id": "123456789",
      "status": "open"
    }
  },
  "id": "1"
}
```

### Create Task
```json
{
  "jsonrpc": "2.0", 
  "method": "callTool",
  "params": {
    "name": "createTask",
    "arguments": {
      "project_id": "123456789",
      "name": "Review API documentation",
      "owner": "developer@company.com",
      "due_date": "2025-07-01"
    }
  },
  "id": "2"
}
```

## 🧪 Development

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=server --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### Code Quality
```bash
# Linting
ruff check .
ruff format .

# Type checking  
mypy server/

# Security scan
bandit -r server/
safety check
```

### Pre-commit Hooks
```bash
pre-commit install
pre-commit run --all-files
```

## 🚀 Deployment

### Render Platform
This project is configured for deployment on Render using `render.yaml`.

1. Connect your GitHub repository to Render
2. Configure environment variables in Render dashboard
3. Deploy automatically on push to main branch

### Docker
```bash
# Build image
docker build -t zoho-mcp-server .

# Run container
docker run -p 8000:8000 --env-file .env zoho-mcp-server
```

### Environment-specific Configuration

#### Production
- Use Render Starter plan or higher
- Configure Redis Add-on
- Set up monitoring and alerts
- Enable auto-scaling

#### Development  
- Use local Redis instance
- Enable debug mode
- Use development Zoho credentials

## Monitoring

### Health Checks
- `/health` endpoint for basic health status
- Redis connectivity check
- Zoho API accessibility test

### Metrics
- Request rate and response times
- Error rates by endpoint
- Token refresh frequency
- Cache hit rates

### Logging
- Structured JSON logging
- Request/response correlation IDs
- Security event tracking
- Performance metrics

## Security

### Authentication Flow
1. Client requests JWT token (external process)
2. Include `Authorization: Bearer <token>` header
3. Server validates JWT signature and expiration
4. IP address checked against allowlist
5. Rate limiting applied per client

### OAuth Token Management
- Automatic token refresh before expiration
- Secure storage in Redis with TTL
- Token revocation support
- Refresh token backup in secrets manager

## 🔍 Troubleshooting

### Common Issues

**401 Unauthorized**
- Check JWT token validity and expiration
- Verify JWT_SECRET matches token issuer
- Confirm IP address is in allowlist

**429 Rate Limited**  
- Reduce request frequency
- Check rate limit headers
- Consider request batching

**Zoho API Errors**
- Verify OAuth scopes and permissions
- Check refresh token validity
- Monitor Zoho API rate limits

**Redis Connection Issues**
- Verify Redis URL and credentials
- Check network connectivity
- Monitor Redis memory usage

### Debug Mode
Set `DEBUG=true` in environment to enable:
- Detailed error messages
- API request/response logging  
- Interactive API documentation at `/docs`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks
5. Submit pull request

### Development Workflow
- Follow conventional commit messages
- Maintain 90%+ test coverage
- Update documentation for API changes
- Security scan all dependencies

## License

MIT License - see LICENSE file for details.

## Support

- GitHub Issues for bug reports
- Documentation in `docs/` directory
- API reference at `/docs` endpoint (debug mode)