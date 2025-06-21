Feature: タスク管理機能
  As a developer using Cursor IDE or Claude
  I want to manage Zoho Projects tasks through natural language
  So that I can efficiently track project progress

  Background:
    Given the MCP server is running
    And I have valid Zoho API credentials
    And I have a test project with ID "test_project_123"

  Scenario: 新規タスクの作成と確認
    Given 認証済みのMCPクライアント
    When "プロジェクト123に'テストタスク'を作成"というリクエストを送信
    Then タスクが正常に作成される
    And タスクIDが返される
    And listTasksでタスクが確認できる

  Scenario: タスクステータスの更新
    Given 既存のオープンタスク
    When タスクのステータスを"closed"に更新
    Then タスクのステータスが正常に更新される
    And getProjectSummaryで完了率が反映される

  Scenario: タスクの詳細情報取得
    Given タスクID "task_001" が存在する
    When getTaskDetailを実行
    Then タスクの詳細情報が取得できる
    And 説明、コメント、履歴が含まれる

  Scenario: プロジェクトサマリーの取得
    Given プロジェクトに複数のタスクが存在する
    When getProjectSummaryを実行
    Then 完了率が計算される
    And 遅延タスク数が表示される
    And 総タスク数が表示される

  Scenario: 無効なプロジェクトIDでのエラーハンドリング
    Given 無効なプロジェクトID "invalid_project"
    When listTasksを実行
    Then 適切なエラーメッセージが返される
    And エラーコードが設定される

  Scenario: レート制限の適切な処理
    Given MCPサーバーが稼働中
    When 短時間で大量のリクエストを送信
    Then レート制限が適用される
    And 429エラーまたは適切な制限メッセージが返される

  Scenario Outline: 異なるタスクステータスでのフィルタリング
    Given プロジェクトに様々なステータスのタスクが存在する
    When ステータス "<status>" でタスクをフィルタリング
    Then "<status>" ステータスのタスクのみ取得される

    Examples:
      | status   |
      | open     |
      | closed   |
      | overdue  |

  Scenario: タスクの担当者設定と更新
    Given 新規タスク作成リクエスト
    When 担当者を "test@example.com" に設定
    Then タスクが指定した担当者で作成される
    And 担当者情報が正しく保存される