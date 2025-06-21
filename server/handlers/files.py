"""File management handlers for Zoho WorkDrive API."""

import base64
import logging
from typing import Any, Dict, List, Optional

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
            endpoint = f"/workdrive/v1/files"
            
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
            
            # Build search endpoint
            endpoint = "/workdrive/v1/search"
            params = {"query": query}
            
            if folder_id:
                params["parent_id"] = folder_id
            
            # Make search request
            search_response = await self.api_client.get(
                endpoint,
                params=params,
                use_workdrive=True
            )
            
            # Parse search results
            files_data = search_response.get("data", [])
            files = []
            
            for file_data in files_data:
                try:
                    attributes = file_data.get("attributes", {})
                    file_info = FileInfo(
                        id=file_data.get("id"),
                        name=attributes.get("name"),
                        type=attributes.get("type"),
                        size=attributes.get("size_in_bytes"),
                        created_at=attributes.get("created_time"),
                        modified_at=attributes.get("modified_time")
                    )
                    files.append(file_info.model_dump())
                except Exception as e:
                    logger.warning(f"Invalid file data in search results: {e}")
                    continue
            
            result = {
                "query": query,
                "folder_id": folder_id,
                "files": files,
                "total_count": len(files),
                "search_time": search_response.get("search_time")
            }
            
            logger.info(f"Found {len(files)} files for query '{query}'")
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