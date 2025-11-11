# hephaestus init

## 概要

`hephaestus init` は、現在のディレクトリにHephaestusの作業環境を初期化するコマンドです。

## 使用方法

```bash
hephaestus init [OPTIONS]
```

## オプション

| オプション | 短縮形 | デフォルト | 説明 |
|-----------|--------|-----------|------|
| `--workers` | `-w` | 3 | Workerエージェントの数を指定 |
| `--agent-type` | `-a` | claude | 使用するAIエージェントのタイプ（claude, gemini, codex） |
| `--force` | `-f` | - | 既存の.hephaestus-workディレクトリがある場合でも強制的に再初期化 |
| `--help` | - | - | ヘルプメッセージを表示 |

## 動作

このコマンドを実行すると、以下の処理が行われます：

1. **ディレクトリ構造の作成**
   ```
   .hephaestus-work/
   ├── .claude/              # エージェント設定
   │   ├── CLAUDE.md         # 共通設定（claudeの場合）
   │   ├── GEMINI.md         # 共通設定（geminiの場合）
   │   ├── AGENT.md          # 共通設定（codexの場合）
   │   ├── master/           # Master設定
   │   │   └── [エージェント固有のREADMEファイル]
   │   └── worker/           # Worker設定
   │       └── [エージェント固有のREADMEファイル]
   ├── config.yaml           # システム設定
   ├── cache/                # キャッシュ
   │   ├── agent_states/
   │   └── rate_limits/
   ├── tasks/                # タスク管理
   │   ├── pending/
   │   ├── in_progress/
   │   └── completed/
   ├── communication/        # エージェント間通信
   │   ├── master_to_worker/
   │   └── worker_to_master/
   ├── logs/                 # ログファイル
   ├── checkpoints/          # チェックポイント
   └── progress/             # 進捗追跡
   ```

2. **設定ファイルの生成**
   - `config.yaml`: システム全体の設定（agent_typeフィールドを含む）
   - エージェントタイプに応じたREADMEファイル:
     - Claude: `.claude/CLAUDE.md`, `.claude/master/CLAUDE.md`, `.claude/worker/CLAUDE.md`
     - Gemini: `.claude/GEMINI.md`, `.claude/master/GEMINI.md`, `.claude/worker/GEMINI.md`
     - Codex: `.claude/AGENT.md`, `.claude/master/AGENT.md`, `.claude/worker/AGENT.md`

3. **初期化の確認**
   - 正常に完了すると、作成されたディレクトリとファイルの情報が表示されます

## 使用例

### 基本的な初期化

```bash
hephaestus init
```

デフォルトで3つのWorkerエージェント、Claude Codeを使用する環境が作成されます。

### エージェントタイプを指定して初期化

```bash
# Gemini CLIを使用
hephaestus init --agent-type gemini

# ChatGPT Codexを使用
hephaestus init --agent-type codex

# Claude Code（明示的指定）
hephaestus init --agent-type claude
```

各エージェントタイプに応じたコマンドとREADMEファイルが自動的に設定されます。

### Worker数を指定して初期化

```bash
hephaestus init --workers 5
```

5つのWorkerエージェントを含む環境が作成されます。

### エージェントタイプとWorker数を両方指定

```bash
hephaestus init --agent-type gemini --workers 4
```

Gemini CLIを使用し、4つのWorkerエージェントを含む環境が作成されます。

### 強制的に再初期化

```bash
hephaestus init --force
```

既存の`.hephaestus-work`ディレクトリがある場合でも、警告なしで上書きします。

## エラーと対処

### 既に.hephaestus-workディレクトリが存在する場合

```
.hephaestus-work directory already exists at:
/path/to/.hephaestus-work

Use --force to reinitialize.
```

**対処**: `--force`オプションを使用して再初期化するか、手動でディレクトリを削除してから再実行してください。

### ディレクトリ作成の権限がない場合

```
Permission denied: '.hephaestus-work'
```

**対処**: 現在のディレクトリに書き込み権限があることを確認してください。

## 注意事項

- 初期化後、`config.yaml`を編集してWorker数やその他の設定をカスタマイズできます
- `--force`オプションを使用すると、既存のタスクやログなどすべてのデータが失われます
- 初期化後は`hephaestus attach --create`でエージェントを起動できます

## 関連コマンド

- [hephaestus attach](./attach_ja.md) - エージェントの起動
- [hephaestus status](./status_ja.md) - 初期化状態の確認
- [hephaestus kill](./kill_ja.md) - セッションの終了

## 設定ファイル

初期化後に生成される`config.yaml`の詳細については、[Configuration Guide](../configuration_ja.md)を参照してください。
