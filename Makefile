# NarratoAI Docker Makefile

.PHONY: help build up down restart logs shell clean deploy

# 默认目标
.DEFAULT_GOAL := help

# 变量定义
SERVICE_NAME := narratoai-webui
COMPOSE ?= docker compose
NARRATOAI_WEBUI_PORT ?= 8501

# 颜色定义
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
RESET := \033[0m

help: ## 显示帮助信息
	@echo "$(GREEN)NarratoAI Docker 管理命令$(RESET)"
	@echo ""
	@echo "$(YELLOW)可用命令:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(BLUE)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

deploy: ## 一键部署
	@echo "$(GREEN)执行一键部署...$(RESET)"
	./docker-deploy.sh

build: ## 构建 Docker 镜像
	@echo "$(GREEN)构建 Docker 镜像...$(RESET)"
	NARRATOAI_WEBUI_PORT=$(NARRATOAI_WEBUI_PORT) $(COMPOSE) build

up: ## 启动服务
	@echo "$(GREEN)启动服务...$(RESET)"
	NARRATOAI_WEBUI_PORT=$(NARRATOAI_WEBUI_PORT) $(COMPOSE) up -d
	@echo "$(GREEN)访问地址: http://localhost:$(NARRATOAI_WEBUI_PORT)$(RESET)"

down: ## 停止服务
	@echo "$(YELLOW)停止服务...$(RESET)"
	NARRATOAI_WEBUI_PORT=$(NARRATOAI_WEBUI_PORT) $(COMPOSE) down

restart: ## 重启服务
	@echo "$(YELLOW)重启服务...$(RESET)"
	NARRATOAI_WEBUI_PORT=$(NARRATOAI_WEBUI_PORT) $(COMPOSE) restart

logs: ## 查看日志
	NARRATOAI_WEBUI_PORT=$(NARRATOAI_WEBUI_PORT) $(COMPOSE) logs -f

shell: ## 进入容器
	NARRATOAI_WEBUI_PORT=$(NARRATOAI_WEBUI_PORT) $(COMPOSE) exec $(SERVICE_NAME) bash

ps: ## 查看服务状态
	NARRATOAI_WEBUI_PORT=$(NARRATOAI_WEBUI_PORT) $(COMPOSE) ps

clean: ## 清理未使用的资源
	@echo "$(YELLOW)清理未使用的资源...$(RESET)"
	docker system prune -f

config: ## 检查配置文件
	@if [ -d "config.toml" ]; then \
		if [ -z "$$(find config.toml -mindepth 1 -maxdepth 1 -print -quit)" ]; then \
			echo "$(YELLOW)config.toml 是空目录，删除后重新生成配置文件$(RESET)"; \
			rmdir config.toml; \
		else \
			echo "$(YELLOW)config.toml 是目录且非空，请先备份并删除该目录$(RESET)"; \
			exit 1; \
		fi; \
	fi; \
	if [ -f "config.toml" ]; then \
		echo "$(GREEN)config.toml 存在$(RESET)"; \
	else \
		echo "$(YELLOW)复制示例配置...$(RESET)"; \
		cp config.example.toml config.toml; \
	fi
