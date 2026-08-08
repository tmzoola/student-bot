.PHONY: up down shell migrate makemigrations install run \
        logs logs-app logs-bot logs-db logs-redis logs-all \
        logs-errors logs-timeouts logs-429 logs-slow logs-conflict \
        db-connections db-locks db-slow db-shell \
        redis-info redis-keys redis-flush-sub \
        health

# ─── Docker ───────────────────────────────────────────────────────────────────
up:
	docker compose up -d --build

down:
	docker compose down

shell:
	docker compose exec app bash

# ─── Database (run from project root so alembic.ini is found) ─────────────────
migrate:
	alembic upgrade head

makemigrations:
	alembic revision --autogenerate -m "$(msg)"

# ─── Local dev ────────────────────────────────────────────────────────────────
install:
	pip install -r requirements.txt

run:
	cd app && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# ─── Log kuzatuv (tirik) ──────────────────────────────────────────────────────
# Grafana/Dozzle UI'siz tez ko'rish uchun terminal buyruqlari.

logs:      logs-app     ## Default: app log'i
logs-app:
	docker compose logs -f --tail=200 app

logs-bot:
	docker compose logs -f --tail=200 bot

logs-db:
	docker compose logs -f --tail=100 db

logs-redis:
	docker compose logs -f --tail=100 redis

logs-all:
	docker compose logs -f --tail=100 app bot db redis

# ─── Log xato hisobi (o'tgan 1 soatlik) ──────────────────────────────────────
logs-errors:
	@echo "=== Errors (oxirgi 1 soat) ==="
	@docker compose logs --since 1h 2>&1 | grep -iE "error|traceback|exception" | tail -50

logs-timeouts:
	@echo "=== Timeout / DB pool xatolar (oxirgi 1 soat) ==="
	@docker compose logs --since 1h 2>&1 | grep -iE "timeout|queuepool|pool_timeout|too many connections" | tail -50

logs-429:
	@echo "=== Telegram rate-limit (oxirgi 1 soat) ==="
	@docker compose logs --since 1h 2>&1 | grep -iE "429|too many requests|retry_after|telegramretryafter" | tail -50

logs-slow:
	@echo "=== Sekin so'rovlar (oxirgi 1 soat) ==="
	@docker compose logs --since 1h app 2>&1 | grep -iE "took [0-9]{4,}ms|slow query|took [0-9]+\.[0-9]+s" | tail -50

logs-conflict:
	@echo "=== Bot polling konflikti (oxirgi 1 soat) ==="
	@docker compose logs --since 1h bot 2>&1 | grep -iE "conflict|terminated by other|getupdates" | tail -50

# ─── DB diagnostikasi ────────────────────────────────────────────────────────
db-connections:
	@docker compose exec -T db psql -U $${POSTGRES_USER:-pos} -d $${POSTGRES_DB:-student} \
	  -c "SELECT count(*) AS n, state FROM pg_stat_activity GROUP BY state ORDER BY n DESC;"

db-locks:
	@docker compose exec -T db psql -U $${POSTGRES_USER:-pos} -d $${POSTGRES_DB:-student} \
	  -c "SELECT pid, mode, granted, LEFT(query, 80) AS query FROM pg_locks JOIN pg_stat_activity USING(pid) WHERE NOT granted;"

db-slow:
	@docker compose exec -T db psql -U $${POSTGRES_USER:-pos} -d $${POSTGRES_DB:-student} \
	  -c "SELECT pid, EXTRACT(EPOCH FROM (now()-query_start))::int AS sec, LEFT(query, 120) AS query FROM pg_stat_activity WHERE state='active' AND now()-query_start > interval '1 second' ORDER BY sec DESC LIMIT 10;"

db-shell:
	docker compose exec db psql -U $${POSTGRES_USER:-pos} -d $${POSTGRES_DB:-student}

# ─── Redis diagnostikasi ─────────────────────────────────────────────────────
redis-info:
	@docker compose exec -T redis redis-cli info stats | grep -E "^total_|^keyspace|^connected|^instantaneous" || true
	@docker compose exec -T redis redis-cli info memory | grep -E "^used_memory_human|^used_memory_peak_human|^maxmemory_human" || true

redis-keys:
	@echo -n "Subscription kesh (mk:sub:*): "
	@docker compose exec -T redis redis-cli --scan --pattern 'mk:sub:*' | wc -l

redis-flush-sub:
	@docker compose exec -T redis redis-cli --scan --pattern 'mk:sub:*' | xargs -r docker compose exec -T redis redis-cli del || true
	@echo "Subscription kesh tozalandi"

# ─── /health tekshiruvi ──────────────────────────────────────────────────────
health:
	@curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
