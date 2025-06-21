"""Tests for tasks handler module."""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from pydantic import ValidationError

from server.handlers.tasks import TaskHandler, Task, ProjectSummary


class TestTaskModel:
    """Test Task model validation."""
    
    def test_task_model_creation_with_required_fields(self):
        """Test creating Task with required fields only."""
        task = Task(
            id="12345",
            name="Test Task",
            status="open"
        )
        assert task.id == "12345"
        assert task.name == "Test Task"
        assert task.status == "open"
        assert task.owner is None
        assert task.due_date is None
        assert task.created_at is None
        assert task.description is None
        assert task.url is None
    
    def test_task_model_creation_with_all_fields(self):
        """Test creating Task with all fields."""
        created_at = datetime.now(timezone.utc)
        due_date = date.today()
        
        task = Task(
            id="12345",
            name="Test Task",
            status="open",
            owner="test@example.com",
            due_date=due_date,
            created_at=created_at,
            description="Test description",
            url="https://example.com/task/12345"
        )
        
        assert task.id == "12345"
        assert task.name == "Test Task"
        assert task.status == "open"
        assert task.owner == "test@example.com"
        assert task.due_date == due_date
        assert task.created_at == created_at
        assert task.description == "Test description"
        assert task.url == "https://example.com/task/12345"


class TestProjectSummaryModel:
    """Test ProjectSummary model validation."""
    
    def test_project_summary_model_creation(self):
        """Test creating ProjectSummary with all fields."""
        summary = ProjectSummary(
            project_id="proj123",
            total_tasks=100,
            completion_rate=85.5,
            overdue_count=5,
            open_count=10,
            closed_count=85
        )
        
        assert summary.project_id == "proj123"
        assert summary.total_tasks == 100
        assert summary.completion_rate == 85.5
        assert summary.overdue_count == 5
        assert summary.open_count == 10
        assert summary.closed_count == 85


class TestTaskHandler:
    """Test TaskHandler class."""
    
    @pytest.fixture
    def handler(self):
        """Create TaskHandler instance with mocked API client."""
        with patch('server.handlers.tasks.ZohoAPIClient') as mock_client:
            handler = TaskHandler()
            handler.api_client = AsyncMock()
            return handler
    
    @pytest.mark.asyncio
    async def test_list_tasks_success(self, handler):
        """Test successful task listing."""
        # Mock API response
        mock_response = {
            "tasks": [
                {
                    "id": "12345",
                    "name": "Test Task 1",
                    "status": "open",
                    "owner": {"name": "John Doe"},
                    "due_date": "2023-12-31",
                    "created_time": "2023-12-01T10:00:00Z",
                    "description": "Test description",
                    "link": {"self": {"url": "https://example.com/task/12345"}}
                },
                {
                    "id": "67890",
                    "name": "Test Task 2",
                    "status": "closed",
                    "owner": {"name": "Jane Smith"},
                    "due_date": "2023-12-30",
                    "created_time": "2023-12-02T11:00:00Z",
                    "description": "Another test description",
                    "link": {"self": {"url": "https://example.com/task/67890"}}
                }
            ]
        }
        
        handler.api_client.get.return_value = mock_response
        
        result = await handler.list_tasks("proj123", "open")
        
        # Verify API call
        handler.api_client.get.assert_called_once_with(
            "/projects/proj123/tasks/",
            params={"status": "open"}
        )
        
        # Verify result
        assert result["project_id"] == "proj123"
        assert result["total_count"] == 2
        assert result["status_filter"] == "open"
        assert len(result["tasks"]) == 2
        
        # Verify first task
        task1 = result["tasks"][0]
        assert task1["id"] == "12345"
        assert task1["name"] == "Test Task 1"
        assert task1["status"] == "open"
        assert task1["owner"] == "John Doe"
    
    @pytest.mark.asyncio
    async def test_list_tasks_without_status_filter(self, handler):
        """Test task listing without status filter."""
        mock_response = {"tasks": []}
        handler.api_client.get.return_value = mock_response
        
        result = await handler.list_tasks("proj123")
        
        handler.api_client.get.assert_called_once_with(
            "/projects/proj123/tasks/",
            params={}
        )
        
        assert result["status_filter"] is None
    
    @pytest.mark.asyncio
    async def test_list_tasks_invalid_status(self, handler):
        """Test task listing with invalid status."""
        with pytest.raises(ValueError, match="Invalid status: invalid"):
            await handler.list_tasks("proj123", "invalid")
    
    @pytest.mark.asyncio
    async def test_list_tasks_with_invalid_task_data(self, handler):
        """Test task listing with invalid task data - KeyError causes entire function to fail."""
        mock_response = {
            "tasks": [
                {
                    "id": "12345",
                    "name": "Valid Task",
                    "status": "open"
                },
                {
                    # Missing required 'id' field - this will cause KeyError
                    "name": "Invalid Task",
                    "status": "open"
                },
                {
                    "id": "67890",
                    "name": "Another Valid Task",
                    "status": "closed"
                }
            ]
        }
        
        handler.api_client.get.return_value = mock_response
        
        # The current implementation directly accesses task_data["id"] which causes KeyError
        # This propagates up and causes the entire function to fail
        with pytest.raises(Exception, match="'id'"):
            await handler.list_tasks("proj123")
    
    @pytest.mark.asyncio
    async def test_list_tasks_api_error(self, handler):
        """Test task listing with API error."""
        handler.api_client.get.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            await handler.list_tasks("proj123")
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, handler):
        """Test successful task creation."""
        mock_response = {
            "task": {
                "id": "new_task_123",
                "link": {"self": {"url": "https://example.com/task/new_task_123"}}
            }
        }
        
        handler.api_client.post.return_value = mock_response
        
        result = await handler.create_task(
            "proj123",
            "New Task",
            "owner@example.com",
            "2023-12-31"
        )
        
        # Verify API call
        handler.api_client.post.assert_called_once_with(
            "/projects/proj123/tasks/",
            json={
                "name": "New Task",
                "owner": "owner@example.com",
                "due_date": "2023-12-31"
            },
            retry=True
        )
        
        # Verify result
        assert result["task_id"] == "new_task_123"
        assert result["name"] == "New Task"
        assert result["project_id"] == "proj123"
        assert result["status"] == "created"
        assert result["owner"] == "owner@example.com"
        assert result["due_date"] == "2023-12-31"
    
    @pytest.mark.asyncio
    async def test_create_task_minimal_data(self, handler):
        """Test task creation with minimal data."""
        mock_response = {
            "task": {
                "id": "new_task_123",
                "link": {"self": {"url": "https://example.com/task/new_task_123"}}
            }
        }
        
        handler.api_client.post.return_value = mock_response
        
        result = await handler.create_task("proj123", "New Task")
        
        handler.api_client.post.assert_called_once_with(
            "/projects/proj123/tasks/",
            json={"name": "New Task"},
            retry=True
        )
        
        assert result["owner"] is None
        assert result["due_date"] is None
    
    @pytest.mark.asyncio
    async def test_create_task_invalid_date_format(self, handler):
        """Test task creation with invalid date format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            await handler.create_task("proj123", "New Task", None, "invalid-date")
    
    @pytest.mark.asyncio
    async def test_create_task_no_task_id_in_response(self, handler):
        """Test task creation when no task ID is returned."""
        mock_response = {"task": {}}
        handler.api_client.post.return_value = mock_response
        
        with pytest.raises(Exception, match="Task creation failed: No task ID returned"):
            await handler.create_task("proj123", "New Task")
    
    @pytest.mark.asyncio
    async def test_create_task_api_error(self, handler):
        """Test task creation with API error."""
        handler.api_client.post.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            await handler.create_task("proj123", "New Task")
    
    @pytest.mark.asyncio
    async def test_update_task_success(self, handler):
        """Test successful task update."""
        handler.api_client.put.return_value = {}
        
        result = await handler.update_task(
            "task123",
            status="closed",
            due_date="2023-12-31",
            owner="new_owner@example.com"
        )
        
        # Verify API call
        handler.api_client.put.assert_called_once_with(
            "/tasks/task123/",
            json={
                "status": "closed",
                "due_date": "2023-12-31",
                "owner": "new_owner@example.com"
            }
        )
        
        # Verify result
        assert result["task_id"] == "task123"
        assert result["status"] == "updated"
        assert set(result["updated_fields"]) == {"status", "due_date", "owner"}
    
    @pytest.mark.asyncio
    async def test_update_task_invalid_status(self, handler):
        """Test task update with invalid status."""
        with pytest.raises(ValueError, match="Invalid status: invalid"):
            await handler.update_task("task123", status="invalid")
    
    @pytest.mark.asyncio
    async def test_update_task_invalid_date_format(self, handler):
        """Test task update with invalid date format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            await handler.update_task("task123", due_date="invalid-date")
    
    @pytest.mark.asyncio
    async def test_update_task_no_fields_provided(self, handler):
        """Test task update with no fields provided."""
        with pytest.raises(ValueError, match="No update fields provided"):
            await handler.update_task("task123")
    
    @pytest.mark.asyncio
    async def test_update_task_api_error(self, handler):
        """Test task update with API error."""
        handler.api_client.put.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            await handler.update_task("task123", status="closed")
    
    @pytest.mark.asyncio
    async def test_get_task_detail_success(self, handler):
        """Test successful task detail retrieval."""
        mock_task_response = {
            "task": {
                "id": "task123",
                "name": "Test Task",
                "description": "Test description",
                "status": "open",
                "owner": {"name": "John Doe"},
                "due_date": "2023-12-31",
                "created_time": "2023-12-01T10:00:00Z",
                "updated_time": "2023-12-02T11:00:00Z",
                "priority": "high",
                "percent_complete": 75,
                "link": {"self": {"url": "https://example.com/task/task123"}}
            }
        }
        
        mock_comments_response = {
            "comments": [
                {"id": "comment1", "content": "First comment"},
                {"id": "comment2", "content": "Second comment"}
            ]
        }
        
        handler.api_client.get.side_effect = [mock_task_response, mock_comments_response]
        
        result = await handler.get_task_detail("task123")
        
        # Verify API calls
        assert handler.api_client.get.call_count == 2
        handler.api_client.get.assert_any_call("/tasks/task123/")
        handler.api_client.get.assert_any_call("/tasks/task123/comments/")
        
        # Verify result
        assert result["id"] == "task123"
        assert result["name"] == "Test Task"
        assert result["description"] == "Test description"
        assert result["status"] == "open"
        assert result["owner"] == "John Doe"
        assert result["due_date"] == "2023-12-31"
        assert result["priority"] == "high"
        assert result["percent_complete"] == 75
        assert len(result["comments"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_task_detail_comments_error(self, handler):
        """Test task detail retrieval when comments API fails."""
        mock_task_response = {
            "task": {
                "id": "task123",
                "name": "Test Task",
                "status": "open"
            }
        }
        
        handler.api_client.get.side_effect = [mock_task_response, Exception("Comments API Error")]
        
        result = await handler.get_task_detail("task123")
        
        # Comments should be empty when API fails
        assert result["comments"] == []
    
    @pytest.mark.asyncio
    async def test_get_task_detail_api_error(self, handler):
        """Test task detail retrieval with API error."""
        handler.api_client.get.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            await handler.get_task_detail("task123")
    
    @pytest.mark.asyncio
    async def test_get_project_summary_success(self, handler):
        """Test successful project summary retrieval."""
        # Mock list_tasks response
        mock_list_tasks_response = {
            "tasks": [
                {"id": "1", "status": "open"},
                {"id": "2", "status": "closed"},
                {"id": "3", "status": "closed"},
                {"id": "4", "status": "overdue"},
                {"id": "5", "status": "open"}
            ]
        }
        
        # Mock project details response
        mock_project_response = {
            "project": {
                "name": "Test Project"
            }
        }
        
        # Mock the list_tasks method and project API call
        with patch.object(handler, 'list_tasks', return_value=mock_list_tasks_response):
            handler.api_client.get.return_value = mock_project_response
            
            result = await handler.get_project_summary("proj123", "month")
            
            # Verify API call for project details
            handler.api_client.get.assert_called_once_with("/projects/proj123/")
            
            # Verify result
            assert result["project_id"] == "proj123"
            assert result["project_name"] == "Test Project"
            assert result["total_tasks"] == 5
            assert result["open_count"] == 2
            assert result["closed_count"] == 2
            assert result["overdue_count"] == 1
            assert result["completion_rate"] == 40.0  # 2 closed out of 5 total
            assert result["period"] == "month"
            assert "last_updated" in result
    
    @pytest.mark.asyncio
    async def test_get_project_summary_no_tasks(self, handler):
        """Test project summary with no tasks."""
        mock_list_tasks_response = {"tasks": []}
        
        with patch.object(handler, 'list_tasks', return_value=mock_list_tasks_response):
            handler.api_client.get.side_effect = Exception("Project API Error")
            
            result = await handler.get_project_summary("proj123")
            
            # Should handle empty task list
            assert result["total_tasks"] == 0
            assert result["completion_rate"] == 0
            assert result["project_name"] == "Unknown Project"
    
    @pytest.mark.asyncio
    async def test_get_project_summary_project_api_error(self, handler):
        """Test project summary when project API fails."""
        mock_list_tasks_response = {
            "tasks": [
                {"id": "1", "status": "closed"}
            ]
        }
        
        with patch.object(handler, 'list_tasks', return_value=mock_list_tasks_response):
            handler.api_client.get.side_effect = Exception("Project API Error")
            
            result = await handler.get_project_summary("proj123")
            
            # Should use default project name when API fails
            assert result["project_name"] == "Unknown Project"
            assert result["total_tasks"] == 1
    
    @pytest.mark.asyncio
    async def test_get_project_summary_list_tasks_error(self, handler):
        """Test project summary when list_tasks fails."""
        with patch.object(handler, 'list_tasks', side_effect=Exception("List Tasks Error")):
            with pytest.raises(Exception, match="List Tasks Error"):
                await handler.get_project_summary("proj123")