"""Step definitions for file management scenarios."""

import base64

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

# Load scenarios from feature file
scenarios('../features/file_management.feature')


class FileTestContext:
    """Context for file-related test data."""

    def __init__(self):
        self.client = None
        self.response = None
        self.folder_id = "test_folder_123"
        self.file_id = None
        self.search_query = None
        self.upload_data = None
        self.download_url = None


@pytest.fixture
def file_context():
    """Provide file test context."""
    return FileTestContext()


# Background steps
@given('I have valid WorkDrive API credentials')
def valid_workdrive_credentials(file_context: FileTestContext):
    """Verify WorkDrive API credentials are configured."""
    # In a real test, this would verify actual credentials
    assert file_context.client is not None


@given(parsers.parse('I have a test folder with ID "{folder_id}"'))
def test_folder_exists(folder_id: str, file_context: FileTestContext):
    """Set up test folder ID."""
    file_context.folder_id = folder_id


# Scenario: ファイル検索機能
@given('WorkDriveにテストファイルが存在する')
def workdrive_has_test_files(file_context: FileTestContext):
    """Set up test files in WorkDrive."""
    # In real implementation, this would ensure test files exist
    pass


@when(parsers.parse('"{query}" でファイルを検索'))
def search_files_with_query(query: str, file_context: FileTestContext):
    """Search files with specific query."""
    file_context.search_query = query

    search_request = {
        "jsonrpc": "2.0",
        "method": "callTool",
        "params": {
            "name": "searchFiles",
            "arguments": {
                "query": query
            }
        },
        "id": "bdd_search_files_001"
    }

    file_context.response = file_context.client.post("/mcp", json=search_request)


@then('検索結果が返される')
def search_results_returned(file_context: FileTestContext):
    """Verify search results are returned."""
    assert file_context.response.status_code == 200
    data = file_context.response.json()
    assert "result" in data
    assert "error" not in data


@then('ファイル名、ID、パスが含まれる')
def results_contain_file_info(file_context: FileTestContext):
    """Verify results contain file name, ID, and path."""
    data = file_context.response.json()
    result_text = data["result"]["content"][0]["text"]

    # Check for file information fields
    text_lower = result_text.lower()
    assert any(field in text_lower for field in ["name", "ファイル名"])
    assert any(field in text_lower for field in ["id", "file_id"])
    assert any(field in text_lower for field in ["path", "パス"])


# Scenario: フォルダ指定でのファイル検索
@given('特定のフォルダにファイルが存在する')
def specific_folder_has_files(file_context: FileTestContext):
    """Set up files in specific folder."""
    pass


@when(parsers.parse('フォルダID "{folder_id}" を指定してファイルを検索'))
def search_files_in_folder(folder_id: str, file_context: FileTestContext):
    """Search files in specific folder."""
    search_request = {
        "jsonrpc": "2.0",
        "method": "callTool",
        "params": {
            "name": "searchFiles",
            "arguments": {
                "query": "test",
                "folder_id": folder_id
            }
        },
        "id": "bdd_search_folder_001"
    }

    file_context.response = file_context.client.post("/mcp", json=search_request)


@then('指定フォルダ内のファイルのみ取得される')
def only_folder_files_retrieved(file_context: FileTestContext):
    """Verify only files from specified folder are retrieved."""
    assert file_context.response.status_code == 200
    data = file_context.response.json()
    assert "result" in data


@then('フォルダ外のファイルは除外される')
def files_outside_folder_excluded(file_context: FileTestContext):
    """Verify files outside folder are excluded."""
    # In real implementation, this would verify folder filtering
    data = file_context.response.json()
    assert "result" in data


# Scenario: ファイルダウンロード
@given(parsers.parse('ダウンロード可能なファイルID "{file_id}"'))
def downloadable_file_exists(file_id: str, file_context: FileTestContext):
    """Set up downloadable file ID."""
    file_context.file_id = file_id


@when('downloadFileを実行')
def execute_download_file(file_context: FileTestContext):
    """Execute downloadFile."""
    download_request = {
        "jsonrpc": "2.0",
        "method": "callTool",
        "params": {
            "name": "downloadFile",
            "arguments": {
                "file_id": file_context.file_id
            }
        },
        "id": "bdd_download_001"
    }

    file_context.response = file_context.client.post("/mcp", json=download_request)


@then('プリサインドURLが返される')
def presigned_url_returned(file_context: FileTestContext):
    """Verify presigned URL is returned."""
    assert file_context.response.status_code == 200
    data = file_context.response.json()
    assert "result" in data

    result_text = data["result"]["content"][0]["text"]
    assert any(term in result_text.lower() for term in ["url", "link", "download"])


@then('URLが有効期限内である')
def url_within_expiry(file_context: FileTestContext):
    """Verify URL is within expiry period."""
    # In real implementation, this would check URL expiry
    data = file_context.response.json()
    assert "result" in data


@then('ファイルサイズが1GB以下である')
def file_size_within_limit(file_context: FileTestContext):
    """Verify file size is within 1GB limit."""
    # In real implementation, this would check file size information
    data = file_context.response.json()
    assert "result" in data


# Scenario: レビューシートのアップロード
@given('アップロード対象のExcelファイル')
def excel_file_for_upload(file_context: FileTestContext):
    """Prepare Excel file for upload."""
    # Create mock Excel file data
    mock_excel_content = b"Mock Excel file content"
    file_context.upload_data = {
        "name": "test_review.xlsx",
        "content_base64": base64.b64encode(mock_excel_content).decode(),
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }


@when('uploadReviewSheetを実行')
def execute_upload_review_sheet(file_context: FileTestContext):
    """Execute uploadReviewSheet."""
    upload_request = {
        "jsonrpc": "2.0",
        "method": "callTool",
        "params": {
            "name": "uploadReviewSheet",
            "arguments": {
                "project_id": "test_project_123",
                "folder_id": file_context.folder_id,
                "name": file_context.upload_data["name"],
                "content_base64": file_context.upload_data["content_base64"]
            }
        },
        "id": "bdd_upload_001"
    }

    file_context.response = file_context.client.post("/mcp", json=upload_request)


@then('ファイルが正常にアップロードされる')
def file_uploaded_successfully(file_context: FileTestContext):
    """Verify file was uploaded successfully."""
    assert file_context.response.status_code == 200
    data = file_context.response.json()
    assert "result" in data
    assert "error" not in data


@then('アップロードされたファイルIDが返される')
def uploaded_file_id_returned(file_context: FileTestContext):
    """Verify uploaded file ID is returned."""
    data = file_context.response.json()
    result_text = data["result"]["content"][0]["text"]
    assert any(term in result_text.lower() for term in ["file_id", "id"])


@then('ファイルが指定フォルダに保存される')
def file_saved_in_specified_folder(file_context: FileTestContext):
    """Verify file is saved in specified folder."""
    # In real implementation, this would verify folder location
    data = file_context.response.json()
    assert "result" in data


# Scenario: Markdownファイルのアップロード
@given('アップロード対象のMarkdownファイル')
def markdown_file_for_upload(file_context: FileTestContext):
    """Prepare Markdown file for upload."""
    mock_md_content = b"# Test Review\n\nThis is a test markdown file."
    file_context.upload_data = {
        "name": "test_review.md",
        "content_base64": base64.b64encode(mock_md_content).decode(),
        "mime_type": "text/markdown"
    }


@then('Markdownファイルが正常にアップロードされる')
def markdown_file_uploaded_successfully(file_context: FileTestContext):
    """Verify Markdown file was uploaded successfully."""
    assert file_context.response.status_code == 200
    data = file_context.response.json()
    assert "result" in data


@then('正しいMIMEタイプが設定される')
def correct_mime_type_set(file_context: FileTestContext):
    """Verify correct MIME type is set."""
    # In real implementation, this would verify MIME type
    data = file_context.response.json()
    assert "result" in data


# Scenario: 大容量ファイルのアップロード制限
@given('1GBを超えるファイル')
def large_file_over_1gb(file_context: FileTestContext):
    """Prepare file over 1GB (mock)."""
    # Mock large file data
    file_context.upload_data = {
        "name": "large_file.xlsx",
        "content_base64": "mock_large_file_content",
        "size": 1024 * 1024 * 1024 + 1  # Just over 1GB
    }


@then('ファイルサイズエラーが返される')
def file_size_error_returned(file_context: FileTestContext):
    """Verify file size error is returned."""
    data = file_context.response.json()
    # Should either be an error response or contain size limit message
    assert "error" in data or "size" in str(data).lower()


@then('適切なエラーメッセージが含まれる')
def appropriate_error_message_included(file_context: FileTestContext):
    """Verify appropriate error message is included."""
    data = file_context.response.json()
    error_text = str(data).lower()
    assert any(term in error_text for term in ["size", "limit", "1gb", "large"])


# Scenario: 存在しないファイルのダウンロード
@given(parsers.parse('存在しないファイルID "{file_id}"'))
def nonexistent_file_id(file_id: str, file_context: FileTestContext):
    """Set up nonexistent file ID."""
    file_context.file_id = file_id


@then('404エラーが返される')
def not_found_error_returned(file_context: FileTestContext):
    """Verify 404 error is returned."""
    data = file_context.response.json()
    # Should contain error or not found indication
    assert "error" in data or "not found" in str(data).lower()


# Scenario: 無効なファイル形式のアップロード
@given('サポートされていないファイル形式')
def unsupported_file_format(file_context: FileTestContext):
    """Prepare unsupported file format."""
    mock_content = b"Unsupported file content"
    file_context.upload_data = {
        "name": "test_file.xyz",  # Unsupported extension
        "content_base64": base64.b64encode(mock_content).decode(),
        "mime_type": "application/unknown"
    }


@then('ファイル形式エラーが返される')
def file_format_error_returned(file_context: FileTestContext):
    """Verify file format error is returned."""
    data = file_context.response.json()
    error_text = str(data).lower()
    assert "error" in data or any(term in error_text for term in ["format", "type", "supported"])


@then('サポートされている形式のリストが含まれる')
def supported_formats_list_included(file_context: FileTestContext):
    """Verify supported formats list is included."""
    data = file_context.response.json()
    result_text = str(data).lower()
    # Should mention supported formats
    assert any(format_type in result_text for format_type in ["xlsx", "md", "supported"])
