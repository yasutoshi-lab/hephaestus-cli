# hephaestus attach

## 概要

`hephaestus attach` は、Hephaestusのtmuxセッションにアタッチ（接続）するコマンドです。

## 使用方法

```bash
hephaestus attach [OPTIONS]
```

## オプション

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--create` | `-c` | セッションが存在しない場合、新しく作成 |
| `--change-agent <type>` | - | アタッチ前にエージェント設定を `claude` / `gemini` / `codex` に差し替え（事前に `hephaestus kill` が必要） |
| `--help` | - | ヘルプメッセージを表示 |

## 動作

1. 既存のtmuxセッションが存在する場合、そのセッションにアタッチします
2. `--create`オプションが指定されている場合、セッションが存在しなければ新規作成します
3. `--change-agent` が指定されている場合、tmux起動前に `config.yaml` と `.Claude/`（もしくは `.Gemini/`, `.Codex/`）を再生成します（事前に `hephaestus kill` を実行してセッションを停止してください）
4. tmuxセッション内では、Master + Workerエージェントがそれぞれ別のペインで起動します

### ヘッドレスモードへのフォールバック

tmuxがインストールされていない、もしくは `error connecting to /tmp/tmux-1000/default (Operation not permitted)` のようにソケットへ接続できない場合でも、コマンドは失敗せず自動的にヘッドレスモードへ切り替わります。

- 現在のターミナルにエージェント名・PID・ログパス・稼働状況を表示するパネルが現れます
- `Ctrl+C` でパネルを抜けてもエージェントはバックグラウンドで動作し続けます
- 別ターミナルで `hephaestus logs --all -f`（または `-a master`, `-a worker-1` など）を実行するとログをリアルタイムで追跡できます
- 停止したい場合は通常どおり `hephaestus kill` を実行するだけでヘッドレスセッションも終了します

tmuxが再び利用可能になれば、次回 `hephaestus attach` 実行時に何もせず従来のtmuxセッションへ戻ります。

## 使用例

### 既存セッションにアタッチ

```bash
hephaestus attach
```

### セッションを作成してアタッチ

```bash
hephaestus attach --create
```

初回起動時は必ず `--create` オプションが必要です。

### レート制限到達後にエージェントを切り替え

```bash
hephaestus kill
hephaestus attach --create --change-agent codex
```

既存の `.Claude/` ディレクトリと `config.yaml` が指定したエージェント設定に置き換えられます。

## tmuxセッション内の操作

アタッチ後、以下のtmuxキーバインドが使用できます：

| キーバインド | 機能 |
|------------|------|
| `Ctrl+b` → `d` | セッションからデタッチ（エージェントは実行継続） |
| `Ctrl+b` → 矢印キー | ペイン間を移動 |
| `Ctrl+b` → `z` | 現在のペインを最大化/元に戻す |
| `Ctrl+b` → `[` | スクロールモード（q で終了） |

## セッションレイアウト

```
┌─────────────────────────────────────────────┐
│                Master Agent                 │  ← Masterエージェント
├──────────────┬──────────────┬───────────────┤
│  Worker-1    │  Worker-2    │   Worker-3    │  ← Workerエージェント
│              │              │               │
│              │              │               │
└──────────────┴──────────────┴───────────────┘
```

## エージェント起動時の動作

各エージェントは起動時に以下の処理が行われます：

1. **ペルソナ注入**: エージェント種別に対応したREADME（`CLAUDE.md` / `GEMINI.md` / `AGENT.md`）が読み込まれ、役割が割り当てられます
2. **初期化確認**: エージェントが役割を認識したことを確認します
3. **待機状態**: タスクの割り当てを待ちます

## エラーと対処

### セッションが存在しない

```
No session found: hephaestus

Use --create flag to create a new session:
  hephaestus attach --create
```

**対処**: `--create` オプションを追加してください。

### 初期化されていない

```
.hephaestus-work directory not found!

Run hephaestus init first to initialize the environment.
```

**対処**: まず `hephaestus init` を実行してください。

### tmuxがインストールされていない

```
tmux: command not found
```

**対処**: tmuxをインストールしてください：
```bash
# Ubuntu/Debian
sudo apt-get install tmux

# macOS
brew install tmux
```

## 注意事項

- セッションからデタッチしても、エージェントは実行を継続します
- `--change-agent` を使う前に、必ず `hephaestus kill` で既存セッションを終了してください
- 再度アタッチすれば、同じセッションに戻れます
- セッションを終了するには `hephaestus kill` を使用してください

## 関連コマンド

- [hephaestus init](./init_ja.md) - 初期化（最初に実行）
- [hephaestus kill](./kill_ja.md) - セッション終了
- [hephaestus status](./status_ja.md) - セッション状態確認
- [hephaestus dashboard](./dashboard_ja.md) - 別ウィンドウで監視
