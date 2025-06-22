# Zoho MCP Server テスト戦略書

> **作成日**: 2025-06-21  
> **バージョン**: v1.0

## 1. テスト方針

### 1.1 テストレベル
1. **ユニットテスト** - 個別の関数・クラスの動作検証
2. **統合テスト** - モジュール間の連携検証
3. **E2Eテスト** - システム全体の動作検証
4. **セキュリティテスト** - 脆弱性の検出と対策

### 1.2 テスト自動化
- 全てのテストをCI/CDパイプラインで自動実行
- プルリクエスト時に必須チェック
- デプロイ前の回帰テスト実行

## 2. ユニットテスト詳細

### 2.1 テスト対象モジュール

#### MCP Core (`tests/test_mcp_core.py`)
```python
# テストケース例
class TestMCPCore:
    def test_handshake_success(self):
        """MCP handshakeが正常に完了すること"""
        
    def test_invalid_json_rpc_format(self):
        """不正なJSON-RPC形式でエラーが返ること"""
        
    def test_method_not_found(self):
        """存在しないメソッドで適切なエラーが返ること"""
```

#### 認証 (`tests/test_auth.py`)
```python
class TestJWTAuth:
    def test_valid_token_authentication(self):
        """有効なJWTトークンで認証が成功すること"""
        
    def test_expired_token_rejection(self):
        """期限切れトークンが拒否されること"""
        
    def test_invalid_signature_rejection(self):
        """不正な署名のトークンが拒否されること"""

class TestIPAllowlist:
    def test_allowed_ip_access(self):
        """許可されたIPからのアクセスが通ること"""
        
    def test_blocked_ip_rejection(self):
        """ブロックされたIPが拒否されること"""
```

#### Zoho OAuth (`tests/test_zoho_oauth.py`)
```python
class TestZohoOAuth:
    def test_access_token_generation(self):
        """リフレッシュトークンからアクセストークンが生成できること"""
        
    def test_token_refresh_on_expiry(self):
        """トークン期限切れ時に自動更新されること"""
        
    def test_token_caching(self):
        """トークンがRedisにキャッシュされること"""
```

### 2.2 モックとフィクスチャ

```python
# conftest.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_zoho_api():
    """Zoho APIのモック"""
    mock = Mock()
    mock.get_tasks.return_value = [
        {"id": "1", "name": "Test Task", "status": "open"}
    ]
    return mock

@pytest.fixture
def redis_client():
    """Redisクライアントのモック"""
    import fakeredis
    return fakeredis.FakeRedis()

@pytest.fixture
def auth_headers():
    """認証済みヘッダー"""
    return {"Authorization": "Bearer test-token"}
```

## 3. 統合テスト詳細

### 3.1 API統合テスト (`tests/integration/test_api_integration.py`)

```python
class TestTaskAPIIntegration:
    @pytest.mark.asyncio
    async def test_list_tasks_integration(self, client, mock_zoho_api):
        """listTasks APIの統合テスト"""
        response = await client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {"project_id": "123", "status": "open"}
            },
            "id": 1
        })
        assert response.status_code == 200
        assert "result" in response.json()
```

### 3.2 エラーハンドリングテスト

```python
class TestErrorHandling:
    async def test_zoho_api_timeout_handling(self):
        """Zoho APIタイムアウト時のエラーハンドリング"""
        
    async def test_rate_limit_exceeded_handling(self):
        """レート制限超過時の適切なエラーレスポンス"""
        
    async def test_invalid_project_id_handling(self):
        """無効なプロジェクトIDのエラーハンドリング"""
```

## 4. E2Eテストシナリオ

### 4.1 基本シナリオ (`tests/e2e/test_basic_scenarios.py`)

```gherkin
# features/task_management.feature
Feature: タスク管理機能

  Scenario: 新規タスクの作成と確認
    Given 認証済みのMCPクライアント
    When "プロジェクト123に'テストタスク'を作成"というリクエストを送信
    Then タスクが正常に作成される
    And タスクIDが返される
    And listTasksでタスクが確認できる

  Scenario: タスクステータスの更新
    Given 既存のタスク
    When タスクのステータスを"closed"に更新
    Then タスクのステータスが更新される
    And getProjectSummaryで完了率が反映される
```

### 4.2 パフォーマンステスト (`tests/e2e/test_performance.py`)

```python
# locustfile.py
from locust import HttpUser, task, between

class MCPUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def list_tasks(self):
        self.client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {"project_id": "123"}
            },
            "id": 1
        })
    
    @task
    def create_task(self):
        self.client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": "123",
                    "name": f"Load test task {self.environment.runner.user_count}"
                }
            },
            "id": 1
        })
```

## 5. セキュリティテスト

### 5.1 静的セキュリティ解析

```bash
# セキュリティスキャンスクリプト
#!/bin/bash

echo "Running security scans..."

# Banditでコードの脆弱性スキャン
bandit -r server/ -f json -o security_report_bandit.json

# Safetyで依存関係の脆弱性チェック
safety check --json > security_report_safety.json

# OWASPでより詳細な依存関係チェック
dependency-check --project "Zoho MCP Server" \
  --scan requirements.txt \
  --format JSON \
  --out security_report_owasp.json
```

### 5.2 動的セキュリティテスト

```python
# tests/security/test_security.py
class TestSecurityVulnerabilities:
    def test_sql_injection_prevention(self):
        """SQLインジェクション攻撃が防がれること"""
        
    def test_xss_prevention(self):
        """XSS攻撃が防がれること"""
        
    def test_jwt_algorithm_confusion(self):
        """JWTアルゴリズム混同攻撃が防がれること"""
        
    def test_rate_limiting_enforcement(self):
        """レート制限が正しく機能すること"""
```

## 6. テスト実行とレポート

### 6.1 テスト実行コマンド

```bash
# ユニットテスト実行
pytest tests/unit/ -v --cov=server --cov-report=html

# 統合テスト実行
pytest tests/integration/ -v --cov=server --cov-append

# E2Eテスト実行
pytest tests/e2e/ -v --bdd

# 全テスト実行
pytest -v --cov=server --cov-report=html --cov-report=term

# パフォーマンステスト
locust -f tests/e2e/locustfile.py --headless -u 100 -r 10 -t 5m
```

### 6.2 テストレポート形式

#### カバレッジレポート
```
Name                     Stmts   Miss  Cover
--------------------------------------------
server/__init__.py           2      0   100%
server/main.py              45      2    96%
server/auth/jwt.py          38      1    97%
server/handlers/tasks.py    89      5    94%
--------------------------------------------
TOTAL                      589     32    95%
```

#### セキュリティレポート例
```json
{
  "results": [
    {
      "severity": "LOW",
      "confidence": "HIGH",
      "issue_text": "Consider using secrets.compare_digest()",
      "line_number": 45,
      "filename": "server/auth/jwt.py"
    }
  ]
}
```

## 7. CI/CDパイプライン統合

### 7.1 GitHub Actions設定

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
          
      - name: Run linting
        run: |
          ruff check .
          mypy server/
          
      - name: Run tests
        run: |
          pytest -v --cov=server --cov-report=xml
          
      - name: Run security scans
        run: |
          bandit -r server/
          safety check
          
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 8. テストデータ管理

### 8.1 テストフィクスチャ

```python
# tests/fixtures/test_data.py
TEST_TASKS = [
    {
        "id": "task_001",
        "name": "Unit test task",
        "status": "open",
        "owner": "test_user",
        "due_date": "2025-07-01"
    },
    {
        "id": "task_002",
        "name": "Integration test task",
        "status": "closed",
        "owner": "test_user2",
        "due_date": "2025-06-15"
    }
]

TEST_PROJECT = {
    "id": "proj_test_001",
    "name": "Test Project",
    "description": "Project for automated testing"
}
```

### 8.2 モックレスポンス

```python
# tests/mocks/zoho_responses.py
MOCK_ZOHO_RESPONSES = {
    "list_tasks_success": {
        "tasks": [
            {"id": "1", "name": "Task 1", "status": "open"},
            {"id": "2", "name": "Task 2", "status": "closed"}
        ]
    },
    "create_task_success": {
        "task": {
            "id": "new_task_123",
            "name": "New Task",
            "created_time": "2025-06-21T10:00:00Z"
        }
    },
    "rate_limit_error": {
        "error": {
            "code": "429",
            "message": "Rate limit exceeded"
        }
    }
}
```

## 9. テスト環境

### 9.1 ローカルテスト環境
- Python 3.12
- Redis (Docker container)
- PostgreSQL (テスト用、必要な場合)

### 9.2 CI環境
- GitHub Actions Ubuntu latest
- Redis service container
- テスト用Zoho APIモックサーバー

### 9.3 ステージング環境
- Render staging service
- 本番同等の設定
- テスト用Zohoアカウント

## 10. 品質メトリクス

### 10.1 目標値
- コードカバレッジ: 90%以上
- ユニットテスト成功率: 100%
- E2Eテスト成功率: 95%以上
- セキュリティ脆弱性: Critical/High 0件

### 10.2 継続的改善
- 毎週のテストレビュー会議
- 四半期ごとのセキュリティ監査
- テスト失敗の根本原因分析
- テスト実行時間の最適化