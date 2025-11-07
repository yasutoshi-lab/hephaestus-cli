# 開発中です

## Hephaestus-CLI

複数のLLMエージェント（Master + Workers）を管理し、複雑なタスクを協調実行するためのtmuxベースのマルチエージェントCLIツールです。

> 📖 [English README](README_EN.md)

## 概要

Hephaestus-CLIは、tmuxを活用して複数のClaude Codeエージェントを連携させるLinux向けコマンドラインツールです。主な特徴：

- **Master-Workerアーキテクチャ**: 1つのMasterエージェントが複数のWorkerエージェントを統括
- **Tmux統合**: 分割ペインで複数のエージェントを視覚的に管理
- **リアルタイムダッシュボード**: TUIでエージェントのステータスとタスクをリアルタイム監視
- **ログストリーミング**: エージェントのログをリアルタイムで表示・追跡
- **厳格なペルソナ管理**: 起動時に役割を強制注入してエージェントの役割を明確化
- **タスク管理**: タスクの自動分配と進捗追跡
- **ヘルスモニタリング**: エージェントの自動ヘルスチェックとエラー回復
- **ファイルベース通信**: Markdownベースのエージェント間メッセージング
- **自己完結型**: すべての処理を`hephaestus-work`ディレクトリ内で管理

## システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                    Hephaestus-CLI                       │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐                                       │
│  │   CLI Entry  │ (init, attach, kill)                  │
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
└─────────────────────────────────────────────────────────┘
```

## 前提条件

- Python 3.10以上
- tmux（システムにインストール済み）
- claude CLI（インストール・設定済み）
- Linuxオペレーティングシステム

## インストール

### uvを使用（推奨）

```bash
# uvのインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# リポジトリのクローン
git clone https://github.com/your-org/hephaestus-cli.git
cd hephaestus-cli

# パッケージのビルド
python3 -m build

# uvでインストール
uv tool install dist/hephaestus_cli-0.1.0-*.whl
```

### pipを使用

```bash
# クローンとビルド
git clone https://github.com/your-org/hephaestus-cli.git
cd hephaestus-cli

# 開発モードでインストール
pip install -e .

# またはビルドしてインストール
python3 -m build
pip install dist/hephaestus_cli-0.1.0-*.whl
```

## クイックスタート

### 1. Hephaestusの初期化

プロジェクトディレクトリに移動して初期化します：

```bash
cd /path/to/your/project
hephaestus init
```

以下の構造で`hephaestus-work`ディレクトリが作成されます：

```
hephaestus-work/
├── config.yaml                     # 設定ファイル
├── cache/                          # エージェント状態とレート制限
├── tasks/                          # タスクキュー（pending/in_progress/completed）
├── checkpoints/                    # リカバリーチェックポイント
├── progress/                       # エージェント進捗追跡
├── logs/                           # システムとエージェントのログ
└── communication/                  # エージェント間メッセージング
```

### 2. エージェントの起動

tmuxセッションにアタッチ（存在しない場合は作成）：

```bash
hephaestus attach --create
```

分割ペインでtmuxセッションが開きます：
- 上部ペイン: Masterエージェント
- 追加ペイン: Workerエージェント（デフォルト: 3 workers）

### 3. エージェントの操作

アタッチ後の操作：
- tmuxキーバインドでペイン間を移動（デフォルト: `Ctrl+b` → 矢印キー）
- Masterペインで高レベルのタスクを入力
- Workerが自動的にMasterからサブタスクを受け取り実行
- すべてのエージェントで`claude`が実行され、ツールにアクセス可能

### 4. エージェントの停止

tmuxセッションからデタッチ（エージェントは実行継続）：
```bash
# Ctrl+b を押してから d
```

すべてのエージェントを停止してセッションを破棄：
```bash
hephaestus kill
```

## 設定

`hephaestus-work/config.yaml`を編集してカスタマイズ：

```yaml
version: 1.0

agents:
  master:
    enabled: true
    command: "claude"
    args: []
  workers:
    count: 3  # Worker数を変更
    command: "claude"
    args: []

monitoring:
  health_check_interval: 30  # 秒
  retry_attempts: 3
  retry_delay: 5

tmux:
  session_name: "hephaestus"
  layout: "tiled"  # even-horizontal, even-vertical, main-horizontal, main-vertical, tiled
```

## コマンド

### `hephaestus init`

hephaestus-workディレクトリを初期化します。

オプション:
- `-w, --workers N`: Workerエージェント数（デフォルト: 3）
- `-f, --force`: 既存の場合でも強制的に初期化

例:
```bash
hephaestus init --workers 5
```

### `hephaestus attach`

tmuxセッションにアタッチします。

オプション:
- `-c, --create`: セッションが存在しない場合は作成

例:
```bash
hephaestus attach --create
```

### `hephaestus kill`

すべてのエージェントを停止し、tmuxセッションを破棄します。

オプション:
- `-f, --force`: 確認プロンプトをスキップ

例:
```bash
hephaestus kill --force
```

### `hephaestus status`

エージェントとタスクの現在のステータスを表示します。

例:
```bash
hephaestus status
```

### `hephaestus dashboard`

エージェントをモニタリングするためのリアルタイムTUIダッシュボードを起動します。

表示内容:
- エージェントのステータスと現在のタスク
- タスク概要テーブル
- 通信ログストリーム

例:
```bash
hephaestus dashboard
```

キーバインド:
- `q`: ダッシュボードを終了
- `r`: 手動で更新

### `hephaestus logs`

エージェントのログを表示・ストリーミングします。

オプション:
- `-a, --agent <name>`: 特定のエージェントのログを表示（例: master, worker-1）
- `-f, --follow`: リアルタイムでログを追跡（tail -fと同様）
- `-n, --lines N`: 表示する行数（デフォルト: 50）
- `--all`: すべてのエージェントのログを表示
- `-l, --list`: 利用可能なログファイルの一覧を表示

例:
```bash
# ログ一覧を表示
hephaestus logs --list

# Masterエージェントのログを表示
hephaestus logs -a master

# Masterエージェントのログをリアルタイムで追跡
hephaestus logs -a master -f

# すべてのエージェントのログをリアルタイムで追跡
hephaestus logs --all -f

# 複数のWorkerのログを表示
hephaestus logs -a worker-1 -a worker-2

# 最後の100行を表示
hephaestus logs -a master -n 100
```

### `hephaestus monitor`

タスク配布を監視し、自動的にWorkerに通知します。

オプション:
- `-i, --interval N`: タスクチェック間隔（秒）（デフォルト: 5）
- `-m, --max-iterations N`: 最大監視回数（デフォルト: 120）

例:
```bash
hephaestus monitor --interval 10
```

## 使用例

### 例1: コードリファクタリングプロジェクト

```bash
# 4 workersで初期化
hephaestus init --workers 4

# セッション開始
hephaestus attach --create

# Masterペインで指示:
# "コードベース全体を依存性注入を使用するようにリファクタリングしてください。
#  利用可能なworker間で作業を分割してください。"

# Masterの処理:
# 1. コードベースを分析
# 2. サブタスクを作成（例: モジュールA, B, C, Dをリファクタリング）
# 3. Workerにタスクを割り当て
# 4. 進捗を監視し、結果を統合
```

### 例2: ドキュメント生成

```bash
# デフォルトのworker数で初期化
hephaestus init

# セッション開始
hephaestus attach --create

# Masterペインで:
# "すべてのPythonモジュールの包括的なドキュメントを生成してください。
#  各Workerが異なるパッケージを処理するようにしてください。"

# MasterがWorkerを調整しながら並列処理
```

## ディレクトリ構造の説明

### `cache/`
- `agent_states/`: エージェントのステータスとメタデータを保存
- `rate_limits/`: APIレート制限情報を追跡

### `tasks/`
- `pending/`: 割り当て待ちのタスク
- `in_progress/`: 実行中のタスク
- `completed/`: 完了したタスクと結果

### `communication/`
- `master_to_worker/`: MasterからWorkerへのメッセージ
- `worker_to_master/`: Workerからのステータス更新と結果

### `logs/`
- `master.log`: Masterエージェントのログ
- `worker_N.log`: 個別のWorkerログ
- `system.log`: システムレベルのログ

## 高度な機能

### タスク管理

タスクはMarkdownファイルを通じて自動管理されます。Masterエージェントがタスクを作成し、Workerがそれを取得して実行します。

### ヘルスモニタリング

- 30秒間隔の自動ヘルスチェック
- クラッシュしたエージェント、レート制限、リソース問題を検出
- 設定可能なリトライ回数での自動回復
- キャッシュ内のエラー履歴追跡

### チェックポイント

長時間実行されるタスクのために、システムが自動的にチェックポイントを作成し、障害からの回復を可能にします。

## トラブルシューティング

### セッションが起動しない

tmuxがインストールされているか確認:
```bash
tmux -V
```

claudeが利用可能か確認:
```bash
which claude
```

### エージェントが通信しない

通信ディレクトリの権限を確認:
```bash
ls -la hephaestus-work/communication/
```

ログを表示:
```bash
tail -f hephaestus-work/logs/system.log
```

### リソース使用量が高い

config.yamlでworker数を減らす:
```yaml
agents:
  workers:
    count: 2  # 3から減少
```

## 開発

### テストの実行

```bash
pytest tests/
```

### プロジェクト構造

```
hephaestus-cli/
├── src/hephaestus/
│   ├── cli.py                  # CLIエントリーポイント
│   ├── config.py               # 設定管理
│   ├── session_manager.py      # Tmuxセッション処理
│   ├── agent_controller.py     # エージェントライフサイクル
│   ├── communication.py        # エージェント間メッセージング
│   ├── task_manager.py         # タスクキュー管理
│   ├── health_monitor.py       # ヘルスモニタリング
│   └── utils/                  # ユーティリティモジュール
├── templates/                  # 設定テンプレート
├── tests/                      # テストスイート
└── pyproject.toml             # パッケージ設定
```

## コントリビューション

貢献を歓迎します！ガイドラインについてはCONTRIBUTING.mdをご覧ください。

## ライセンス

MITライセンス - 詳細はLICENSEファイルをご覧ください。

## 参考資料

- [Claude Code](https://github.com/anthropics/claude-code)
- [Claude-Code-Communication](https://github.com/nishimoto265/Claude-Code-Communication)
- [tmux](https://github.com/tmux/tmux)

## サポート

問題や質問がある場合:
- GitHub Issues: https://github.com/your-org/hephaestus-cli/issues
- ドキュメント: リポジトリ内の設計書を参照

---

**バージョン**: 0.1.0
**ステータス**: アルファ版
**最終更新**: 2025-01-06
