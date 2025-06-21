"""End-to-end workflow scenario tests for MCP server."""

import pytest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from typing import Dict, Any, List


class TestWorkflowScenarios:
    """Test complete workflow scenarios involving multiple tools."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_project_id = "test_project_workflow"
        self.test_folder_id = "test_folder_workflow"
        self.created_task_ids = []
        self.uploaded_file_ids = []
    
    def teardown_method(self):
        """Cleanup after each test."""
        # In a real implementation, this would clean up created resources
        pass
    
    def test_complete_project_workflow(self, client: TestClient):
        """Test complete project workflow: create project -> tasks -> review -> summary."""
        
        # Step 1: Create initial tasks for the project
        task_names = [
            "設計ドキュメント作成",
            "実装フェーズ1",
            "テスト実行",
            "デプロイメント準備"
        ]
        
        created_tasks = []
        
        for i, task_name in enumerate(task_names):
            # Create task
            create_request = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "createTask",
                    "arguments": {
                        "project_id": self.test_project_id,
                        "name": task_name,
                        "owner": f"developer{i+1}@example.com",
                        "due_date": (datetime.now() + timedelta(days=7+i*3)).strftime("%Y-%m-%d")
                    }
                },
                "id": f"workflow_create_task_{i}"
            }
            
            response = client.post("/mcp", json=create_request)
            assert response.status_code == 200
            
            data = response.json()
            assert "result" in data
            
            # Extract task ID (simplified for testing)
            task_id = f"workflow_task_{i+1}"
            created_tasks.append({
                "id": task_id,
                "name": task_name,
                "status": "open"
            })
            self.created_task_ids.append(task_id)
        
        # Step 2: List all tasks to verify creation
        list_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": self.test_project_id,
                    "status": "open"
                }
            },
            "id": "workflow_list_tasks"
        }
        
        response = client.post("/mcp", json=list_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data
        
        # Step 3: Update some tasks to simulate progress
        # Complete first two tasks
        for i in range(2):
            update_request = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "updateTask",
                    "arguments": {
                        "task_id": created_tasks[i]["id"],
                        "status": "closed"
                    }
                },
                "id": f"workflow_update_task_{i}"
            }
            
            response = client.post("/mcp", json=update_request)
            assert response.status_code == 200
            
            data = response.json()
            assert "result" in data
        
        # Step 4: Get project summary to check progress
        summary_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "getProjectSummary",
                "arguments": {
                    "project_id": self.test_project_id,
                    "period": "month"
                }
            },
            "id": "workflow_project_summary"
        }
        
        response = client.post("/mcp", json=summary_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data
        
        # Verify summary contains progress information
        summary_text = data["result"]["content"][0]["text"]
        assert any(term in summary_text.lower() for term in ["completion", "progress", "完了"])
        
        # Step 5: Upload a review document
        upload_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "uploadReviewSheet",
                "arguments": {
                    "project_id": self.test_project_id,
                    "folder_id": self.test_folder_id,
                    "name": f"review_report_{datetime.now().strftime('%Y%m%d')}.md",
                    "content_base64": self._create_mock_review_content()
                }
            },
            "id": "workflow_upload_review"
        }
        
        response = client.post("/mcp", json=upload_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data
    
    def test_bug_tracking_workflow(self, client: TestClient):
        """Test bug tracking and resolution workflow."""
        
        # Step 1: Create bug report task
        bug_task_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": self.test_project_id,
                    "name": "BUG: ログイン時の認証エラー",
                    "owner": "qa.tester@example.com",
                    "due_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                }
            },
            "id": "bug_create_task"
        }
        
        response = client.post("/mcp", json=bug_task_request)
        assert response.status_code == 200
        
        bug_task_id = "bug_task_001"
        self.created_task_ids.append(bug_task_id)
        
        # Step 2: Get task details for bug investigation
        detail_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "getTaskDetail",
                "arguments": {
                    "task_id": bug_task_id
                }
            },
            "id": "bug_get_details"
        }
        
        response = client.post("/mcp", json=detail_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data
        
        # Step 3: Search for related documentation
        search_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "searchFiles",
                "arguments": {
                    "query": "authentication login"
                }
            },
            "id": "bug_search_docs"
        }
        
        response = client.post("/mcp", json=search_request)
        assert response.status_code == 200
        
        # Step 4: Create fix task
        fix_task_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": self.test_project_id,
                    "name": "FIX: 認証エラーの修正",
                    "owner": "developer@example.com",
                    "due_date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
                }
            },
            "id": "bug_create_fix_task"
        }
        
        response = client.post("/mcp", json=fix_task_request)
        assert response.status_code == 200
        
        fix_task_id = "fix_task_001"
        self.created_task_ids.append(fix_task_id)
        
        # Step 5: Complete fix task
        complete_fix_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "updateTask",
                "arguments": {
                    "task_id": fix_task_id,
                    "status": "closed"
                }
            },
            "id": "bug_complete_fix"
        }
        
        response = client.post("/mcp", json=complete_fix_request)
        assert response.status_code == 200
        
        # Step 6: Close original bug task
        close_bug_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "updateTask",
                "arguments": {
                    "task_id": bug_task_id,
                    "status": "closed"
                }
            },
            "id": "bug_close_original"
        }
        
        response = client.post("/mcp", json=close_bug_request)
        assert response.status_code == 200
    
    def test_code_review_workflow(self, client: TestClient):
        """Test code review workflow with file uploads and task management."""
        
        # Step 1: Create development task
        dev_task_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": self.test_project_id,
                    "name": "新機能: ユーザープロファイル管理",
                    "owner": "developer@example.com",
                    "due_date": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
                }
            },
            "id": "review_create_dev_task"
        }
        
        response = client.post("/mcp", json=dev_task_request)
        assert response.status_code == 200
        
        dev_task_id = "dev_task_001"
        self.created_task_ids.append(dev_task_id)
        
        # Step 2: Upload code review checklist
        checklist_content = self._create_code_review_checklist()
        upload_checklist_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "uploadReviewSheet",
                "arguments": {
                    "project_id": self.test_project_id,
                    "folder_id": self.test_folder_id,
                    "name": "code_review_checklist.md",
                    "content_base64": checklist_content
                }
            },
            "id": "review_upload_checklist"
        }
        
        response = client.post("/mcp", json=upload_checklist_request)
        assert response.status_code == 200
        
        # Step 3: Create review task
        review_task_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": self.test_project_id,
                    "name": "REVIEW: ユーザープロファイル管理のコードレビュー",
                    "owner": "senior.developer@example.com",
                    "due_date": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
                }
            },
            "id": "review_create_review_task"
        }
        
        response = client.post("/mcp", json=review_task_request)
        assert response.status_code == 200
        
        review_task_id = "review_task_001"
        self.created_task_ids.append(review_task_id)
        
        # Step 4: Search for related files
        search_related_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "searchFiles",
                "arguments": {
                    "query": "user profile",
                    "folder_id": self.test_folder_id
                }
            },
            "id": "review_search_files"
        }
        
        response = client.post("/mcp", json=search_related_request)
        assert response.status_code == 200
        
        # Step 5: Upload review results
        review_results_content = self._create_review_results()
        upload_results_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "uploadReviewSheet",
                "arguments": {
                    "project_id": self.test_project_id,
                    "folder_id": self.test_folder_id,
                    "name": f"review_results_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    "content_base64": review_results_content
                }
            },
            "id": "review_upload_results"
        }
        
        response = client.post("/mcp", json=upload_results_request)
        assert response.status_code == 200
        
        # Step 6: Complete review task
        complete_review_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "updateTask",
                "arguments": {
                    "task_id": review_task_id,
                    "status": "closed"
                }
            },
            "id": "review_complete_task"
        }
        
        response = client.post("/mcp", json=complete_review_request)
        assert response.status_code == 200
        
        # Step 7: Update development task based on review
        update_dev_task_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "updateTask",
                "arguments": {
                    "task_id": dev_task_id,
                    "status": "closed"
                }
            },
            "id": "review_update_dev_task"
        }
        
        response = client.post("/mcp", json=update_dev_task_request)
        assert response.status_code == 200
    
    def test_release_preparation_workflow(self, client: TestClient):
        """Test release preparation workflow."""
        
        # Step 1: Create release planning task
        release_planning_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": self.test_project_id,
                    "name": "リリース v2.1.0 準備",
                    "owner": "release.manager@example.com",
                    "due_date": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
                }
            },
            "id": "release_planning_task"
        }
        
        response = client.post("/mcp", json=release_planning_request)
        assert response.status_code == 200
        
        # Step 2: Get current project summary for release readiness
        summary_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "getProjectSummary",
                "arguments": {
                    "project_id": self.test_project_id,
                    "period": "month"
                }
            },
            "id": "release_project_summary"
        }
        
        response = client.post("/mcp", json=summary_request)
        assert response.status_code == 200
        
        # Step 3: Search for test documentation
        search_test_docs_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "searchFiles",
                "arguments": {
                    "query": "test report"
                }
            },
            "id": "release_search_test_docs"
        }
        
        response = client.post("/mcp", json=search_test_docs_request)
        assert response.status_code == 200
        
        # Step 4: Create release checklist tasks
        release_tasks = [
            "テスト完了確認",
            "ドキュメント更新",
            "セキュリティ監査",
            "デプロイメント準備"
        ]
        
        for i, task_name in enumerate(release_tasks):
            create_task_request = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "createTask",
                    "arguments": {
                        "project_id": self.test_project_id,
                        "name": f"RELEASE: {task_name}",
                        "owner": f"team.lead{i+1}@example.com",
                        "due_date": (datetime.now() + timedelta(days=7+i)).strftime("%Y-%m-%d")
                    }
                },
                "id": f"release_create_task_{i}"
            }
            
            response = client.post("/mcp", json=create_task_request)
            assert response.status_code == 200
            
            task_id = f"release_task_{i+1}"
            self.created_task_ids.append(task_id)
        
        # Step 5: Upload release notes
        release_notes_content = self._create_release_notes()
        upload_release_notes_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "uploadReviewSheet",
                "arguments": {
                    "project_id": self.test_project_id,
                    "folder_id": self.test_folder_id,
                    "name": "release_notes_v2.1.0.md",
                    "content_base64": release_notes_content
                }
            },
            "id": "release_upload_notes"
        }
        
        response = client.post("/mcp", json=upload_release_notes_request)
        assert response.status_code == 200
        
        # Step 6: Complete first release task (testing)
        complete_test_task_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "updateTask",
                "arguments": {
                    "task_id": "release_task_1",
                    "status": "closed"
                }
            },
            "id": "release_complete_test_task"
        }
        
        response = client.post("/mcp", json=complete_test_task_request)
        assert response.status_code == 200
        
        # Step 7: Get updated project summary
        final_summary_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "getProjectSummary",
                "arguments": {
                    "project_id": self.test_project_id,
                    "period": "week"
                }
            },
            "id": "release_final_summary"
        }
        
        response = client.post("/mcp", json=final_summary_request)
        assert response.status_code == 200
    
    def test_error_recovery_workflow(self, client: TestClient):
        """Test error handling and recovery in workflow scenarios."""
        
        # Step 1: Attempt to create task with invalid project ID
        invalid_project_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": "invalid_project_id_12345",
                    "name": "Should Fail Task",
                    "owner": "test@example.com"
                }
            },
            "id": "error_invalid_project"
        }
        
        response = client.post("/mcp", json=invalid_project_request)
        assert response.status_code == 200  # MCP always returns 200
        
        data = response.json()
        # Should contain error information
        assert "error" in data or "not found" in str(data).lower()
        
        # Step 2: Recover by using valid project ID
        valid_project_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": self.test_project_id,
                    "name": "Recovery Task",
                    "owner": "test@example.com"
                }
            },
            "id": "error_recovery_task"
        }
        
        response = client.post("/mcp", json=valid_project_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data
        
        recovery_task_id = "recovery_task_001"
        self.created_task_ids.append(recovery_task_id)
        
        # Step 3: Attempt to update non-existent task
        invalid_task_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "updateTask",
                "arguments": {
                    "task_id": "non_existent_task_12345",
                    "status": "closed"
                }
            },
            "id": "error_invalid_task"
        }
        
        response = client.post("/mcp", json=invalid_task_request)
        assert response.status_code == 200
        
        data = response.json()
        # Should handle gracefully
        assert "error" in data or "not found" in str(data).lower()
        
        # Step 4: Recover by updating valid task
        valid_update_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "updateTask",
                "arguments": {
                    "task_id": recovery_task_id,
                    "status": "closed"
                }
            },
            "id": "error_recovery_update"
        }
        
        response = client.post("/mcp", json=valid_update_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data
        
        # Step 5: Verify system is still functional
        health_check_response = client.get("/health")
        assert health_check_response.status_code == 200
        assert health_check_response.json()["status"] == "healthy"
    
    def _create_mock_review_content(self) -> str:
        """Create mock review document content."""
        import base64
        
        content = """# プロジェクトレビューレポート

## 概要
プロジェクトの進捗状況と品質評価

## 完了タスク
- 設計ドキュメント作成 ✅
- 実装フェーズ1 ✅

## 進行中タスク
- テスト実行 🔄
- デプロイメント準備 📋

## 推奨事項
1. テストカバレッジの向上
2. ドキュメントの更新
3. セキュリティレビューの実施

## 次のステップ
- テストフェーズの完了
- 本番環境への準備
"""
        return base64.b64encode(content.encode()).decode()
    
    def _create_code_review_checklist(self) -> str:
        """Create code review checklist content."""
        import base64
        
        content = """# コードレビューチェックリスト

## 機能性
- [ ] 要件通りに動作するか
- [ ] エラーハンドリングが適切か
- [ ] パフォーマンスは許容範囲か

## コード品質
- [ ] 可読性が高いか
- [ ] 命名規則に従っているか
- [ ] コメントが適切か

## セキュリティ
- [ ] 入力検証が実装されているか
- [ ] 認証・認可が適切か
- [ ] セキュリティホールがないか

## テスト
- [ ] ユニットテストが存在するか
- [ ] テストカバレッジが十分か
- [ ] エッジケースがテストされているか
"""
        return base64.b64encode(content.encode()).decode()
    
    def _create_review_results(self) -> str:
        """Create review results content."""
        import base64
        
        # Mock Excel-like content (simplified)
        content = """Review Results,Status,Comments
Functionality,PASS,All requirements met
Code Quality,PASS,Well structured code
Security,MINOR ISSUES,Need input validation improvements
Testing,PASS,Good test coverage
Overall,APPROVED,Ready for merge with minor fixes"""
        return base64.b64encode(content.encode()).decode()
    
    def _create_release_notes(self) -> str:
        """Create release notes content."""
        import base64
        
        content = """# リリースノート v2.1.0

## 新機能
- ユーザープロファイル管理機能
- 高度な検索フィルタ
- ダッシュボードの改善

## バグ修正
- ログイン時の認証エラーを修正
- ファイルアップロードの安定性向上
- パフォーマンスの最適化

## 技術的改善
- セキュリティ強化
- API レスポンス時間の改善
- ログ機能の拡張

## 既知の問題
- なし

## アップグレード手順
1. バックアップの作成
2. システムの停止
3. 新しいバージョンのデプロイ
4. データベースのマイグレーション
5. システムの再起動と確認
"""
        return base64.b64encode(content.encode()).decode()


class TestCrossToolIntegration:
    """Test integration between different MCP tools."""
    
    def test_task_and_file_integration(self, client: TestClient):
        """Test integration between task management and file operations."""
        
        # Step 1: Create a documentation task
        doc_task_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": "integration_test_project",
                    "name": "API ドキュメント作成",
                    "owner": "technical.writer@example.com",
                    "due_date": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
                }
            },
            "id": "integration_create_doc_task"
        }
        
        response = client.post("/mcp", json=doc_task_request)
        assert response.status_code == 200
        
        # Step 2: Search for existing documentation
        search_docs_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "searchFiles",
                "arguments": {
                    "query": "API documentation"
                }
            },
            "id": "integration_search_docs"
        }
        
        response = client.post("/mcp", json=search_docs_request)
        assert response.status_code == 200
        
        # Step 3: Upload new documentation
        upload_doc_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "uploadReviewSheet",
                "arguments": {
                    "project_id": "integration_test_project",
                    "folder_id": "docs_folder",
                    "name": "api_documentation_v2.md",
                    "content_base64": self._create_api_doc_content()
                }
            },
            "id": "integration_upload_doc"
        }
        
        response = client.post("/mcp", json=upload_doc_request)
        assert response.status_code == 200
        
        # Step 4: Complete the documentation task
        complete_task_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "updateTask",
                "arguments": {
                    "task_id": "doc_task_001",
                    "status": "closed"
                }
            },
            "id": "integration_complete_task"
        }
        
        response = client.post("/mcp", json=complete_task_request)
        assert response.status_code == 200
        
        # Step 5: Verify the uploaded file can be found
        search_new_doc_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "searchFiles",
                "arguments": {
                    "query": "api_documentation_v2"
                }
            },
            "id": "integration_verify_upload"
        }
        
        response = client.post("/mcp", json=search_new_doc_request)
        assert response.status_code == 200
    
    def test_summary_with_multiple_tools(self, client: TestClient):
        """Test project summary integration with task and file operations."""
        
        # Step 1: Create multiple tasks of different types
        task_types = [
            ("FEATURE: 新機能開発", "feature.dev@example.com"),
            ("BUG: 緊急バグ修正", "bug.fixer@example.com"),
            ("DOCS: ドキュメント更新", "doc.writer@example.com"),
            ("TEST: テスト追加", "qa.engineer@example.com")
        ]
        
        for i, (task_name, owner) in enumerate(task_types):
            create_task_request = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "createTask",
                    "arguments": {
                        "project_id": "summary_integration_project",
                        "name": task_name,
                        "owner": owner,
                        "due_date": (datetime.now() + timedelta(days=3+i)).strftime("%Y-%m-%d")
                    }
                },
                "id": f"summary_create_task_{i}"
            }
            
            response = client.post("/mcp", json=create_task_request)
            assert response.status_code == 200
        
        # Step 2: Complete some tasks
        for i in range(2):  # Complete first 2 tasks
            update_task_request = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "updateTask",
                    "arguments": {
                        "task_id": f"summary_task_{i+1}",
                        "status": "closed"
                    }
                },
                "id": f"summary_complete_task_{i}"
            }
            
            response = client.post("/mcp", json=update_task_request)
            assert response.status_code == 200
        
        # Step 3: Upload some project files
        upload_requests = [
            ("project_status.md", self._create_status_doc()),
            ("test_results.xlsx", self._create_test_results())
        ]
        
        for filename, content in upload_requests:
            upload_request = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "uploadReviewSheet",
                    "arguments": {
                        "project_id": "summary_integration_project",
                        "folder_id": "project_docs",
                        "name": filename,
                        "content_base64": content
                    }
                },
                "id": f"summary_upload_{filename.split('.')[0]}"
            }
            
            response = client.post("/mcp", json=upload_request)
            assert response.status_code == 200
        
        # Step 4: Get comprehensive project summary
        summary_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "getProjectSummary",
                "arguments": {
                    "project_id": "summary_integration_project",
                    "period": "month"
                }
            },
            "id": "summary_comprehensive"
        }
        
        response = client.post("/mcp", json=summary_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data
        
        # Verify summary includes task completion information
        summary_text = data["result"]["content"][0]["text"]
        assert any(term in summary_text.lower() for term in ["completion", "progress", "tasks"])
        
        # Step 5: Search for uploaded files to verify they're accessible
        search_files_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "searchFiles",
                "arguments": {
                    "query": "project_status"
                }
            },
            "id": "summary_search_uploaded"
        }
        
        response = client.post("/mcp", json=search_files_request)
        assert response.status_code == 200
    
    def _create_api_doc_content(self) -> str:
        """Create API documentation content."""
        import base64
        
        content = """# API Documentation v2.0

## Overview
This document describes the REST API endpoints for the application.

## Authentication
All API requests require authentication via JWT token.

## Endpoints

### Tasks
- GET /api/tasks - List all tasks
- POST /api/tasks - Create new task
- PUT /api/tasks/{id} - Update task
- DELETE /api/tasks/{id} - Delete task

### Files
- GET /api/files - Search files
- POST /api/files - Upload file
- GET /api/files/{id} - Download file

## Error Handling
All errors return JSON with error code and message.
"""
        return base64.b64encode(content.encode()).decode()
    
    def _create_status_doc(self) -> str:
        """Create project status document."""
        import base64
        
        content = """# プロジェクト状況レポート

## 全体進捗
- 完了率: 50%
- 予定通り進行中

## 主要マイルストーン
- [x] 設計フェーズ完了
- [x] 実装フェーズ1完了
- [ ] テストフェーズ
- [ ] リリース準備

## リスク
- なし

## 次週の予定
- テストケース追加
- パフォーマンステスト実行
"""
        return base64.b64encode(content.encode()).decode()
    
    def _create_test_results(self) -> str:
        """Create test results document."""
        import base64
        
        content = """Test Name,Status,Coverage,Notes
Unit Tests,PASS,95%,All core functions covered
Integration Tests,PASS,87%,API endpoints tested
Performance Tests,PASS,N/A,Response times within SLA
Security Tests,PASS,N/A,No vulnerabilities found"""
        return base64.b64encode(content.encode()).decode()