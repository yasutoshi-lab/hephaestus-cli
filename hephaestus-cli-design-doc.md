# Hephaestus-CLI 詳細設計書

## 1. システムアーキテクチャ

### 1.1 システム構成図

```
┌─────────────────────────────────────────────────────────┐
│                    Hephaestus-CLI                       │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐                                       │
│  │   CLI Entry  │ (/init, /attach, /kill)               │
│  └──────┬───────┘                                       │
│         │                                                │
│  ┌──────▼───────────────────────────────┐              │
│  │    Session Manager (tmux wrapper)     │              │
│  └──────┬───────────────────────────────┘              │
│         │                                                │
│  ┌──────▼────────┬──────────┬──────────┬──────────┐    │
│  │    Master     │ Worker-1 │ Worker-2 │ Worker-N │    │
│  │ (claude-code) │  (c-c)   │  (c-c)   │  (c-c)   │    │
│  └───────────────┴──────────┴──────────┴──────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │           hephaestus-work/                       │    │
│  │  ├── config.yaml                                 │    │
│  │  ├── cache/                                      │    │
│  │  ├── tasks/                                      │    │
│  │  ├── checkpoints/                                │    │
│  │  ├── progress/                                   │    │
│  │  └── logs/                                       │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 1.2 コンポーネント設計

#### 1.2.1 CLI Entry Point
- **責務**: コマンドライン引数の解析と適切なサブコマンドへのルーティング
- **実装**: Python Click または argparse を使用

#### 1.2.2 Session Manager
- **責務**: tmuxセッションの作成、管理、削除
- **実装**: tmux Python wrapper (libtmux) を使用

#### 1.2.3 Agent Controller
- **責務**: Master/Workerエージェントのライフサイクル管理
- **実装**: subprocess管理とプロセス監視

#### 1.2.4 Communication Manager
- **責務**: Master-Worker間の通信制御
- **実装**: Markdownファイルベースのメッセージキュー

#### 1.2.5 Health Monitor
- **責務**: エージェントの死活監視とエラーハンドリング
- **実装**: 30秒間隔のヘルスチェック実装

## 2. ディレクトリ構造

### 2.1 プロジェクト構造
```
hephaestus-cli/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── hephaestus/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py                  # CLIエントリーポイント
│       ├── config.py                # 設定管理
│       ├── session_manager.py      # tmuxセッション管理
│       ├── agent_controller.py     # エージェント制御
│       ├── communication.py        # Master-Worker通信
│       ├── health_monitor.py       # 死活監視
│       ├── task_manager.py         # タスク管理
│       └── utils/
│           ├── __init__.py
│           ├── file_utils.py
│           └── logger.py
├── tests/
│   └── ...
└── templates/
    ├── config.yaml.template
    └── task.md.template
```

### 2.2 作業ディレクトリ構造
```
hephaestus-work/
├── config.yaml                     # 設定ファイル
├── cache/
│   ├── agent_states/               # エージェント状態キャッシュ
│   │   ├── master.json
│   │   └── worker-{id}.json
│   └── rate_limits/                # レート制限情報
├── tasks/
│   ├── pending/                    # 未実行タスク
│   ├── in_progress/                # 実行中タスク
│   └── completed/                  # 完了タスク
├── checkpoints/
│   └── {timestamp}/                # チェックポイントデータ
├── progress/
│   ├── master_status.md           # Master進捗
│   └── worker_{id}_status.md      # Worker進捗
├── logs/
│   ├── master.log
│   ├── worker_{id}.log
│   └── system.log
└── communication/
    ├── master_to_worker/           # Master→Worker通信
    └── worker_to_master/           # Worker→Master通信
```

## 3. 詳細仕様

### 3.1 設定ファイル (config.yaml)

```yaml
# hephaestus-work/config.yaml
version: 1.0
agents:
  master:
    enabled: true
    command: "claude-code"
    args: []
  workers:
    count: 3  # Worker数（変更可能）
    command: "claude-code"
    args: []
    
monitoring:
  health_check_interval: 30  # 秒
  retry_attempts: 3
  retry_delay: 5  # 秒
  
communication:
  format: "markdown"
  encoding: "utf-8"
  
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
tmux:
  session_name: "hephaestus"
  layout: "tiled"  # even-horizontal, even-vertical, main-horizontal, main-vertical, tiled
```

### 3.2 通信プロトコル

#### 3.2.1 メッセージフォーマット
```markdown
# Task Message
---
metadata:
  id: "{uuid}"
  type: "task|status|result|error"
  from: "master|worker-{id}"
  to: "master|worker-{id}"
  timestamp: "{iso8601}"
  priority: "high|medium|low"
---

## Content

{message_content}

---
checksum: "{md5}"
```

#### 3.2.2 タスク割り当てフロー
```markdown
# Task Assignment
---
metadata:
  id: "task-001"
  type: "task"
  from: "master"
  to: "worker-1"
  timestamp: "2024-01-01T00:00:00Z"
  priority: "high"
---

## Task Description

### Objective
{タスクの目的}

### Requirements
- {要件1}
- {要件2}

### Expected Output
{期待される成果物}

### Deadline
{締切}

---
checksum: "a1b2c3d4"
```

### 3.3 死活監視仕様

#### 3.3.1 ヘルスチェック実装
```python
# health_monitor.py の主要メソッド
class HealthMonitor:
    def __init__(self, interval: int = 30):
        self.interval = interval
        self.agents = {}
        
    async def monitor_agents(self):
        """30秒間隔でエージェントの死活監視を実施"""
        while True:
            for agent_id, agent_info in self.agents.items():
                status = await self.check_agent_health(agent_id)
                if status == "unhealthy":
                    await self.handle_unhealthy_agent(agent_id)
            await asyncio.sleep(self.interval)
    
    async def check_agent_health(self, agent_id: str) -> str:
        """エージェントの健康状態を確認"""
        # 1. プロセスの存在確認
        # 2. 最終活動時刻の確認
        # 3. リソース使用状況の確認
        pass
    
    async def handle_unhealthy_agent(self, agent_id: str):
        """異常エージェントの処理"""
        # 1. 状態をキャッシュに保存
        # 2. 再起動試行
        # 3. Masterへの通知
        pass
```

#### 3.3.2 エラーキャッシュ形式
```json
{
  "agent_id": "worker-1",
  "error_type": "rate_limit|crash|timeout",
  "timestamp": "2024-01-01T00:00:00Z",
  "error_details": {
    "message": "Rate limit exceeded",
    "context": {
      "task_id": "task-001",
      "progress": 75,
      "last_checkpoint": "checkpoint-123"
    }
  },
  "recovery_attempts": 1,
  "recoverable": true
}
```

### 3.4 コマンド実装詳細

#### 3.4.1 hephaestus /init
```python
def init_command():
    """作業ディレクトリの初期化"""
    1. カレントディレクトリの確認
    2. hephaestus-work/ディレクトリの作成
    3. 必要なサブディレクトリの作成
    4. config.yamlの生成（テンプレートから）
    5. 初期ログファイルの作成
    6. 権限設定（700）
```

#### 3.4.2 hephaestus /attach
```python
def attach_command():
    """tmuxセッションへのアタッチ"""
    1. 既存セッションの確認
    2. セッションが存在しない場合は新規作成
    3. Master + Worker数に応じたペイン分割
    4. 各ペインでclaude-codeを起動
    5. tmux attachでセッションに接続
```

#### 3.4.3 hephaestus /kill
```python
def kill_command():
    """全エージェントの停止"""
    1. 実行中のタスクの状態保存
    2. チェックポイントの作成
    3. エージェントへの終了シグナル送信
    4. tmuxセッションの終了
    5. クリーンアップ処理
```

## 4. 実装の優先順位

### Phase 1: 基本機能（MVP）
1. CLI基本構造の実装
2. tmuxセッション管理
3. 設定ファイル管理
4. 基本的なディレクトリ構造の作成

### Phase 2: エージェント管理
1. Master/Worker起動制御
2. 基本的な死活監視
3. ログ出力

### Phase 3: 通信機能
1. Markdownベースの通信実装
2. タスクキューの実装
3. 進捗管理

### Phase 4: 高度な機能
1. エラーリカバリー
2. チェックポイント/リストア
3. パフォーマンス最適化

## 5. 依存関係

```toml
[project]
name = "hephaestus-cli"
version = "0.1.0"
dependencies = [
    "click>=8.1.0",
    "libtmux>=0.25.0",
    "pyyaml>=6.0",
    "watchdog>=3.0.0",
    "asyncio>=3.4.3",
    "psutil>=5.9.0",
    "rich>=13.0.0",  # 美しいCLI出力用
]

[project.scripts]
hephaestus = "hephaestus.cli:main"
```

## 6. セキュリティ考慮事項

1. **ファイル権限**: 作業ディレクトリは700権限で作成
2. **通信の整合性**: メッセージにチェックサムを付与
3. **インジェクション対策**: ユーザー入力のサニタイゼーション
4. **ログのマスキング**: 機密情報のログ出力を防止

## 7. テスト戦略

1. **単体テスト**: 各モジュールの独立したテスト
2. **統合テスト**: tmux環境でのエンドツーエンドテスト
3. **負荷テスト**: 複数Workerでの並列実行テスト
4. **異常系テスト**: エラーリカバリーのテスト

## 8. 追加仕様

### 8.1 タスク分割戦略

Masterエージェントは以下の基準でタスクをWorkerに分割・割り当てます：

1. **タスクの独立性**: 相互依存のないタスクを識別し、並列実行可能なものを優先
2. **負荷分散**: 各Workerの現在の負荷を考慮した動的割り当て
3. **専門性**: タスクの性質に応じたWorkerへの割り当て（将来的な拡張）

### 8.2 進捗レポート形式

```markdown
# Progress Report
Generated: 2024-01-01 12:00:00

## Overall Status
- Total Tasks: 10
- Completed: 6
- In Progress: 3
- Pending: 1
- Success Rate: 100%

## Agent Status
### Master
- Status: Active
- Current Activity: Task coordination
- CPU: 15%
- Memory: 256MB

### Worker-1
- Status: Active
- Current Task: task-003
- Progress: 75%
- CPU: 45%
- Memory: 512MB

### Worker-2
- Status: Active
- Current Task: task-004
- Progress: 30%
- CPU: 60%
- Memory: 480MB

### Worker-3
- Status: Idle
- Last Task: task-002 (Completed)
- CPU: 5%
- Memory: 128MB

## Recent Events
- [12:00:00] Worker-1 completed task-002
- [11:58:30] Worker-2 started task-004
- [11:55:00] Master assigned task-004 to Worker-2
```

### 8.3 エラーリカバリー戦略

1. **自動リトライ**: 一時的なエラーに対して最大3回まで自動リトライ
2. **タスク再割り当て**: Workerの障害時は他のWorkerへタスク再割り当て
3. **チェックポイントからの再開**: 長時間タスクは定期的にチェックポイントを作成
4. **グレースフルデグレード**: Worker数が減少してもシステム全体は動作継続

### 8.4 パフォーマンス指標

システムは以下の指標を監視・記録します：

1. **タスク完了時間**: 各タスクの実行時間
2. **スループット**: 単位時間あたりの完了タスク数
3. **リソース使用率**: CPU、メモリ、ディスクI/O
4. **エラー率**: タスク失敗率、リトライ率
5. **レスポンス時間**: Master-Worker間の通信遅延


## 9. ライセンスと貢献

- **ライセンス**: MIT License
- **貢献ガイドライン**: CONTRIBUTING.md参照
- **行動規範**: CODE_OF_CONDUCT.md参照
- **サポート**: GitHubのIssueにて対応

---

この設計書は継続的に更新される生きたドキュメントです。
最新版は常にGitHubリポジトリのmainブランチを参照してください。

Version: 1.0.0
Last Updated: 2024-01-01
Author: Hephaestus-CLI Development Team
