"""Task management handlers for Zoho Projects API."""

import logging
from datetime import date, datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, ValidationError

from server.zoho.api_client import ZohoAPIClient

logger = logging.getLogger(__name__)


class Task(BaseModel):
    """Task model."""

    id: Union[str, int]
    name: str
    status: Union[str, dict[str, Any]]
    owner: Optional[str] = None
    due_date: Union[str, Optional[date]] = None
    created_at: Union[str, Optional[datetime]] = None
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

    async def list_projects(self) -> dict[str, Any]:
        """List all available Zoho projects.

        Returns:
            List of projects with basic information
        """
        try:
            logger.info("Listing all projects")

            # Build API endpoint with portal ID
            import os
            portal_id = os.getenv("ZOHO_PORTAL_ID", "")
            if not portal_id:
                raise ValueError("ZOHO_PORTAL_ID environment variable is not set")
            endpoint = f"/portal/{portal_id}/projects/"

            # Make API request
            response = await self.api_client.get(endpoint)

            # Parse projects
            projects_data = response.get("projects", [])
            projects = []

            for project_data in projects_data:
                try:
                    project = {
                        "id": str(project_data["id"]),
                        "name": project_data["name"],
                        "status": project_data.get("status", "Unknown"),
                        "description": project_data.get("description", ""),
                        "created_date": project_data.get("created_date"),
                        "owner": project_data.get("owner", {}).get("name") if isinstance(project_data.get("owner"), dict) else project_data.get("owner"),
                        "url": project_data.get("link", {}).get("self", {}).get("url") if isinstance(project_data.get("link"), dict) else None
                    }
                    projects.append(project)
                except Exception as e:
                    logger.warning(f"Error processing project data: {e}")
                    logger.debug(f"Project data: {project_data}")
                    continue

            result = {
                "projects": projects,
                "total_count": len(projects)
            }

            logger.info(f"Retrieved {len(projects)} projects")
            return result

        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            raise

    async def list_tasks(
        self,
        project_id: str,
        status: Optional[str] = None,
        get_all: bool = True,
        index: int = 1,
        range: int = 200,
        summary_only: bool = False
    ) -> dict[str, Any]:
        """List tasks from a Zoho project.

        Args:
            project_id: Zoho project ID
            status: Optional status filter (open, closed, overdue) - Note: Not supported by API
            get_all: If True, fetch all tasks using pagination
            index: Starting index for pagination (1-based)
            range: Number of tasks per page (max 200)

        Returns:
            List of tasks
        """
        try:
            logger.info(f"Listing tasks for project {project_id}, status: {status}, get_all: {get_all}")

            # Build API endpoint with portal ID
            import os
            portal_id = os.getenv("ZOHO_PORTAL_ID", "")
            if not portal_id:
                raise ValueError("ZOHO_PORTAL_ID environment variable is not set")
            endpoint = f"/portal/{portal_id}/projects/{project_id}/tasks/"

            all_tasks = []

            if get_all:
                # Fetch all tasks using pagination with safety limits
                current_index = 1
                page_size = 200  # Maximum allowed by API
                max_pages = 20  # Safety limit: 20 pages * 200 = 4000 tasks max
                page_count = 0

                while page_count < max_pages:
                    page_count += 1
                    params = {
                        "index": current_index,
                        "range": page_size
                    }

                    # Note: Status filtering is not supported by Zoho API
                    # It returns error code 6832 if status parameter is used

                    logger.info(f"Fetching tasks page {page_count}: index={current_index}, range={page_size}")

                    try:
                        response = await self.api_client.get(endpoint, params=params)
                        tasks_data = response.get("tasks", [])

                        if not tasks_data:
                            logger.info(f"No more tasks found at page {page_count}")
                            break

                        # Process tasks for this page
                        page_tasks = []
                        for task_data in tasks_data:
                            try:
                                # IDを文字列に変換
                                task_id = str(task_data["id"])

                                # ステータスを処理
                                status_data = task_data.get("status", "open")
                                if isinstance(status_data, dict):
                                    task_status = status_data.get("name", "Unknown")
                                else:
                                    task_status = str(status_data)

                                # オーナー情報を処理
                                owner_data = task_data.get("owner", {})
                                if isinstance(owner_data, dict):
                                    owner = owner_data.get("name")
                                else:
                                    owner = str(owner_data) if owner_data else None

                                task = Task(
                                    id=task_id,
                                    name=task_data["name"],
                                    status=task_status,
                                    owner=owner,
                                    due_date=task_data.get("due_date"),
                                    created_at=task_data.get("created_time"),
                                    description=task_data.get("description"),
                                    url=task_data.get("link", {}).get("self", {}).get("url")
                                )
                                page_tasks.append(task.model_dump())
                            except ValidationError as e:
                                logger.warning(f"Invalid task data: {e}")
                                logger.debug(f"Task data: {task_data}")
                                continue
                            except Exception as e:
                                logger.error(f"Error processing task data: {e}")
                                logger.debug(f"Task data: {task_data}")
                                continue

                        all_tasks.extend(page_tasks)
                        logger.info(f"Retrieved {len(page_tasks)} tasks from page {page_count} (total: {len(all_tasks)})")

                        # Check if we got fewer tasks than requested (last page)
                        if len(tasks_data) < page_size:
                            logger.info(f"Last page reached (got {len(tasks_data)} < {page_size})")
                            break

                        current_index += page_size

                    except Exception as e:
                        logger.error(f"Error fetching page {page_count}: {e}")
                        break

                if page_count >= max_pages:
                    logger.warning(f"Reached maximum page limit ({max_pages}), may not have fetched all tasks")

                # Apply status filter after fetching all tasks (since API doesn't support it)
                if status:
                    if status == "open":
                        filtered_tasks = [t for t in all_tasks if t["status"].lower() in ["open", "in progress", "in review", "pending"]]
                    elif status == "closed":
                        filtered_tasks = [t for t in all_tasks if t["status"].lower() == "closed"]
                    elif status == "overdue":
                        # Check for overdue tasks (tasks with due_date in the past)
                        today = datetime.now().date()
                        filtered_tasks = []
                        for task in all_tasks:
                            if task.get("due_date"):
                                try:
                                    due_date = datetime.strptime(task["due_date"], "%m-%d-%Y").date()
                                    if due_date < today and task["status"].lower() != "closed":
                                        filtered_tasks.append(task)
                                except (ValueError, KeyError) as e:
                                    logger.warning(f"Invalid date format in task {task.get('id', 'unknown')}: {e}")
                                    continue
                    else:
                        raise ValueError(f"Invalid status: {status}")

                    all_tasks = filtered_tasks

            else:
                # Single page fetch
                params = {
                    "index": index,
                    "range": range
                }

                response = await self.api_client.get(endpoint, params=params)
                tasks_data = response.get("tasks", [])

                for task_data in tasks_data:
                    try:
                        # IDを文字列に変換
                        task_id = str(task_data["id"])

                        # ステータスを処理
                        status_data = task_data.get("status", "open")
                        if isinstance(status_data, dict):
                            task_status = status_data.get("name", "Unknown")
                        else:
                            task_status = str(status_data)

                        # オーナー情報を処理
                        owner_data = task_data.get("owner", {})
                        if isinstance(owner_data, dict):
                            owner = owner_data.get("name")
                        else:
                            owner = str(owner_data) if owner_data else None

                        task = Task(
                            id=task_id,
                            name=task_data["name"],
                            status=task_status,
                            owner=owner,
                            due_date=task_data.get("due_date"),
                            created_at=task_data.get("created_time"),
                            description=task_data.get("description"),
                            url=task_data.get("link", {}).get("self", {}).get("url")
                        )
                        all_tasks.append(task.model_dump())
                    except ValidationError as e:
                        logger.warning(f"Invalid task data: {e}")
                        logger.debug(f"Task data: {task_data}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing task data: {e}")
                        logger.debug(f"Task data: {task_data}")
                        continue

            result = {
                "success": True,
                "message": f"Successfully retrieved {len(all_tasks)} tasks from project {project_id}",
                "project_id": project_id,
                "tasks": all_tasks,
                "total_count": len(all_tasks),
                "status_filter": status,
                "pagination_used": get_all,
                "completed_at": datetime.now().isoformat()
            }

            logger.info(f"Retrieved {len(all_tasks)} tasks for project {project_id}")
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
    ) -> dict[str, Any]:
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
                    datetime.strptime(due_date, "%Y-%m-%d").date()
                    payload["due_date"] = due_date
                except ValueError:
                    raise ValueError(f"Invalid date format: {due_date}. Use YYYY-MM-DD")

            # Make API request with retry logic
            import os
            portal_id = os.getenv("ZOHO_PORTAL_ID", "")
            if not portal_id:
                raise ValueError("ZOHO_PORTAL_ID environment variable is not set")
            endpoint = f"/portal/{portal_id}/projects/{project_id}/tasks/"
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
    ) -> dict[str, Any]:
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
                    datetime.strptime(due_date, "%Y-%m-%d").date()
                    payload["due_date"] = due_date
                except ValueError:
                    raise ValueError(f"Invalid date format: {due_date}. Use YYYY-MM-DD")

            if owner:
                payload["owner"] = owner

            if not payload:
                raise ValueError("No update fields provided")

            # Make API request
            from server.core.config import settings
            portal_id = settings.portal_id
            endpoint = f"/portal/{portal_id}/tasks/{task_id}/"
            await self.api_client.put(endpoint, json=payload)

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

    async def get_task_detail(self, task_id: str) -> dict[str, Any]:
        """Get detailed information about a task.

        Args:
            task_id: Task ID to retrieve

        Returns:
            Detailed task information
        """
        try:
            logger.info(f"Getting details for task {task_id}")

            # Make API request
            from server.core.config import settings
            portal_id = settings.portal_id
            endpoint = f"/portal/{portal_id}/tasks/{task_id}/"
            response = await self.api_client.get(endpoint)

            task_data = response.get("task", {})

            # Get additional details like comments and history
            comments_endpoint = f"/portal/{portal_id}/tasks/{task_id}/comments/"
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
    ) -> dict[str, Any]:
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
            from server.core.config import settings
            portal_id = settings.portal_id
            project_endpoint = f"/portal/{portal_id}/projects/{project_id}/"
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
