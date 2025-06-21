# Zoho MCP Server

Model Context Protocol (MCP) server for Zoho Projects and WorkDrive integration.

## Overview

This server enables natural language interaction with Zoho applications through MCP-compatible clients like Cursor IDE and Claude. It provides secure access to Zoho Projects tasks and WorkDrive files via JSON-RPC protocol.

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

## Quick Start

### Prerequisites
- Python 3.12+
- Redis server
- Zoho OAuth credentials

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd zoho-mcp-server
```

2. Install dependencies:
```bash
pip install -r requirements-dev.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. Run the server:
```bash
uvicorn server.main:app --reload
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ZOHO_CLIENT_ID` | Zoho OAuth Client ID | Yes |
| `ZOHO_CLIENT_SECRET` | Zoho OAuth Client Secret | Yes |
| `ZOHO_REFRESH_TOKEN` | Zoho OAuth Refresh Token | Yes |
| `JWT_SECRET` | JWT signing secret (32+ chars) | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `ALLOWED_IPS` | Comma-separated IP allowlist | No |

### Zoho OAuth Setup

1. Create a Zoho application in [Zoho Developer Console](https://api-console.zoho.com)
2. Configure OAuth scopes:
   - `ZohoProjects.tasks.ALL`
   - `ZohoProjects.files.READ`
   - `ZohoWorkDrive.files.ALL`
3. Generate refresh token using server-based OAuth flow

## API Endpoints

### MCP Protocol
- `POST /mcp` - JSON-RPC 2.0 endpoint
- `GET /manifest.json` - Tool manifest

### Health & Monitoring  
- `GET /health` - Health check
- `POST /webhook/task-updated` - Webhook receiver

## Available Tools

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

## Usage Examples

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

## Development

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

## Deployment

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

## Troubleshooting

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