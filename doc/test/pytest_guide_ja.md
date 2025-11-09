# pytest 実行ガイド

Hephaestus リポジトリでテストスイートを実行する手順をまとめたドキュメントです。`uv` を利用する前提になっています。

## 前提条件

- Python 3.10 以上
- `uv` コマンドがインストール済み（https://github.com/astral-sh/uv）
- プロジェクトルートに移動済み（例：`/home/ubuntu/python_project/Hephaestus`）

## 1. 仮想環境と依存関係のセットアップ

初回は `uv` が自動で `.venv` を作成します。`pytest` が未インストールの場合は以下を実行してください。

```bash
uv pip install pytest
```

`pyproject.toml`／`uv.lock` に必要な依存が追加された際は、次のコマンドで同期できます。

```bash
uv sync
```

## 2. テストの実行

すべてのテストを実行するには以下を使用します。

```bash
uv run pytest
```

特定ディレクトリやファイルに限定する場合は引数を指定します。

```bash
uv run pytest test/unit/test_communication.py
uv run pytest test/integration
```

## 3. 失敗時の確認ポイント

- `pytest` が見つからない：`uv pip install pytest` を再度実行
- 既存の仮想環境を使いたい場合は `source .venv/bin/activate` 後に `pytest` を直接実行可能
- 依存関係の追加・更新後は `uv sync` でロックファイルを反映

## 4. 補足

- `uv run` は仮想環境の作成とキャッシュ管理を自動で行います
- テスト結果は `test/` ディレクトリ配下の 30 件のケースが対象です（2025-11-09 時点）


