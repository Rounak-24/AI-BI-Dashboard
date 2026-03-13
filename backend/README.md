# BI Dashboard Backend

Conversational AI for Instant Business Intelligence Dashboards.

## Setup

```bash
uv sync
```

## LLM (Groq)

1. Get an API key at [console.groq.com/keys](https://console.groq.com/keys)
2. Add to `.env`:
   ```
   GROQ_API_KEY=your-groq-api-key
   ```

## Database (Neon PostgreSQL)

1. Create a project at [neon.tech](https://neon.tech)
2. Copy the connection string from **Connection Details**
3. Add to `.env`:
   ```
   DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
   ```

## Seed Database

```bash
uv run python scripts/seed_database.py
```

## Run Server

```bash
uv run python -m uvicorn app.main:app --reload
```
