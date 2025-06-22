"""Tests for files handler module."""

import base64
from unittest.mock import AsyncMock, patch

import pytest

from server.handlers.files import FileHandler, FileInfo


class TestFileInfoModel:
    """Test FileInfo model validation."""

    def test_file_info_model_creation_with_required_fields(self):
        """Test creating FileInfo with required fields only."""
        file_info = FileInfo(
            id="file123",
            name="test.txt",
            type="file"
        )
        assert file_info.id == "file123"
        assert file_info.name == "test.txt"
        assert file_info.type == "file"
        assert file_info.size is None
        assert file_info.created_at is None
        assert file_info.modified_at is None
        assert file_info.download_url is None

    def test_file_info_model_creation_with_all_fields(self):
        """Test creating FileInfo with all fields."""
        file_info = FileInfo(
            id="file123",
            name="test.txt",
            type="file",
            size=1024,
            created_at="2023-12-01T10:00:00Z",
            modified_at="2023-12-02T11:00:00Z",
            download_url="https://example.com/download/file123"
        )

        assert file_info.id == "file123"
        assert file_info.name == "test.txt"
        assert file_info.type == "file"
        assert file_info.size == 1024
        assert file_info.created_at == "2023-12-01T10:00:00Z"
        assert file_info.modified_at == "2023-12-02T11:00:00Z"
        assert file_info.download_url == "https://example.com/download/file123"


class TestFileHandler:
    """Test FileHandler class."""

    @pytest.fixture
    def handler(self):
        """Create FileHandler instance with mocked API client."""
        with patch('server.handlers.files.ZohoAPIClient'):
            handler = FileHandler()
            handler.api_client = AsyncMock()
            return handler

    @pytest.mark.asyncio
    async def test_download_file_success(self, handler):
        """Test successful file download."""
        # Mock file metadata response
        mock_file_response = {
            "data": {
                "id": "file123",
                "attributes": {
                    "name": "test.txt",
                    "size_in_bytes": 1024,
                    "type": "file"
                }
            }
        }

        # Mock download URL response
        mock_download_response = {
            "download_url": "https://example.com/download/file123",
            "expires_at": "2023-12-01T12:00:00Z"
        }

        handler.api_client.get.side_effect = [mock_file_response, mock_download_response]

        result = await handler.download_file("file123")

        # Verify API calls
        assert handler.api_client.get.call_count == 2
        handler.api_client.get.assert_any_call("/workdrive/v1/files/file123", use_workdrive=True)
        handler.api_client.get.assert_any_call("/workdrive/v1/files/file123/download", use_workdrive=True)

        # Verify result
        assert result["file_id"] == "file123"
        assert result["name"] == "test.txt"
        assert result["size"] == 1024
        assert result["type"] == "file"
        assert result["download_url"] == "https://example.com/download/file123"
        assert result["expires_at"] == "2023-12-01T12:00:00Z"
        assert result["status"] == "ready_for_download"

    @pytest.mark.asyncio
    async def test_download_file_no_download_url(self, handler):
        """Test file download when no download URL is returned."""
        mock_file_response = {
            "data": {
                "id": "file123",
                "attributes": {"name": "test.txt"}
            }
        }

        mock_download_response = {}  # No download_url

        handler.api_client.get.side_effect = [mock_file_response, mock_download_response]

        with pytest.raises(Exception, match="Failed to get download URL"):
            await handler.download_file("file123")

    @pytest.mark.asyncio
    async def test_download_file_api_error(self, handler):
        """Test file download with API error."""
        handler.api_client.get.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            await handler.download_file("file123")

    @pytest.mark.asyncio
    async def test_upload_review_sheet_success(self, handler):
        """Test successful review sheet upload."""
        # Create test file content
        test_content = "Test file content"
        content_base64 = base64.b64encode(test_content.encode()).decode()

        mock_upload_response = {
            "data": {
                "id": "uploaded_file_123",
                "attributes": {
                    "created_time": "2023-12-01T10:00:00Z"
                }
            }
        }

        handler.api_client.post.return_value = mock_upload_response

        result = await handler.upload_review_sheet(
            "proj123",
            "folder456",
            "review.txt",
            content_base64
        )

        # Verify API call
        handler.api_client.post.assert_called_once()
        call_args = handler.api_client.post.call_args
        assert call_args[0][0] == "/workdrive/v1/files"
        assert call_args[1]["use_workdrive"] is True
        assert call_args[1]["data"]["parent_id"] == "folder456"
        assert call_args[1]["data"]["filename"] == "review.txt"
        assert call_args[1]["files"]["content"][0] == "review.txt"

        # Verify result
        assert result["file_id"] == "uploaded_file_123"
        assert result["name"] == "review.txt"
        assert result["folder_id"] == "folder456"
        assert result["project_id"] == "proj123"
        assert result["size"] == len(test_content)
        assert result["status"] == "uploaded"
        assert result["upload_time"] == "2023-12-01T10:00:00Z"

    @pytest.mark.asyncio
    async def test_upload_review_sheet_invalid_base64(self, handler):
        """Test upload with invalid base64 content."""
        # Use a truly invalid base64 string that will cause binascii.Error
        invalid_base64 = "invalid base64 with spaces and invalid chars!!!"

        with pytest.raises(ValueError, match="Invalid base64 content"):
            await handler.upload_review_sheet(
                "proj123",
                "folder456",
                "review.txt",
                invalid_base64
            )

    @pytest.mark.asyncio
    async def test_upload_review_sheet_file_too_large(self, handler):
        """Test upload with file exceeding size limit."""
        # Create content larger than 1GB
        large_content = "x" * (1024 * 1024 * 1024 + 1)  # 1GB + 1 byte
        content_base64 = base64.b64encode(large_content.encode()).decode()

        with pytest.raises(ValueError, match="File too large"):
            await handler.upload_review_sheet(
                "proj123",
                "folder456",
                "large_file.txt",
                content_base64
            )

    @pytest.mark.asyncio
    async def test_upload_review_sheet_no_file_id(self, handler):
        """Test upload when no file ID is returned."""
        test_content = "Test file content"
        content_base64 = base64.b64encode(test_content.encode()).decode()

        mock_upload_response = {"data": {}}  # No file ID
        handler.api_client.post.return_value = mock_upload_response

        with pytest.raises(Exception, match="Upload failed: No file ID returned"):
            await handler.upload_review_sheet(
                "proj123",
                "folder456",
                "review.txt",
                content_base64
            )

    @pytest.mark.asyncio
    async def test_upload_review_sheet_api_error(self, handler):
        """Test upload with API error."""
        test_content = "Test file content"
        content_base64 = base64.b64encode(test_content.encode()).decode()

        handler.api_client.post.side_effect = Exception("Upload API Error")

        with pytest.raises(Exception, match="Upload API Error"):
            await handler.upload_review_sheet(
                "proj123",
                "folder456",
                "review.txt",
                content_base64
            )

    @pytest.mark.asyncio
    async def test_search_files_success(self, handler):
        """Test successful file search."""
        mock_search_response = {
            "data": [
                {
                    "id": "file1",
                    "attributes": {
                        "name": "document1.txt",
                        "type": "file",
                        "size_in_bytes": 1024,
                        "created_time": "2023-12-01T10:00:00Z",
                        "modified_time": "2023-12-02T11:00:00Z"
                    }
                },
                {
                    "id": "file2",
                    "attributes": {
                        "name": "document2.txt",
                        "type": "file",
                        "size_in_bytes": 2048,
                        "created_time": "2023-12-01T11:00:00Z",
                        "modified_time": "2023-12-02T12:00:00Z"
                    }
                }
            ],
            "search_time": 0.5
        }

        handler.api_client.get.return_value = mock_search_response

        result = await handler.search_files("document", "folder123")

        # Verify API call
        handler.api_client.get.assert_called_once_with(
            "/workdrive/v1/search",
            params={"query": "document", "parent_id": "folder123"},
            use_workdrive=True
        )

        # Verify result
        assert result["query"] == "document"
        assert result["folder_id"] == "folder123"
        assert result["total_count"] == 2
        assert result["search_time"] == 0.5
        assert len(result["files"]) == 2

        # Verify first file
        file1 = result["files"][0]
        assert file1["id"] == "file1"
        assert file1["name"] == "document1.txt"
        assert file1["type"] == "file"
        assert file1["size"] == 1024

    @pytest.mark.asyncio
    async def test_search_files_without_folder(self, handler):
        """Test file search without folder restriction."""
        mock_search_response = {"data": [], "search_time": 0.1}
        handler.api_client.get.return_value = mock_search_response

        result = await handler.search_files("document")

        # Should not include parent_id in params
        handler.api_client.get.assert_called_once_with(
            "/workdrive/v1/search",
            params={"query": "document"},
            use_workdrive=True
        )

        assert result["folder_id"] is None

    @pytest.mark.asyncio
    async def test_search_files_with_invalid_file_data(self, handler):
        """Test search with invalid file data in results."""
        mock_search_response = {
            "data": [
                {
                    "id": "file1",
                    "attributes": {
                        "name": "valid_file.txt",
                        "type": "file"
                    }
                },
                {
                    # Missing required fields
                    "attributes": {
                        "name": "invalid_file.txt"
                        # Missing type
                    }
                },
                {
                    "id": "file2",
                    "attributes": {
                        "name": "another_valid_file.txt",
                        "type": "file"
                    }
                }
            ]
        }

        handler.api_client.get.return_value = mock_search_response

        with patch('server.handlers.files.logger.warning') as mock_warning:
            result = await handler.search_files("test")

            # Should skip invalid file data and log warning
            assert len(result["files"]) == 2
            assert result["files"][0]["id"] == "file1"
            assert result["files"][1]["id"] == "file2"
            mock_warning.assert_called()

    @pytest.mark.asyncio
    async def test_search_files_api_error(self, handler):
        """Test search with API error."""
        handler.api_client.get.side_effect = Exception("Search API Error")

        with pytest.raises(Exception, match="Search API Error"):
            await handler.search_files("document")

    @pytest.mark.asyncio
    async def test_get_file_info_success(self, handler):
        """Test successful file info retrieval."""
        mock_response = {
            "data": {
                "id": "file123",
                "attributes": {
                    "name": "test.txt",
                    "type": "file",
                    "size_in_bytes": 1024,
                    "created_time": "2023-12-01T10:00:00Z",
                    "modified_time": "2023-12-02T11:00:00Z",
                    "parent_id": "folder456",
                    "status": "active"
                },
                "permissions": {
                    "read": True,
                    "write": False
                }
            }
        }

        handler.api_client.get.return_value = mock_response

        result = await handler.get_file_info("file123")

        # Verify API call
        handler.api_client.get.assert_called_once_with(
            "/workdrive/v1/files/file123",
            use_workdrive=True
        )

        # Verify result
        assert result["id"] == "file123"
        assert result["name"] == "test.txt"
        assert result["type"] == "file"
        assert result["size"] == 1024
        assert result["created_at"] == "2023-12-01T10:00:00Z"
        assert result["modified_at"] == "2023-12-02T11:00:00Z"
        assert result["parent_id"] == "folder456"
        assert result["status"] == "active"
        assert result["permissions"]["read"] is True
        assert result["permissions"]["write"] is False

    @pytest.mark.asyncio
    async def test_get_file_info_api_error(self, handler):
        """Test file info retrieval with API error."""
        handler.api_client.get.side_effect = Exception("File Info API Error")

        with pytest.raises(Exception, match="File Info API Error"):
            await handler.get_file_info("file123")

    @pytest.mark.asyncio
    async def test_list_folder_contents_success(self, handler):
        """Test successful folder contents listing."""
        mock_response = {
            "data": [
                {
                    "id": "file1",
                    "attributes": {
                        "name": "document.txt",
                        "type": "file",
                        "size_in_bytes": 1024,
                        "created_time": "2023-12-01T10:00:00Z",
                        "modified_time": "2023-12-02T11:00:00Z"
                    }
                },
                {
                    "id": "folder1",
                    "attributes": {
                        "name": "subfolder",
                        "type": "folder",
                        "created_time": "2023-12-01T09:00:00Z",
                        "modified_time": "2023-12-01T09:00:00Z"
                    }
                }
            ]
        }

        handler.api_client.get.return_value = mock_response

        result = await handler.list_folder_contents("folder123", "file")

        # Verify API call
        handler.api_client.get.assert_called_once_with(
            "/workdrive/v1/files/folder123/files",
            params={"type": "file"},
            use_workdrive=True
        )

        # Verify result
        assert result["folder_id"] == "folder123"
        assert result["total_count"] == 2
        assert result["file_type_filter"] == "file"
        assert len(result["files"]) == 2

        # Verify first item
        item1 = result["files"][0]
        assert item1["id"] == "file1"
        assert item1["name"] == "document.txt"
        assert item1["type"] == "file"
        assert item1["size"] == 1024

    @pytest.mark.asyncio
    async def test_list_folder_contents_without_type_filter(self, handler):
        """Test folder listing without file type filter."""
        mock_response = {"data": []}
        handler.api_client.get.return_value = mock_response

        result = await handler.list_folder_contents("folder123")

        # Should not include type in params
        handler.api_client.get.assert_called_once_with(
            "/workdrive/v1/files/folder123/files",
            params={},
            use_workdrive=True
        )

        assert result["file_type_filter"] is None

    @pytest.mark.asyncio
    async def test_list_folder_contents_with_invalid_file_data(self, handler):
        """Test folder listing with missing file data."""
        mock_response = {
            "data": [
                {
                    "id": "file1",
                    "attributes": {
                        "name": "valid_file.txt",
                        "type": "file"
                    }
                },
                {
                    # Missing id field - this gets stored as None, not skipped
                    "attributes": {
                        "name": "invalid_file.txt",
                        "type": "file"
                    }
                },
                {
                    "id": "file2",
                    "attributes": {
                        "name": "another_valid_file.txt",
                        "type": "file"
                    }
                }
            ]
        }

        handler.api_client.get.return_value = mock_response

        result = await handler.list_folder_contents("folder123")

        # Folder listing doesn't validate with FileInfo model, so all data is included
        assert len(result["files"]) == 3
        assert result["files"][0]["id"] == "file1"
        assert result["files"][1]["id"] is None  # Missing id becomes None
        assert result["files"][1]["name"] == "invalid_file.txt"
        assert result["files"][2]["id"] == "file2"

    @pytest.mark.asyncio
    async def test_list_folder_contents_api_error(self, handler):
        """Test folder listing with API error."""
        handler.api_client.get.side_effect = Exception("Folder API Error")

        with pytest.raises(Exception, match="Folder API Error"):
            await handler.list_folder_contents("folder123")
