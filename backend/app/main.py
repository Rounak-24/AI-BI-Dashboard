"""FastAPI application for Conversational AI BI Dashboards."""
import re
from contextlib import asynccontextmanager
from typing import Any
import multipart.multipart as multipart
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
import io
import uuid

import pandas as pd

from app.database import engine, get_db
from app.llm_service import generate_sql_and_metadata
from app.schema_utils import get_schema_context
from app.config import DATABASE_URL

_byod_tables: set[str] = set()
_conversations: dict[str, dict[str, str]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title="BI Dashboard API",
    description="Conversational AI for Instant Business Intelligence",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    prompt: str
    conversation_id: str | None = None  # For follow-ups; backend stores context
    table_names: list[str] | None = None  # Scope to CSV tables; pass from upload response


class QueryResponse(BaseModel):
    conversation_id: str  # Client uses this for follow-up questions
    sql: str | None
    data: list[dict[str, Any]]
    chart_type: str | None
    insight: str
    error: str | None = None


# --- Query endpoint with Chain-of-Thought, Self-Correction, Hallucination handling ---


def _tables_in_sql(sql: str) -> set[str]:
    """Extract table references from SQL (FROM, JOIN). Handles schema.table."""
    _SKIP = {"SELECT", "ON", "WHERE", "AND", "OR", "LEFT", "RIGHT", "INNER", "OUTER"}
    tables = set()
    for match in re.finditer(
        r'(?:FROM|JOIN)\s+(?:"([^"]+)"|([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?))',
        sql,
        re.IGNORECASE,
    ):
        t = (match.group(1) or match.group(2) or "").strip()
        if not t or t.upper() in _SKIP:
            continue
        # Use table name only for schema.table
        name = t.split(".")[-1] if "." in t else t
        tables.add(name)
    return tables


def _validate_sql_tables(sql: str, allowed_tables: list[str] | None) -> str | None:
    """Return error message if SQL references tables not in allowed_tables, else None."""
    if not allowed_tables:
        return None
    allowed = {t.lower() for t in allowed_tables}
    referenced = _tables_in_sql(sql)
    disallowed = [t for t in referenced if t.lower() not in allowed]
    if disallowed:
        return f"Query references unauthorized table(s): {disallowed}. Only these tables are allowed: {allowed_tables}"
    return None


def execute_sql(sql: str) -> list[dict[str, Any]]:
    """Execute read-only SELECT and return rows as list of dicts."""
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchall()
        columns = result.keys()
        return [dict(zip(columns, row)) for row in rows]


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """
    Natural language to SQL: generates SELECT, runs it, returns data + chart metadata.
    Send conversation_id for follow-up questions; backend manages context internally.
    Client never needs to pass or handle SQL.
    """
    prompt = request.prompt.strip()
    conv_id = request.conversation_id or str(uuid.uuid4())
    prev = _conversations.get(conv_id)
    previous_sql = prev.get("sql") if prev else None
    previous_prompt = prev.get("prompt") if prev else None
    execution_error = None

    for attempt in range(2):  
        try:
            result = generate_sql_and_metadata(
                user_prompt=prompt,
                previous_sql=previous_sql,
                previous_prompt=previous_prompt,
                execution_error=execution_error,
                table_names=request.table_names,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        if result.get("error") == "UNABLE_TO_ANSWER":
            return QueryResponse(
                conversation_id=conv_id,
                sql=None,
                data=[],
                chart_type=None,
                insight=result.get("insight", "Cannot answer with available data."),
                error="UNABLE_TO_ANSWER",
            )

        sql = result["sql"]
        if not sql:
            return QueryResponse(
                conversation_id=conv_id,
                sql=None,
                data=[],
                chart_type=None,
                insight="No SQL was generated.",
                error="NO_SQL",
            )

        table_err = _validate_sql_tables(sql, request.table_names)
        if table_err:
            return QueryResponse(
                conversation_id=conv_id,
                sql=sql,
                data=[],
                chart_type=None,
                insight=table_err,
                error="UNAUTHORIZED_TABLES",
            )

        try:
            data = execute_sql(sql)
        except Exception as e:
            execution_error = str(e)
            previous_sql = sql
            continue  

        _conversations[conv_id] = {"prompt": prompt, "sql": sql}

        return QueryResponse(
            conversation_id=conv_id,
            sql=sql,
            data=data,
            chart_type=result.get("chart_type", "table"),
            insight=result.get("insight", ""),
            error=None,
        )

    return QueryResponse(
        conversation_id=conv_id,
        sql=previous_sql,
        data=[],
        chart_type=None,
        insight=f"SQL execution failed after retry: {execution_error}",
        error="SQL_EXECUTION_FAILED",
    )


# --- BYOD: Bring Your Own Data (CSV upload) ---

@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file. Creates a table in the database and adds it to the schema context.
    Returns the table name for use in queries.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents), nrows=10000)  # Limit rows
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")


    base_name = "".join(c if c.isalnum() or c == "_" else "_" for c in file.filename[:-4])
    table_name = f"byod_{base_name}_{uuid.uuid4().hex[:8]}"

    with engine.connect() as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.commit()

    _byod_tables.add(table_name)
    return {"table_name": table_name, "rows": len(df), "columns": list(df.columns)}


# --- Schema endpoint (for debugging / dynamic context verification) ---

@app.get("/schema")
def get_schema():
    """Return current database schema for LLM context."""
    return {"schema": get_schema_context()}

# --- Health Check Route ---
@app.get("/health")
def health():
    return {"status": "ok"}
