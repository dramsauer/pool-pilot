SHELL := /bin/bash
APP_NAME := pool-water-balance
DOCKER_COMPOSE := docker compose
PYTHON := python3

.PHONY: help install run start stop quit logs test build dev clean shell restart

help:
	@echo "================================================"
	@echo "  $(APP_NAME) - Pool Water Balance"
	@echo "================================================"
	@echo ""
	@echo "  Development:"
	@echo "    make install     Install project + dev deps"
	@echo "    make dev         Run app locally (streamlit)"
	@echo "    make test        Run all tests"
	@echo ""
	@echo "  Docker:"
	@echo "    make build       Build Docker image"
	@echo "    make run         Start app in Docker background"
	@echo "    make start       Alias for run"
	@echo "    make stop        Stop Docker container"
	@echo "    make quit        Alias for stop"
	@echo "    make logs        Follow container logs"
	@echo "    make shell       Open bash in running container"
	@echo "    make restart     Restart container"
	@echo ""
	@echo "  Maintenance:"
	@echo "    make clean       Remove containers, volumes, caches"
	@echo "    make help        Show this help"
	@echo ""

install:
	pip install --no-cache-dir \
	streamlit>=1.35 \
	sqlalchemy>=2.0 \
	plotly>=5.20 \
	pillow>=10.0 \
	pandas>=2.1 \
	pytest>=7.4 \
	tomli>=2.0

dev:
	$(PYTHON) -m streamlit run Wasserrechner.py --server.address=0.0.0.0 --server.port=8501

test:
	$(PYTHON) -m pytest tests/ -v

build:
	$(DOCKER_COMPOSE) build

run start:
	$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "  App is running at: http://localhost:8501"

stop quit:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

shell:
	$(DOCKER_COMPOSE) exec pool-app bash

restart: stop run

clean:
	$(DOCKER_COMPOSE) down -v 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf data/*.db 2>/dev/null || true
	rm -rf data/photos/* 2>/dev/null || true
	rm -rf *.egg-info 2>/dev/null || true
	@echo "Cleaned up."
