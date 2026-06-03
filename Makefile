# 展示说明：V0.3 常用工程命令，覆盖后端、AI Service、前端、Docker 编排和 RAG 索引/评估复验。
.PHONY: test test-backend test-ai test-frontend rag-index rag-eval dev-backend dev-ai dev-frontend docker-up docker-down docker-logs clean

MAVEN ?= mvn
PYTHON ?= python
NPM ?= npm

test: test-backend test-ai test-frontend

test-backend:
	cd backend && $(MAVEN) test

test-ai:
	cd ai-service && $(PYTHON) -m pytest

test-frontend:
	cd frontend && $(NPM) run build

rag-index:
	cd ai-service && $(PYTHON) eval/build_rag_index.py

rag-eval:
	cd ai-service && $(PYTHON) eval/run_rag_eval.py

dev-backend:
	cd backend && $(MAVEN) spring-boot:run

dev-ai:
	cd ai-service && $(PYTHON) -m uvicorn app.main:app --reload

dev-frontend:
	cd frontend && $(NPM) run dev

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

clean:
	cd backend && $(MAVEN) clean
	cd frontend && $(NPM) run build
