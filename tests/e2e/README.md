# E2E テストガイド

このディレクトリには、Zoho MCP Serverの包括的なエンドツーエンド（E2E）テストが含まれています。

## テストファイル構成

### 🔧 基本テスト
- `test_real_api_integration.py` - 実際のZoho APIを使用した統合テスト
- `test_performance.py` - パフォーマンステスト（pytest版）
- `conftest.py` - pytest設定とフィクスチャ

### 📋 BDDテスト
- `features/task_management.feature` - タスク管理のBDDシナリオ
- `features/file_management.feature` - ファイル管理のBDDシナリオ
- `step_definitions/test_task_steps.py` - タスク管理のステップ定義
- `step_definitions/test_file_steps.py` - ファイル管理のステップ定義

### ⚡ パフォーマンステスト
- `locustfile.py` - Locustベースの負荷テスト
- `test_performance.py` - pytestベースのパフォーマンステスト

### 🔄 ワークフローテスト
- `test_workflow_scenarios.py` - 複数ツール連携のワークフローテスト

## テスト実行方法

### 1. 基本的なE2Eテスト
```bash
# 全E2Eテスト実行
pytest tests/e2e/ -v

# モックを使用したテストのみ
pytest tests/e2e/ -v -m "not real_api"

# 特定のテストファイルのみ
pytest tests/e2e/test_workflow_scenarios.py -v
```

### 2. 実際のAPI連携テスト
```bash
# 環境変数を設定して実行
export ZOHO_E2E_TESTS_ENABLED=true
export ZOHO_TEST_PROJECT_ID=your_test_project_id
export ZOHO_TEST_FOLDER_ID=your_test_folder_id

pytest tests/e2e/test_real_api_integration.py -v
```

### 3. BDDテスト実行
```bash
# pytest-bddが必要
pip install pytest-bdd

# BDDテスト実行
pytest tests/e2e/step_definitions/ -v --bdd

# 特定のフィーチャーのみ
pytest tests/e2e/step_definitions/test_task_steps.py -v
```

### 4. パフォーマンステスト

#### pytest版
```bash
# 基本パフォーマンステスト
pytest tests/e2e/test_performance.py -v -m "not slow"

# 全パフォーマンステスト（時間がかかります）
pytest tests/e2e/test_performance.py -v

# ストレステスト
pytest tests/e2e/test_performance.py -v -m stress
```

#### Locust版
```bash
# Locustが必要
pip install locust

# Web UIでテスト実行
locust -f tests/e2e/locustfile.py --host http://localhost:8000

# ヘッドレスでテスト実行（5分間、最大10ユーザー）
locust -f tests/e2e/locustfile.py --headless -u 10 -r 2 -t 5m --host http://localhost:8000

# ストレステスト
locust -f tests/e2e/locustfile.py HighLoadUser --headless -u 50 -r 10 -t 10m --host http://localhost:8000

# スパイクテスト
locust -f tests/e2e/locustfile.py SpikeTestUser --headless -u 100 -r 50 -t 2m --host http://localhost:8000
```

## テストマーカー

以下のpytestマーカーを使用してテストを分類しています：

- `@pytest.mark.e2e` - E2Eテスト
- `@pytest.mark.slow` - 実行時間が長いテスト
- `@pytest.mark.real_api` - 実際のAPI使用テスト
- `@pytest.mark.performance` - パフォーマンステスト
- `@pytest.mark.stress` - ストレステスト
- `@pytest.mark.integration` - 統合テスト

### マーカーを使った実行例
```bash
# E2Eテストのみ
pytest -m e2e

# 遅いテストを除外
pytest -m "not slow"

# パフォーマンステストのみ
pytest -m performance

# 実際のAPIテストを除外
pytest -m "not real_api"
```

## 環境設定

### 必要な環境変数

#### 基本設定
- `TESTING=true` - テストモード有効化
- `LOG_LEVEL=DEBUG` - ログレベル設定

#### 実際のAPI連携テスト用
- `ZOHO_E2E_TESTS_ENABLED=true` - 実APIテスト有効化
- `ZOHO_TEST_PROJECT_ID` - テスト用プロジェクトID
- `ZOHO_TEST_FOLDER_ID` - テスト用フォルダID
- `ZOHO_CLIENT_ID` - Zoho OAuth クライアントID
- `ZOHO_CLIENT_SECRET` - Zoho OAuth クライアントシークレット
- `ZOHO_REFRESH_TOKEN` - Zoho リフレッシュトークン

#### パフォーマンステスト用
- `RUN_SLOW_TESTS=true` - 遅いテストの実行許可
- `RUN_STRESS_TESTS=true` - ストレステストの実行許可

### 環境変数設定例
```bash
# .env.e2e ファイルを作成
cat > .env.e2e << EOF
TESTING=true
LOG_LEVEL=DEBUG
ZOHO_E2E_TESTS_ENABLED=false
ZOHO_TEST_PROJECT_ID=test_project_123
ZOHO_TEST_FOLDER_ID=test_folder_123
RUN_SLOW_TESTS=false
RUN_STRESS_TESTS=false
EOF

# 環境変数読み込み
source .env.e2e
```

## テストシナリオ

### 1. タスク管理ワークフロー
- プロジェクト作成 → タスク作成 → 進捗更新 → 完了確認
- バグ報告 → 調査 → 修正 → 検証 → クローズ
- コードレビュー → フィードバック → 修正 → 承認

### 2. ファイル管理ワークフロー
- ドキュメント検索 → ダウンロード → 編集 → アップロード
- レビューシート作成 → アップロード → 共有 → フィードバック

### 3. プロジェクト管理ワークフロー
- プロジェクト開始 → タスク計画 → 実行 → 監視 → 完了

### 4. エラー処理とリカバリ
- 無効なデータでのエラー → 適切なエラーメッセージ → 回復手順

## パフォーマンス要件

### SLA要件
- 平均レスポンス時間: < 500ms
- 95パーセンタイル: < 500ms
- エラー率: < 0.1%
- 可用性: 99.5%

### 負荷テスト目標
- 同時ユーザー数: 100ユーザー
- スループット: 100 req/sec
- 持続時間: 10分間

## トラブルシューティング

### よくある問題

#### 1. 実APIテストの失敗
```bash
# 原因: 認証情報が設定されていない
# 解決: 環境変数を正しく設定
export ZOHO_CLIENT_ID=your_client_id
export ZOHO_CLIENT_SECRET=your_client_secret
export ZOHO_REFRESH_TOKEN=your_refresh_token
```

#### 2. パフォーマンステストのタイムアウト
```bash
# 原因: サーバーが起動していない
# 解決: サーバーを起動してからテスト実行
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

#### 3. BDDテストの実行エラー
```bash
# 原因: pytest-bddがインストールされていない
# 解決: 依存関係をインストール
pip install pytest-bdd
```

### ログとデバッグ

#### デバッグモードでテスト実行
```bash
# 詳細ログ付きで実行
pytest tests/e2e/ -v -s --log-cli-level=DEBUG

# 失敗したテストのみ再実行
pytest tests/e2e/ --lf -v

# 特定のテストをデバッグ
pytest tests/e2e/test_workflow_scenarios.py::TestWorkflowScenarios::test_complete_project_workflow -v -s
```

## CI/CD統合

### GitHub Actions設定例
```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run E2E tests (mock)
        run: pytest tests/e2e/ -v -m "not real_api and not slow"
      
      - name: Run performance tests
        run: pytest tests/e2e/test_performance.py -v -m "not stress"
        if: github.event_name == 'push'
```

## 継続的改善

### メトリクス収集
- テスト実行時間の監視
- カバレッジレポートの生成
- パフォーマンス指標の追跡

### 定期的なレビュー
- 週次: テスト結果の確認
- 月次: パフォーマンス基準の見直し
- 四半期: テストシナリオの更新

## 貢献方法

### 新しいテストの追加
1. 適切なファイルにテストを追加
2. 必要に応じてマーカーを設定
3. ドキュメントを更新
4. プルリクエストを作成

### テストの改善
1. 既存テストの品質向上
2. エラーハンドリングの強化
3. パフォーマンスの最適化
4. 可読性の向上