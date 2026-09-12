# ICAN Backend

Окремий FastAPI backend для ICAN. Робоче сховище — MongoDB; production
entry point не запускає SQLAlchemy, asyncpg, Alembic або PostgreSQL.

## Локальний запуск

1. Скопіюйте `.env.example` у `.env` і задайте `MONGODB_URL`,
   `MONGODB_DATABASE=ican` та `JWT_SECRET`.
2. Відкрийте `run.py` у VS Code і натисніть **Run Python File in Terminal**,
   або виконайте `python run.py`.
3. Перевірте `http://127.0.0.1:8099/health`.

Очікувана відповідь:

```json
{"status":"ok","storage":"mongodb","database":"ican"}
```

## Production

```bash
uvicorn app.mongo_runtime.main:app --host 0.0.0.0 --port 8099
```

Обов'язкові environment variables не потрібно і не можна комітити:

```env
MONGODB_URL=
MONGODB_DATABASE=ican
JWT_SECRET=
```

Історичні SQL-модулі й Alembic-файли поки збережені лише для перевірки
цілісності та rollback. `app.mongo_runtime.main` їх не імпортує.

## Джерело поточної версії

Код бекенду звірено з `backend/` репозиторію `YEELOW-HELP/ICAN`, гілка
`feature/consultant-workspace-v1`, коміт `3318464`. У цьому окремому
репозиторії збережено адаптації для самостійного запуску: власний `run.py`,
`Procfile`, налаштовуваний `CORS_ORIGINS` і локальні шляхи в тестах.
