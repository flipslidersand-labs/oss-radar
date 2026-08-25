.DEFAULT_GOAL := help

PYTHON := .venv/bin/python
PYTEST := .venv/bin/pytest
RUFF   := .venv/bin/ruff

# .env が存在する場合に読み込む
ENV_LOAD := $(if $(wildcard .env),set -a && source .env && set +a &&,)

.PHONY: help setup collect dry-run search test lint

help: ## このヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## 依存パッケージをインストール (.venv を作成)
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@if [ -f requirements-dev.txt ]; then .venv/bin/pip install -r requirements-dev.txt; fi

collect: ## 全ソースから OSS リポジトリを収集して Qdrant に ingest
	$(ENV_LOAD) $(PYTHON) main.py

dry-run: ## 収集・dedup 結果だけ表示 (Qdrant には書かない)
	$(ENV_LOAD) $(PYTHON) main.py --dry-run

search: ## OSS リポジトリを検索 (例: make search q="machine learning" lang=Go)
	$(ENV_LOAD) $(PYTHON) search.py "$(q)" \
		$(if $(lang),--lang $(lang),) \
		$(if $(license),--license $(license),) \
		$(if $(stars),--stars-min $(stars),) \
		$(if $(limit),--limit $(limit),)

test: ## テストを実行
	$(PYTEST) tests/ -q

lint: ## ruff でコードをチェック
	$(RUFF) check .
