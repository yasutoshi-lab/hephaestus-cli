# Hephaestus-CLI

下記にHephaestus-CLIが持つ機能を記載します。内容をもとに肉付けし、詳細設計書を作成してください。

## システム概要

- **Hephaestus-CLI**はtmuxを基盤としたLinux向けマルチエージェントCLIツール
- 複数のLLMエージェント（Master+Workers実行）を効率的に管理し、コーディング、レポート作成、調査などの複雑なタスクを協調実行します

## 特徴

- Master実行: MasterエージェントがCLIツールを直接呼び出し、ユーザーから指示を受け、タスク実行計画の作成とworkerエージェントの進捗管理を実施
- Worker実行: Masterエージェントが作成したタスク実行計画をもとに、WorkerエージェントがCLIツールを直接呼び出してタスクを実行し、随時進捗をMasterに共有
- CLIツールラッパー: tmuxで単一のterminakを複数分割し、claude-codeを並列実行(Master, Workerの数により分割数は変動)
- カレントディレクトリ実行: 起動コマンドを実行した際のカレントディレクトリをルートディレクトリとし、"hephaestus-work"ディレクトリを作成し、"hephaestus-work"ディレクトリ内部ですべてのcache, タスク, checkpoint処理, 進捗管理, logなどを管理。
- Docker等は利用せず、作業ディレクトリ内部で完結するもので管理を実装してください
- Masterへのタスク投入は、"hephaestus /attach"コマンドでAgentを確認したときに、直接Master claude-code Agentのchat欄に入力して運用します

## 機能概要

### コマンドライン

"hephaestus /init" カレントディレクトリに"hephaestus-work"ディレクトリを作成し、配下に"cache", "task"などの作業に必要なファイルの作成を実施
"hephaestus /attach" tmuxで実行したすべてのclaude-code Agentの状態を確認(マウス操作で各Agentタブを操作可能)
"hephaestus /kill" tmuxで実行したすべてのclaude-code Agentを停止

### インストール想定

```bash
# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# リポジトリをクローン
git clone https://github.com/your-org/hephaestus-cli.git
cd hephaestus-cli

# ビルド
python3 -m build

# uvでインストール
uv tool install dist/hephaestus-cli0.1.0-.whl

# ヘルプの確認
hephaestus --help
```

## 参考資料
[claude-code](https://github.com/anthropics/claude-code)
[Claude-Code-Communication](https://github.com/nishimoto265/Claude-Code-Communication)
