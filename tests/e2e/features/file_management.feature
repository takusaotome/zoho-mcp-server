Feature: ファイル管理機能
  As a developer using MCP
  I want to manage WorkDrive files
  So that I can access and upload project documents

  Background:
    Given the MCP server is running
    And I have valid WorkDrive API credentials
    And I have a test folder with ID "test_folder_123"

  Scenario: ファイル検索機能
    Given WorkDriveにテストファイルが存在する
    When "test document" でファイルを検索
    Then 検索結果が返される
    And ファイル名、ID、パスが含まれる

  Scenario: フォルダ指定でのファイル検索
    Given 特定のフォルダにファイルが存在する
    When フォルダID "test_folder_123" を指定してファイルを検索
    Then 指定フォルダ内のファイルのみ取得される
    And フォルダ外のファイルは除外される

  Scenario: ファイルダウンロード
    Given ダウンロード可能なファイルID "file_001"
    When downloadFileを実行
    Then プリサインドURLが返される
    And URLが有効期限内である
    And ファイルサイズが1GB以下である

  Scenario: レビューシートのアップロード
    Given アップロード対象のExcelファイル
    When uploadReviewSheetを実行
    Then ファイルが正常にアップロードされる
    And アップロードされたファイルIDが返される
    And ファイルが指定フォルダに保存される

  Scenario: Markdownファイルのアップロード
    Given アップロード対象のMarkdownファイル
    When uploadReviewSheetを実行
    Then Markdownファイルが正常にアップロードされる
    And 正しいMIMEタイプが設定される

  Scenario: 大容量ファイルのアップロード制限
    Given 1GBを超えるファイル
    When uploadReviewSheetを実行
    Then ファイルサイズエラーが返される
    And 適切なエラーメッセージが含まれる

  Scenario: 存在しないファイルのダウンロード
    Given 存在しないファイルID "nonexistent_file"
    When downloadFileを実行
    Then 404エラーが返される
    And 適切なエラーメッセージが含まれる

  Scenario: 無効なファイル形式のアップロード
    Given サポートされていないファイル形式
    When uploadReviewSheetを実行
    Then ファイル形式エラーが返される
    And サポートされている形式のリストが含まれる