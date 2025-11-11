# hephaestus logs

## 概要

`hephaestus logs` は、エージェントのログファイルを表示・ストリーミングするコマンドです。

## 使用方法

```bash
hephaestus logs [OPTIONS]
```

## オプション

| オプション | 短縮形 | デフォルト | 説明 |
|-----------|--------|-----------|------|
| `--agent` | `-a` | - | 表示するエージェント名（複数指定可） |
| `--follow` | `-f` | false | リアルタイムでログを追跡（tail -f相当） |
| `--lines` | `-n` | 50 | 表示する行数 |
| `--all` | - | false | 全エージェントのログを表示 |
| `--list` | `-l` | false | 利用可能なログファイル一覧を表示 |
| `--help` | - | - | ヘルプメッセージを表示 |

## エージェント名

以下のエージェント名を指定できます：

- `master`: Masterエージェントのログ
- `worker-1`, `worker-2`, ...: 各Workerエージェントのログ
- `system`: システムログ
- `communication`: エージェント間通信ログ

## 使用例

### ログファイル一覧の表示

```bash
hephaestus logs --list
```

出力例：
```
                    Available Logs
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Agent    ┃ Log File          ┃ Size    ┃ Last Modified       ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ Master   │ master.log        │ 486.0 B │ 2025-11-07 02:39:49 │
│ Worker-1 │ worker_1.log      │ 485.0 B │ 2025-11-07 02:39:52 │
│ Worker-2 │ worker_2.log      │ 425.0 B │ 2025-11-07 02:39:55 │
│ System   │ system.log        │ 133.0 B │ 2025-11-07 02:39:06 │
│ Comm     │ communication.log │ 396.0 B │ 2025-11-07 02:39:57 │
└──────────┴───────────────────┴─────────┴─────────────────────┘
```

### 特定エージェントのログを表示

```bash
# Masterエージェントの最後の50行（デフォルト）
hephaestus logs -a master

# Masterエージェントの最後の100行
hephaestus logs -a master -n 100

# Worker-1の最後の20行
hephaestus logs -a worker-1 -n 20
```

### 複数エージェントのログを表示

```bash
# MasterとWorker-1のログを表示
hephaestus logs -a master -a worker-1

# Worker-1とWorker-2のログを表示
hephaestus logs -a worker-1 -a worker-2
```

### リアルタイムでログを追跡

```bash
# Masterエージェントのログをリアルタイム追跡
hephaestus logs -a master -f

# 全エージェントのログをリアルタイム追跡
hephaestus logs --all -f

# Worker-1のログをリアルタイム追跡
hephaestus logs -a worker-1 --follow
```

**注意**: リアルタイム追跡は`Ctrl+C`で停止できます。

### 通信ログの確認

```bash
# エージェント間通信ログを表示
hephaestus logs -a communication

# 通信ログをリアルタイム追跡
hephaestus logs -a communication -f
```

### システムログの確認

```bash
hephaestus logs -a system
```

## ヘッドレスモードでの使い方

`hephaestus attach` がヘッドレスモードへフォールバックした場合（tmuxが利用できない環境など）、このコマンドがエージェント出力を確認するメイン手段になります。

- `hephaestus logs --all -f` で全エージェントのログを同時に追跡
- `-a master` や `-a worker-1` などを指定して特定エージェントに絞り込む
- `.hephaestus-work/logs/` 以下のログは自動的に作成されるため、エージェントが出力を出す前から `-f` で待ち受けできます

作業が完了したら `hephaestus kill` でヘッドレスセッションを停止してください。

## 色分け表示

ログは見やすいように、エージェントごとに色分けされて表示されます：

- **Master**: シアン
- **Worker**: グリーン
- **System**: イエロー
- **Communication**: マゼンタ

## 出力形式

### 個別ログ表示

```
╭───────────────────────────────── master Log ─────────────────────────────────╮
│ Last 3 lines from: master.log                                                │
╰──────────────────────────────────────────────────────────────────────────────╯
2025-11-07 10:00:04,678 - Master - INFO - Tasks assigned to workers
2025-11-07 10:00:05,901 - Master - INFO - Monitoring worker progress
```

### リアルタイム追跡

```
╭─────────────────────────────────  Log Stream ─────────────────────────────────╮
│ Streaming logs from: master.log                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

Press Ctrl+C to stop streaming

[Master] 2025-11-07 10:00:04,678 - Master - INFO - Tasks assigned to workers
[Master] 2025-11-07 10:00:05,901 - Master - INFO - Monitoring worker progress
...
```

## エラーと対処

### 初期化されていない場合

```
Not initialized. Run 'hephaestus init' first.
```

**対処**: `hephaestus init`を実行してください。

### 指定したエージェントのログが存在しない場合

```
Log file not found for agent: worker-5
```

**対処**:
- `hephaestus logs --list`で利用可能なログを確認
- エージェント名のスペルを確認
- セッションが起動しているか確認（`hephaestus status`）

## 使用シーン

### デバッグ時

```bash
# エラーが発生したWorkerのログを確認
hephaestus logs -a worker-2 -n 100

# 全エージェントのログを確認
hephaestus logs --all -n 50
```

### タスク実行の監視

```bash
# Masterの動作をリアルタイム監視
hephaestus logs -a master -f

# 特定のWorkerの進捗をリアルタイム監視
hephaestus logs -a worker-1 -f
```

### 通信の確認

```bash
# エージェント間の通信を確認
hephaestus logs -a communication -f
```

## 注意事項

- ログファイルが存在しない場合は、エージェントがまだ起動していない可能性があります
- リアルタイム追跡（`-f`）は、ログファイルが更新されるまで待機します
- 大量のログがある場合、`-n`オプションで行数を制限することを推奨します

## パフォーマンス

- ログ表示は高速で、大きなログファイルでも効率的に処理します
- リアルタイム追跡は、ファイルの変更を効率的に検出します

## 関連コマンド

- [hephaestus dashboard](./dashboard_ja.md) - グラフィカルな監視
- [hephaestus status](./status_ja.md) - 簡易ステータス確認
- [hephaestus monitor](./monitor_ja.md) - タスク配布の監視

## ログファイルの場所

ログファイルは`.hephaestus-work/logs/`ディレクトリに保存されます：

```
.hephaestus-work/logs/
├── master.log           # Masterエージェントのログ
├── worker_1.log         # Worker-1のログ
├── worker_2.log         # Worker-2のログ
├── worker_N.log         # Worker-Nのログ
├── system.log           # システムログ
└── communication.log    # 通信ログ
```
