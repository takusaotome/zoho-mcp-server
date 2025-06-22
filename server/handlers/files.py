"""File management handlers for Zoho WorkDrive API."""

import base64
import logging
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from server.zoho.api_client import ZohoAPIClient

logger = logging.getLogger(__name__)


class FileInfo(BaseModel):
    """File information model."""

    id: str
    name: str
    type: str
    size: Optional[int] = None
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    download_url: Optional[str] = None


class FileHandler:
    """Handler for file management operations."""

    def __init__(self) -> None:
        """Initialize file handler."""
        self.api_client = ZohoAPIClient()
        logger.info("File handler initialized")

    async def download_file(self, file_id: str) -> Dict[str, Any]:
        """Download a file from WorkDrive.

        Args:
            file_id: WorkDrive file ID

        Returns:
            File download information with presigned URL
        """
        try:
            logger.info(f"Downloading file {file_id}")

            # Get file metadata first
            endpoint = f"/workdrive/v1/files/{file_id}"
            file_response = await self.api_client.get(endpoint, use_workdrive=True)

            file_data = file_response.get("data", {})

            # Get download URL
            download_endpoint = f"/workdrive/v1/files/{file_id}/download"
            download_response = await self.api_client.get(
                download_endpoint,
                use_workdrive=True
            )

            download_url = download_response.get("download_url")

            if not download_url:
                raise Exception("Failed to get download URL")

            result = {
                "file_id": file_id,
                "name": file_data.get("attributes", {}).get("name"),
                "size": file_data.get("attributes", {}).get("size_in_bytes"),
                "type": file_data.get("attributes", {}).get("type"),
                "download_url": download_url,
                "expires_at": download_response.get("expires_at"),
                "status": "ready_for_download"
            }

            logger.info(f"Generated download URL for file {file_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            raise

    async def upload_review_sheet(
        self,
        project_id: str,
        folder_id: str,
        name: str,
        content_base64: str
    ) -> Dict[str, Any]:
        """Upload a review sheet to WorkDrive.

        Args:
            project_id: Zoho project ID
            folder_id: WorkDrive folder ID
            name: File name
            content_base64: Base64 encoded file content

        Returns:
            Upload result with file ID
        """
        try:
            logger.info(f"Uploading review sheet '{name}' to folder {folder_id}")

            # Validate base64 content
            try:
                file_content = base64.b64decode(content_base64)
            except Exception as e:
                raise ValueError(f"Invalid base64 content: {e}")

            # Check file size (1GB limit from requirements)
            max_size = 1024 * 1024 * 1024  # 1GB
            if len(file_content) > max_size:
                raise ValueError(f"File too large: {len(file_content)} bytes (max: {max_size})")

            # Prepare upload request
            endpoint = "/workdrive/v1/files"

            # Create multipart form data
            files = {
                "content": (name, file_content),
            }

            data = {
                "parent_id": folder_id,
                "filename": name,
                "override-name-exist": "true"
            }

            # Upload file
            upload_response = await self.api_client.post(
                endpoint,
                files=files,
                data=data,
                use_workdrive=True
            )

            file_data = upload_response.get("data", {})
            file_id = file_data.get("id")

            if not file_id:
                raise Exception("Upload failed: No file ID returned")

            result = {
                "file_id": file_id,
                "name": name,
                "folder_id": folder_id,
                "project_id": project_id,
                "size": len(file_content),
                "status": "uploaded",
                "upload_time": file_data.get("attributes", {}).get("created_time")
            }

            logger.info(f"Review sheet uploaded successfully: {file_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to upload review sheet '{name}': {e}")
            raise

    async def search_files(
        self,
        query: str,
        folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search files in WorkDrive.

        Args:
            query: Search query
            folder_id: Optional folder ID to limit search scope

        Returns:
            Search results with matching files
        """
        try:
            logger.info(f"Searching files with query: '{query}', folder: {folder_id}")

            # WorkDrive search might not be available for all accounts
            # Try different search approaches
            search_endpoints = [
                "/search",  # Basic search
                "/files/search",  # Files search
                "/filesearch"  # Alternative search
            ]

            response = None
            working_endpoint = None

            for endpoint in search_endpoints:
                try:
                    params = {}
                    if query:
                        params["q"] = query  # Try different parameter names
                    
                    response = await self.api_client.get(
                        endpoint,
                        params=params,
                        use_workdrive=True
                    )

                    working_endpoint = endpoint
                    logger.info(f"Search endpoint {endpoint} worked")
                    break

                except Exception as e:
                    logger.warning(f"Search endpoint {endpoint} failed: {e}")
                    continue

            if not response:
                # If search doesn't work, fall back to listing all files and filtering
                logger.info("Search endpoints failed, falling back to file listing with filter")
                all_files_result = await self.list_files(limit=100)
                all_files = all_files_result.get("files", [])
                
                # Filter files by query if provided
                filtered_files = []
                if query:
                    query_lower = query.lower()
                    for file_info in all_files:
                        file_name = file_info.get("name", "").lower()
                        if query_lower in file_name:
                            filtered_files.append(file_info)
                else:
                    filtered_files = all_files

                result = {
                    "query": query,
                    "folder_id": folder_id,
                    "files": filtered_files,
                    "total_count": len(filtered_files),
                    "search_method": "file_listing_filter"
                }

                logger.info(f"Found {len(filtered_files)} files for query '{query}' using file listing filter")
                return result

            # Parse search results if we got a response
            files_data = response.get("data", [])
            files = []

            for file_data in files_data:
                try:
                    attributes = file_data.get("attributes", {})
                    file_info = {
                        "id": file_data.get("id"),
                        "name": attributes.get("name"),
                        "type": attributes.get("type"),
                        "size": attributes.get("size_in_bytes"),
                        "created_at": attributes.get("created_time"),
                        "modified_at": attributes.get("modified_time")
                    }
                    files.append(file_info)
                except Exception as e:
                    logger.warning(f"Invalid file data in search results: {e}")
                    continue

            result = {
                "query": query,
                "folder_id": folder_id,
                "files": files,
                "total_count": len(files),
                "search_method": "api_search",
                "endpoint_used": working_endpoint
            }

            logger.info(f"Found {len(files)} files for query '{query}' using API search")
            return result

        except Exception as e:
            logger.error(f"Failed to search files with query '{query}': {e}")
            raise

    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get file information.

        Args:
            file_id: WorkDrive file ID

        Returns:
            File information
        """
        try:
            logger.info(f"Getting info for file {file_id}")

            endpoint = f"/workdrive/v1/files/{file_id}"
            response = await self.api_client.get(endpoint, use_workdrive=True)

            file_data = response.get("data", {})
            attributes = file_data.get("attributes", {})

            result = {
                "id": file_data.get("id"),
                "name": attributes.get("name"),
                "type": attributes.get("type"),
                "size": attributes.get("size_in_bytes"),
                "created_at": attributes.get("created_time"),
                "modified_at": attributes.get("modified_time"),
                "parent_id": attributes.get("parent_id"),
                "status": attributes.get("status"),
                "permissions": file_data.get("permissions", {})
            }

            logger.info(f"Retrieved info for file {file_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to get file info for {file_id}: {e}")
            raise

    async def list_folder_contents(
        self,
        folder_id: str,
        file_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """List contents of a folder.

        Args:
            folder_id: WorkDrive folder ID
            file_type: Optional file type filter

        Returns:
            Folder contents
        """
        try:
            logger.info(f"Listing contents of folder {folder_id}")

            endpoint = f"/workdrive/v1/files/{folder_id}/files"
            params = {}

            if file_type:
                params["type"] = file_type

            response = await self.api_client.get(
                endpoint,
                params=params,
                use_workdrive=True
            )

            files_data = response.get("data", [])
            files = []

            for file_data in files_data:
                try:
                    attributes = file_data.get("attributes", {})
                    file_info = {
                        "id": file_data.get("id"),
                        "name": attributes.get("name"),
                        "type": attributes.get("type"),
                        "size": attributes.get("size_in_bytes"),
                        "created_at": attributes.get("created_time"),
                        "modified_at": attributes.get("modified_time")
                    }
                    files.append(file_info)
                except Exception as e:
                    logger.warning(f"Invalid file data in folder listing: {e}")
                    continue

            result = {
                "folder_id": folder_id,
                "files": files,
                "total_count": len(files),
                "file_type_filter": file_type
            }

            logger.info(f"Listed {len(files)} items in folder {folder_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to list folder contents for {folder_id}: {e}")
            raise

    async def list_files(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List files from WorkDrive.

        Args:
            limit: Maximum number of files to return
            offset: Number of files to skip

        Returns:
            List of files
        """
        try:
            logger.info(f"Listing files from WorkDrive (limit: {limit}, offset: {offset})")

            # Try WorkDrive API endpoints without any parameters first
            endpoints_to_try = [
                "/files",  # Basic files endpoint
                "/privatefolders",  # Private folders
                "/myfiles",  # My files
                "/libraries",  # Libraries endpoint
                "/workspaces"  # Workspaces
            ]

            response = None
            working_endpoint = None

            for endpoint in endpoints_to_try:
                try:
                    # Try without any parameters first
                    response = await self.api_client.get(
                        endpoint,
                        params={},
                        use_workdrive=True
                    )

                    # If we get here, the endpoint worked
                    logger.info(f"Successfully used endpoint: {endpoint}")
                    working_endpoint = endpoint
                    break

                except Exception as e:
                    logger.warning(f"Endpoint {endpoint} failed: {e}")
                    if endpoint == endpoints_to_try[-1]:  # Last endpoint
                        # If all simple endpoints fail, try with basic parameters
                        logger.info("Trying /files with basic parameters...")
                        try:
                            response = await self.api_client.get(
                                "/files",
                                params={"limit": 10},  # Very simple parameter
                                use_workdrive=True
                            )
                            working_endpoint = "/files"
                            break
                        except Exception as e2:
                            logger.error(f"All endpoints failed. Last error: {e2}")
                            raise e2
                    continue

            # Parse response
            files_data = response.get("data", [])
            if not isinstance(files_data, list):
                files_data = [files_data] if files_data else []

            files = []
            for file_data in files_data:
                try:
                    # Handle different response formats
                    if isinstance(file_data, dict):
                        attributes = file_data.get("attributes", {})
                        if not attributes:
                            # Try direct access if no attributes wrapper
                            attributes = file_data

                        file_info = {
                            "id": file_data.get("id") or attributes.get("id"),
                            "name": attributes.get("name") or attributes.get("filename") or file_data.get("name"),
                            "type": attributes.get("type") or attributes.get("file_type", "file"),
                            "size": attributes.get("size") or attributes.get("size_in_bytes") or file_data.get("size"),
                            "created_at": attributes.get("created_time") or attributes.get("created_at") or file_data.get("created_time"),
                            "modified_at": attributes.get("modified_time") or attributes.get("modified_at") or file_data.get("modified_time")
                        }

                        # Only add if we have at least an ID and name
                        if file_info["id"] and file_info["name"]:
                            files.append(file_info)

                except Exception as e:
                    logger.warning(f"Invalid file data: {e}")
                    continue

            result = {
                "files": files,
                "total_count": len(files),
                "limit": limit,
                "offset": offset,
                "endpoint_used": working_endpoint,
                "raw_response": response  # Include raw response for debugging
            }

            logger.info(f"Listed {len(files)} files from WorkDrive using endpoint: {working_endpoint}")
            return result

        except Exception as e:
            logger.error(f"Failed to list files from WorkDrive: {e}")
            raise

    async def get_workdrive_info(self) -> Dict[str, Any]:
        """Get WorkDrive account information.

        Returns:
            WorkDrive account info
        """
        try:
            logger.info("Getting WorkDrive account information")

            # Try different info endpoints based on WorkDrive API documentation
            endpoints_to_try = [
                "/users/me",  # Current user info
                "/account",   # Account information
                "/workspaces/me",  # User workspace info
                "/teams/me"   # Team information
            ]

            for endpoint in endpoints_to_try:
                try:
                    response = await self.api_client.get(endpoint, use_workdrive=True)
                    logger.info(f"Successfully used info endpoint: {endpoint}")
                    break
                except Exception as e:
                    logger.warning(f"Info endpoint {endpoint} failed: {e}")
                    if endpoint == endpoints_to_try[-1]:
                        raise e
                    continue

            result = {
                "account_info": response,
                "endpoint_used": endpoint,
                "status": "connected"
            }

            logger.info("Retrieved WorkDrive account information")
            return result

        except Exception as e:
            logger.error(f"Failed to get WorkDrive info: {e}")
            raise

    async def list_team_files(
        self,
        team_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """List files from a specific team or folder in WorkDrive.

        Args:
            team_id: WorkDrive team ID (extracted from URL)
            folder_id: Specific folder ID to list files from
            limit: Maximum number of files to return

        Returns:
            List of files from the specified team/folder
        """
        try:
            logger.info(f"Listing files from WorkDrive team: {team_id}, folder: {folder_id}")

            # Build endpoint based on provided parameters
            endpoints_to_try = []
            
            if folder_id:
                # Try folder-specific endpoints based on Joel Lipman's documentation
                endpoints_to_try.extend([
                    f"/teamfolders/{folder_id}/folders",
                    f"/files/{folder_id}/files",
                    f"/folders/{folder_id}/files"
                ])
            
            if team_id:
                # Try team-specific endpoints based on Joel Lipman's documentation
                # The team_id from URL might actually be a team folder ID
                endpoints_to_try.extend([
                    f"/teamfolders/{team_id}/folders",
                    f"/teamfolders/{team_id}/files"
                ])
            
            # Fallback to general endpoints
            endpoints_to_try.extend([
                "/files",
                "/folders"
            ])

            response = None
            working_endpoint = None

            for endpoint in endpoints_to_try:
                try:
                    # Add required headers for WorkDrive API
                    headers = {
                        "Accept": "application/vnd.api+json"
                    }
                    
                    # Start with no parameters to test basic endpoint access
                    params = None
                    if "/teamfolders/" not in endpoint and limit and limit > 0:
                        # Only add pagination for non-teamfolder endpoints
                        params = {
                            "page[limit]": min(limit, 50),
                            "page[offset]": 0
                        }
                    
                    response = await self.api_client.get(
                        endpoint,
                        params=params,
                        headers=headers,
                        use_workdrive=True
                    )

                    # If we get here, the endpoint worked
                    logger.info(f"Successfully used team/folder endpoint: {endpoint}")
                    working_endpoint = endpoint
                    break

                except Exception as e:
                    logger.warning(f"Team/folder endpoint {endpoint} failed: {e}")
                    continue

            if not response:
                # If all endpoints failed, try the regular list_files as fallback
                logger.info("All team/folder endpoints failed, falling back to regular file listing")
                return await self.list_files(limit=limit)

            # Parse response based on WorkDrive API format
            files_data = response.get("data", [])
            if not isinstance(files_data, list):
                files_data = [files_data] if files_data else []

            files = []
            for file_data in files_data:
                try:
                    if isinstance(file_data, dict):
                        # WorkDrive API uses 'attributes' structure
                        attributes = file_data.get("attributes", {})
                        if not attributes:
                            attributes = file_data

                        file_info = {
                            "id": file_data.get("id") or attributes.get("id"),
                            "name": attributes.get("name") or attributes.get("filename") or file_data.get("name"),
                            "type": file_data.get("type") or attributes.get("type", "file"),
                            "size": attributes.get("size") or attributes.get("size_in_bytes") or file_data.get("size"),
                            "created_at": attributes.get("created_time") or attributes.get("created_at") or file_data.get("created_time"),
                            "modified_at": attributes.get("modified_time") or attributes.get("modified_at") or file_data.get("modified_time"),
                            "is_folder": file_data.get("type") == "files" or attributes.get("type") == "folder"
                        }

                        if file_info["id"] and file_info["name"]:
                            files.append(file_info)

                except Exception as e:
                    logger.warning(f"Invalid file data: {e}")
                    continue

            result = {
                "files": files,
                "total_count": len(files),
                "team_id": team_id,
                "folder_id": folder_id,
                "limit": limit,
                "endpoint_used": working_endpoint
            }

            logger.info(f"Listed {len(files)} files from team/folder using endpoint: {working_endpoint}")
            return result

        except Exception as e:
            logger.error(f"Failed to list team/folder files: {e}")
            raise

    async def get_workspaces_and_teams(self) -> Dict[str, Any]:
        """Get available workspaces and teams from WorkDrive.

        Returns:
            Dictionary containing workspaces and teams information
        """
        try:
            logger.info("Getting WorkDrive workspaces and teams")

            # Try different endpoints to get workspace/team information
            endpoints_to_try = [
                "/workspaces",
                "/teamfolders",
                "/teams",
                "/me/workspaces",
                "/users/me/workspaces"
            ]

            results = {}
            
            for endpoint in endpoints_to_try:
                try:
                    headers = {
                        "Accept": "application/vnd.api+json"
                    }
                    
                    response = await self.api_client.get(
                        endpoint,
                        headers=headers,
                        use_workdrive=True
                    )

                    if response and response.get("data"):
                        results[endpoint] = response
                        logger.info(f"Successfully retrieved data from endpoint: {endpoint}")
                    
                except Exception as e:
                    logger.warning(f"Endpoint {endpoint} failed: {e}")
                    continue

            return {
                "workspaces_and_teams": results,
                "total_endpoints_tested": len(endpoints_to_try),
                "successful_endpoints": len(results)
            }

        except Exception as e:
            logger.error(f"Failed to get workspaces and teams: {e}")
            raise

    async def list_team_folders(self, team_id: Optional[str] = None) -> Dict[str, Any]:
        """List team folders from WorkDrive.

        Args:
            team_id: Optional team folder ID to get subfolders

        Returns:
            Dictionary containing team folders information
        """
        try:
            if team_id:
                logger.info(f"Listing team folders for team folder ID: {team_id}")
            else:
                logger.info("Discovering team folders and workspaces")

            # Try different endpoints based on Zoho WorkDrive API documentation
            endpoints_to_try = []
            
            # Start with user info to get workspace information
            endpoints_to_try.append("/users/me")
            
            if team_id:
                # If team_id provided, assume it's a team folder ID and get subfolders
                endpoints_to_try.extend([
                    f"/teamfolders/{team_id}/folders",
                    f"/files/{team_id}/files"  # Alternative if teamfolders doesn't work
                ])
            
            # Try to discover available team folders through different approaches
            # Note: Zoho WorkDrive API may not have a direct "list all team folders" endpoint
            
            team_folders = []
            successful_endpoints = 0
            results = {}
            
            for endpoint in endpoints_to_try:
                try:
                    # Required headers for Zoho WorkDrive API
                    headers = {
                        "Accept": "application/vnd.api+json"
                    }
                    
                    params = {}
                    if "/teamfolders/" in endpoint and not team_id:
                        # Skip team-specific endpoints if no team_id provided
                        continue
                    elif "/teamfolders/" in endpoint:
                        # Add pagination for team folder listings
                        params = {
                            "page[limit]": 50,
                            "page[offset]": 0
                        }
                    
                    response = await self.api_client.get(
                        endpoint,
                        params=params,
                        headers=headers,
                        use_workdrive=True
                    )
                    
                    if response and 'data' in response:
                        results[endpoint] = response
                        successful_endpoints += 1
                        
                        # Extract team folder information
                        data = response['data']
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    folder_info = self._extract_folder_info(item)
                                    if folder_info:
                                        team_folders.append(folder_info)
                        elif isinstance(data, dict):
                            # Single item response (like user info)
                            if endpoint == "/users/me":
                                # Extract workspace information from user data
                                self._extract_workspace_info(data, results, endpoint)
                            else:
                                folder_info = self._extract_folder_info(data)
                                if folder_info:
                                    team_folders.append(folder_info)
                        
                        logger.info(f"Successfully retrieved data from endpoint: {endpoint}")
                    
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} failed: {e}")
                    continue

            # Remove duplicates based on folder ID
            unique_folders = {}
            for folder in team_folders:
                folder_id = folder.get('id')
                if folder_id and folder_id not in unique_folders:
                    unique_folders[folder_id] = folder
            
            team_folders = list(unique_folders.values())

            # If no team folders found and no team_id was provided, 
            # try to provide helpful information about available workspaces
            if not team_folders and not team_id:
                logger.info("No team folders found directly, trying workspace discovery")
                workspace_info = await self._discover_workspaces()
                results.update(workspace_info)

            response = {
                "team_folders": team_folders,
                "total_count": len(team_folders),
                "successful_endpoints": successful_endpoints,
                "endpoint_results": results,
                "note": "Team folders in Zoho WorkDrive require specific team folder IDs. Use workspace discovery to find available team folder IDs." if not team_folders and not team_id else None
            }

            logger.info(f"Found {len(team_folders)} team folders from {successful_endpoints} endpoints")
            return response

        except Exception as e:
            logger.error(f"Failed to list team folders: {e}")
            raise

    def _extract_folder_info(self, folder_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract relevant folder information from API response.

        Args:
            folder_data: Raw folder data from API

        Returns:
            Processed folder information or None if invalid
        """
        try:
            folder_id = folder_data.get('id')
            if not folder_id:
                return None

            attributes = folder_data.get('attributes', {})
            
            folder_info = {
                'id': folder_id,
                'name': attributes.get('name', 'Unknown'),
                'type': folder_data.get('type', 'folder'),
                'created_time': attributes.get('created_time'),
                'modified_time': attributes.get('modified_time'),
                'is_team_folder': True
            }

            # Add additional attributes if available
            if 'parent_id' in attributes:
                folder_info['parent_id'] = attributes['parent_id']
            
            if 'description' in attributes:
                folder_info['description'] = attributes['description']
            
            if 'permissions' in attributes:
                folder_info['permissions'] = attributes['permissions']

            # Check if this is a team folder based on type or other indicators
            folder_type = folder_data.get('type', '').lower()
            if 'team' in folder_type or 'shared' in folder_type:
                folder_info['is_team_folder'] = True
            
            return folder_info

        except Exception as e:
            logger.debug(f"Failed to extract folder info: {e}")
            return None

    def _extract_workspace_info(self, user_data: Dict[str, Any], results: Dict[str, Any], endpoint: str) -> None:
        """Extract workspace information from user data.
        
        Args:
            user_data: User data from /users/me endpoint
            results: Results dictionary to update
            endpoint: The endpoint that provided this data
        """
        try:
            # Extract workspace/team information from user data
            attributes = user_data.get('attributes', {})
            
            # Look for workspace or team-related information
            workspace_info = {
                'user_id': user_data.get('id'),
                'user_name': attributes.get('name'),
                'email': attributes.get('email'),
                'role': attributes.get('role'),
                'workspace_count': attributes.get('workspace_count', 0),
                'team_count': attributes.get('team_count', 0)
            }
            
            # Add to results for debugging
            results[f"{endpoint}_workspace_info"] = workspace_info
            
        except Exception as e:
            logger.debug(f"Failed to extract workspace info: {e}")

    async def _discover_workspaces(self) -> Dict[str, Any]:
        """Try to discover available workspaces and team folders.
        
        Returns:
            Dictionary with discovery results
        """
        discovery_results = {}
        
        try:
            # Try alternative endpoints for workspace discovery
            discovery_endpoints = [
                "/files",  # List root files/folders
                "/privatefolders",  # Private folders
                "/sharedfolders"  # Shared folders
            ]
            
            for endpoint in discovery_endpoints:
                try:
                    headers = {
                        "Accept": "application/vnd.api+json"
                    }
                    
                    response = await self.api_client.get(
                        endpoint,
                        headers=headers,
                        use_workdrive=True
                    )
                    
                    if response and 'data' in response:
                        discovery_results[f"discovery_{endpoint}"] = response
                        logger.info(f"Discovery endpoint {endpoint} returned data")
                    
                except Exception as e:
                    logger.debug(f"Discovery endpoint {endpoint} failed: {e}")
                    continue
            
        except Exception as e:
            logger.debug(f"Workspace discovery failed: {e}")
        
        return discovery_results
