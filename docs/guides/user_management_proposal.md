# Zoho MCP Server - マルチユーザー対応改善提案

## 1. ユーザー別Zoho認証

### 現在の課題
- 全ユーザーが同一のZoho OAuth設定を使用
- データアクセスの分離ができない

### 改善案
```python
# ユーザー別OAuth設定の管理
class UserOAuthSettings:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.zoho_client_id = await get_user_oauth_setting(user_id, 'client_id')
        self.zoho_client_secret = await get_user_oauth_setting(user_id, 'client_secret')
        self.zoho_refresh_token = await get_user_oauth_setting(user_id, 'refresh_token')

# MCPエンドポイントでユーザー固有の認証を使用
@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> JSONResponse:
    # ユーザー固有のOAuth設定で API呼び出し
    user_oauth = UserOAuthSettings(current_user.sub)
    response = await mcp_handler.handle_request(body, user_oauth)
```

## 2. ユーザー別レート制限

### 改善案
```python
class EnhancedRateLimitMiddleware:
    def _get_rate_limit_key(self, request: Request, user_id: str = None) -> str:
        if user_id:
            return f"user:{user_id}"
        return f"ip:{self._get_client_identifier(request)}"
    
    def _get_user_rate_limits(self, user_id: str) -> tuple[int, int]:
        # ユーザー別の制限設定を取得
        user_limits = await get_user_rate_limits(user_id)
        return user_limits.get('calls', 100), user_limits.get('period', 60)
```

## 3. プロジェクト・アクセス権限制御

### 改善案
```python
class ProjectAccessControl:
    async def can_access_project(self, user_id: str, project_id: str) -> bool:
        user_permissions = await get_user_permissions(user_id)
        return project_id in user_permissions.get('accessible_projects', [])
    
    async def filter_user_accessible_projects(self, user_id: str, projects: list) -> list:
        accessible_projects = await get_user_accessible_projects(user_id)
        return [p for p in projects if p['id'] in accessible_projects]

# ツール実行時の権限チェック
async def list_tasks(self, project_id: str, user_id: str, **kwargs):
    if not await self.access_control.can_access_project(user_id, project_id):
        raise HTTPException(403, "Access denied to project")
    # 通常の処理を続行
```

## 4. 監査ログ

### 改善案
```python
class AuditLogger:
    async def log_user_action(self, user_id: str, action: str, resource: str, details: dict):
        audit_entry = {
            'timestamp': datetime.utcnow(),
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'details': details,
            'ip_address': request.client.host
        }
        await self.store_audit_log(audit_entry)

# MCPエンドポイントでの監査ログ
logger.info(f"MCP request from user: {current_user.sub}")
await audit_logger.log_user_action(
    current_user.sub, 
    "tool_call", 
    tool_name, 
    tool_arguments
)
```

## 5. ユーザー管理API

### 追加エンドポイント
```python
@app.post("/admin/users")
async def create_user(user_data: UserCreateRequest, admin_user: TokenData = Depends(get_admin_user)):
    # 新規ユーザー作成
    
@app.put("/admin/users/{user_id}/oauth")
async def update_user_oauth(user_id: str, oauth_settings: OAuthSettings):
    # ユーザーのOAuth設定更新
    
@app.get("/admin/users/{user_id}/activity")
async def get_user_activity(user_id: str):
    # ユーザーのアクティビティログ取得
```

## 実装優先度

### Phase 1 (即座に実装可能)
1. **監査ログの強化** - 現在のユーザー識別機能を活用
2. **ユーザー別レート制限** - 既存のミドルウェアを拡張

### Phase 2 (中期実装)
3. **プロジェクトアクセス制御** - 権限管理システムの追加
4. **管理用API** - ユーザー管理インターフェース

### Phase 3 (長期実装)
5. **ユーザー別OAuth設定** - 完全なマルチテナント対応

## セキュリティ考慮事項

1. **秘匿情報の管理**
   - ユーザー別OAuth設定はRedisまたは暗号化DBに保存
   - 環境変数での設定は避ける

2. **権限の最小化**
   - デフォルトでアクセス拒否
   - 明示的な許可のみ

3. **監査とモニタリング**
   - 全API呼び出しの記録
   - 異常なアクセスパターンの検出 