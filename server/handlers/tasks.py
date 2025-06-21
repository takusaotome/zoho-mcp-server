"""Task management handlers for Zoho Projects API."""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationError

from server.zoho.api_client import ZohoAPIClient

logger = logging.getLogger(__name__)


class Task(BaseModel):
    """Task model."""
    
    id: str
    name: str
    status: str
    owner: Optional[str] = None
    due_date: Optional[date] = None
    created_at: Optional[datetime] = None
    description: Optional[str] = None
    url: Optional[str] = None


class ProjectSummary(BaseModel):
    """Project summary model."""
    
    project_id: str
    total_tasks: int
    completion_rate: float
    overdue_count: int
    open_count: int
    closed_count: int


class TaskHandler:
    """Handler for task management operations."""
    
    def __init__(self) -> None:
        """Initialize task handler."""
        self.api_client = ZohoAPIClient()
        logger.info("Task handler initialized")
    
    async def list_tasks(
        self,
        project_id: str,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """List tasks from a Zoho project.
        
        Args:
            project_id: Zoho project ID
            status: Optional status filter (open, closed, overdue)
            
        Returns:
            List of tasks
        """
        try:
            logger.info(f"Listing tasks for project {project_id}, status: {status}")
            
            # Build API endpoint
            endpoint = f"/projects/{project_id}/tasks/"
            params = {}
            
            if status:
                if status not in ["open", "closed", "overdue"]:
                    raise ValueError(f"Invalid status: {status}")
                params["status"] = status
            
            # Make API request
            response = await self.api_client.get(endpoint, params=params)
            
            # Parse tasks
            tasks_data = response.get("tasks", [])
            tasks = []
            
            for task_data in tasks_data:
                try:
                    task = Task(
                        id=task_data["id"],
                        name=task_data["name"],
                        status=task_data.get("status", "open"),
                        owner=task_data.get("owner", {}).get("name"),
                        due_date=task_data.get("due_date"),
                        created_at=task_data.get("created_time"),
                        description=task_data.get("description"),
                        url=task_data.get("link", {}).get("self", {}).get("url")
                    )
                    tasks.append(task.model_dump())
                except ValidationError as e:
                    logger.warning(f"Invalid task data: {e}")
                    continue
            
            result = {
                "project_id": project_id,
                "tasks": tasks,
                "total_count": len(tasks),
                "status_filter": status
            }
            
            logger.info(f"Retrieved {len(tasks)} tasks for project {project_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to list tasks for project {project_id}: {e}")
            raise
    
    async def create_task(
        self,
        project_id: str,
        name: str,
        owner: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new task in Zoho project.
        
        Args:
            project_id: Zoho project ID
            name: Task name
            owner: Task owner email/ID
            due_date: Due date in YYYY-MM-DD format
            
        Returns:
            Created task information
        """
        try:
            logger.info(f"Creating task '{name}' in project {project_id}")
            
            # Build request payload
            payload = {"name": name}
            
            if owner:
                payload["owner"] = owner
            
            if due_date:
                # Validate date format
                try:
                    parsed_date = datetime.strptime(due_date, "%Y-%m-%d").date()
                    payload["due_date"] = due_date
                except ValueError:
                    raise ValueError(f"Invalid date format: {due_date}. Use YYYY-MM-DD")
            
            # Make API request with retry logic
            endpoint = f"/projects/{project_id}/tasks/"
            response = await self.api_client.post(endpoint, json=payload, retry=True)
            
            # Extract task ID from response
            task_data = response.get("task", {})
            task_id = task_data.get("id")
            
            if not task_id:
                raise Exception("Task creation failed: No task ID returned")
            
            result = {
                "task_id": task_id,
                "name": name,
                "project_id": project_id,
                "status": "created",
                "owner": owner,
                "due_date": due_date,
                "url": task_data.get("link", {}).get("self", {}).get("url")
            }
            
            logger.info(f"Task created successfully: {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create task '{name}' in project {project_id}: {e}")
            raise
    
    async def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        due_date: Optional[str] = None,
        owner: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing task.
        
        Args:
            task_id: Task ID to update
            status: New task status
            due_date: New due date in YYYY-MM-DD format
            owner: New task owner
            
        Returns:
            Update confirmation
        """
        try:
            logger.info(f"Updating task {task_id}")
            
            # Build update payload
            payload = {}
            
            if status:
                if status not in ["open", "closed", "overdue"]:
                    raise ValueError(f"Invalid status: {status}")
                payload["status"] = status
            
            if due_date:
                try:
                    parsed_date = datetime.strptime(due_date, "%Y-%m-%d").date()
                    payload["due_date"] = due_date
                except ValueError:
                    raise ValueError(f"Invalid date format: {due_date}. Use YYYY-MM-DD")
            
            if owner:
                payload["owner"] = owner
            
            if not payload:
                raise ValueError("No update fields provided")
            
            # Make API request
            endpoint = f"/tasks/{task_id}/"
            response = await self.api_client.put(endpoint, json=payload)
            
            result = {
                "task_id": task_id,
                "updated_fields": list(payload.keys()),
                "status": "updated"
            }
            
            logger.info(f"Task {task_id} updated successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            raise
    
    async def get_task_detail(self, task_id: str) -> Dict[str, Any]:
        """Get detailed information about a task.
        
        Args:
            task_id: Task ID to retrieve
            
        Returns:
            Detailed task information
        """
        try:
            logger.info(f"Getting details for task {task_id}")
            
            # Make API request
            endpoint = f"/tasks/{task_id}/"
            response = await self.api_client.get(endpoint)
            
            task_data = response.get("task", {})
            
            # Get additional details like comments and history
            comments_endpoint = f"/tasks/{task_id}/comments/"
            try:
                comments_response = await self.api_client.get(comments_endpoint)
                comments = comments_response.get("comments", [])
            except Exception:
                comments = []
            
            result = {
                "id": task_data.get("id"),
                "name": task_data.get("name"),
                "description": task_data.get("description", ""),
                "status": task_data.get("status"),
                "owner": task_data.get("owner", {}).get("name"),
                "due_date": task_data.get("due_date"),
                "created_at": task_data.get("created_time"),
                "updated_at": task_data.get("updated_time"),
                "priority": task_data.get("priority"),
                "percent_complete": task_data.get("percent_complete", 0),
                "comments": comments,
                "url": task_data.get("link", {}).get("self", {}).get("url")
            }
            
            logger.info(f"Retrieved details for task {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get task details for {task_id}: {e}")
            raise
    
    async def get_project_summary(
        self,
        project_id: str,
        period: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get project summary with completion rate and KPIs.
        
        Args:
            project_id: Zoho project ID
            period: Time period filter (week, month)
            
        Returns:
            Project summary with KPIs
        """
        try:
            logger.info(f"Getting summary for project {project_id}, period: {period}")
            
            # Get all tasks for the project
            all_tasks = await self.list_tasks(project_id)
            tasks = all_tasks["tasks"]
            
            # Calculate metrics
            total_tasks = len(tasks)
            closed_tasks = len([t for t in tasks if t["status"] == "closed"])
            open_tasks = len([t for t in tasks if t["status"] == "open"])
            overdue_tasks = len([t for t in tasks if t["status"] == "overdue"])
            
            completion_rate = (closed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Get project details
            project_endpoint = f"/projects/{project_id}/"
            try:
                project_response = await self.api_client.get(project_endpoint)
                project_data = project_response.get("project", {})
                project_name = project_data.get("name", "Unknown Project")
            except Exception:
                project_name = "Unknown Project"
            
            summary = ProjectSummary(
                project_id=project_id,
                total_tasks=total_tasks,
                completion_rate=round(completion_rate, 2),
                overdue_count=overdue_tasks,
                open_count=open_tasks,
                closed_count=closed_tasks
            )
            
            result = {
                **summary.model_dump(),
                "project_name": project_name,
                "period": period,
                "last_updated": datetime.now().isoformat()
            }
            
            logger.info(f"Generated summary for project {project_id}: {completion_rate:.1f}% complete")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get project summary for {project_id}: {e}")
            raise