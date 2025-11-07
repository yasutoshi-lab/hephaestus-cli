# Hephaestus-CLI

複数のLLMエージェント（Master + Workers）を管理し、複雑なタスクを協調実行するためのtmuxベースのマルチエージェントCLIツールです。

> 📖 [English README](README_EN.md) | 📚 [詳細ドキュメント](doc/commands/)

## 主な特徴

- **Master-Workerアーキテクチャ**: 1つのMasterエージェントが複数のWorkerエージェントを統括
- **リアルタイム監視**: TUIダッシュボードとログストリーミングで状態を可視化
- **厳格なペルソナ管理**: 起動時にエージェントの役割を強制注入
- **Tmux統合**: 分割ペインで複数エージェントを視覚的に管理
- **自動タスク分配**: Markdownベースのファイル通信でタスクを自動配布

## 前提条件

- Python 3.10以上
- tmux
- claude CLI
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

```bash
# 1. 初期化
cd /path/to/your/project
hephaestus init

# 2. セッション開始
hephaestus attach --create

# 3. 操作
# - Masterペインで高レベルのタスクを入力
# - Workerが自動的にサブタスクを実行
# - tmuxキーバインド: Ctrl+b → 矢印キーでペイン移動

# 4. 監視（別ターミナルで）
hephaestus dashboard    # リアルタイム監視
hephaestus logs -a master -f    # ログ追跡

# 5. 停止
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

| コマンド | 説明 | ドキュメント |
|---------|------|------------|
| `hephaestus init` | 環境を初期化 | [詳細](doc/commands/init_ja.md) |
| `hephaestus attach` | tmuxセッションにアタッチ/作成 | [詳細](doc/commands/attach_ja.md) |
| `hephaestus status` | 現在のステータスを表示 | [詳細](doc/commands/status_ja.md) |
| `hephaestus dashboard` | リアルタイムTUIダッシュボード | [詳細](doc/commands/dashboard_ja.md) |
| `hephaestus logs` | ログの表示・ストリーミング | [詳細](doc/commands/logs_ja.md) |
| `hephaestus monitor` | タスク配布の監視 | [詳細](doc/commands/monitor_ja.md) |
| `hephaestus kill` | セッションの終了 | [詳細](doc/commands/kill_ja.md) |

詳しい使い方は各コマンドのドキュメントを参照してください。

## 使用例

```bash
# コードリファクタリングプロジェクト
hephaestus init --workers 4
hephaestus attach --create
# Masterペインで:
# "コードベース全体を依存性注入を使用するようにリファクタリングしてください。
#  利用可能なworker間で作業を分割してください。"
```

Masterが自動的にタスクを分割し、Workerに割り当てて並列処理します。

## トラブルシューティング

**セッションが起動しない**
```bash
tmux -V    # tmuxがインストールされているか確認
which claude    # claudeが利用可能か確認
```

**エージェントが通信しない**
```bash
hephaestus logs -a master -f    # ログをチェック
ls -la hephaestus-work/communication/    # 権限を確認
```

**リソース使用量が高い**
```bash
# config.yamlでworker数を減らす
hephaestus init --workers 2 --force
```

## 参考資料

- [Claude Code](https://github.com/anthropics/claude-code)

## ライセンス

MITライセンス

---

**Version**: 0.1.0 | **Status**: アルファ版
