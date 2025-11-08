# hephaestus send

## 概要

`hephaestus send` は、エージェント間でメッセージを送信するコマンドです。MasterからWorkerへのタスク配分や、WorkerからMasterへの進捗報告に使用されます。

## 使用方法

```bash
# エージェント一覧を表示
hephaestus send --list

# メッセージを送信
hephaestus send <agent-name> <message>
```

## オプション

| オプション | 短縮形 | 説明 |
|----------|--------|------|
| `--list` | `-l` | 利用可能なエージェントを一覧表示 |

## 引数

- `<agent-name>`: 送信先エージェント名（master, worker-1, worker-2, etc.）
- `<message>`: 送信するメッセージ

## 使用例

### エージェント一覧の表示

```bash
hephaestus send --list
```

**出力例**:
```
                          Agent List
┏━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Agent Name ┃ Status   ┃ Pane            ┃
┡━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ master    │ Active   │ hephaestus:0.0  │
│ worker-1  │ Active   │ hephaestus:0.1  │
│ worker-2  │ Active   │ hephaestus:0.2  │
│ worker-3  │ Active   │ hephaestus:0.3  │
└───────────┴──────────┴─────────────────┘
```

### Workerにメッセージを送信

```bash
hephaestus send worker-1 "src/ディレクトリのコード解析を開始してください"
```

**出力**:
```
Sending message to worker-1...
✓ Message sent to worker-1
Message: src/ディレクトリのコード解析を開始してください

Communication logged to: hephaestus-work/logs/communication.log
```

### Masterに進捗を報告（Worker内から）

```bash
hephaestus send master "タスク task_001 完了。結果を communication/worker_to_master/task_001_results.md に保存しました"
```

### 複数のWorkerに送信（スクリプト例）

```bash
# 全Workerに一斉送信
for i in {1..3}; do
    hephaestus send worker-$i "緊急タスク: すぐに作業を中断してください"
done
```

## エージェントペルソナと統合

エージェントのペルソナ（CLAUDE.md）は、特定のタイミングで `hephaestus send` の使用を強制します：

### Master Agent

**タスク配分時に必須**:
```bash
# 1. タスクファイルを作成
# communication/master_to_worker/task_001_analysis.md

# 2. 必ず send コマンドで通知（自動実行される）
hephaestus send worker-1 "New task assigned: Code Analysis. Please read task_001_analysis.md"
```

### Worker Agent

**進捗報告時に必須**:

1. **タスク開始時**:
```bash
hephaestus send master "Task task_001 started. Analyzing code. ETA: 30 minutes"
```

2. **進捗更新時**:
```bash
hephaestus send master "Task task_001 progress: 50% complete. Found 5 issues"
```

3. **完了時**:
```bash
hephaestus send master "Task task_001 COMPLETED. Results saved to task_001_results.md"
```

4. **ブロック時**:
```bash
hephaestus send master "Task task_001 BLOCKED: Missing dependency. Need assistance"
```

## 通信ログ

全ての通信は自動的にログファイルに記録されます：

```bash
# ログを確認
cat hephaestus-work/logs/communication.log

# 特定のエージェント間の通信を検索
grep "master -> worker-1" hephaestus-work/logs/communication.log
```

**ログ形式**:
```
[2025-11-08 18:30:45] master -> worker-1: New task assigned: Code Analysis
[2025-11-08 18:31:00] worker-1 -> master: Task acknowledged. Starting work
[2025-11-08 18:45:30] worker-1 -> master: Task completed. Results ready
```

## エラーと対処

### セッションが起動していない

```
No active session found: hephaestus

Start the session first with: hephaestus attach --create
```

**対処**: `hephaestus attach --create` でセッションを起動してください。

### エージェントが見つからない

```
✗ Failed to send message to worker-5
Check if the agent exists with: hephaestus send --list
```

**対処**:
- `hephaestus send --list` でエージェント一覧を確認
- config.yaml のworker数を確認
- 正しいエージェント名を指定（master, worker-1, worker-2, etc.）

### 引数不足

```
Missing arguments

Usage:
  hephaestus send --list                    # List agents
  hephaestus send <agent> <message>         # Send message
```

**対処**: エージェント名とメッセージの両方を指定してください。

## 使用シナリオ

### 1. 緊急タスクの配分

```bash
# 優先度の高いタスクを即座に送信
hephaestus send worker-2 "URGENT: セキュリティ脆弱性の修正を優先してください"
```

### 2. タスクの状況確認

```bash
# Workerに状況を問い合わせ
hephaestus send worker-1 "現在のタスクの進捗状況を報告してください"
```

### 3. 作業の中断指示

```bash
# 全Workerに作業停止を指示
for i in {1..3}; do
    hephaestus send worker-$i "作業を一時停止してください。新しい指示を待ってください"
done
```

### 4. デバッグとテスト

```bash
# 通信システムのテスト
hephaestus send worker-1 "Test message - Please acknowledge"

# ログで受信確認
tail -f hephaestus-work/logs/communication.log
```

## 技術的な詳細

### 通信メカニズム

`hephaestus send` は以下の手順でメッセージを送信します：

1. **ペイン検索**: tmux pane titleからターゲットエージェントを特定
2. **入力クリア**: Ctrl+C で既存入力をクリア
3. **メッセージ送信**: tmux send-keys でメッセージを送信
4. **Enter実行**: メッセージを実行
5. **ログ記録**: communication.log に記録

### メッセージ制限

- メッセージに特殊文字（`$`, `"`, `` ` ``など）を含む場合は適切にエスケープされます
- 非常に長いメッセージは分割送信されます
- tmux の行長制限を考慮してメッセージを設計してください

## 関連コマンド

- [hephaestus attach](./attach_ja.md) - セッションの起動
- [hephaestus monitor](./monitor_ja.md) - 自動タスク配布
- [hephaestus logs](./logs_ja.md) - ログの確認
- [hephaestus status](./status_ja.md) - セッション状態の確認

## 参考

- [Claude-Code-Communication](https://github.com/nishimoto265/Claude-Code-Communication) - 元となった agent-send.sh の実装
