"""FastAPI application for Conversational AI BI Dashboards."""
import re
from contextlib import asynccontextmanager
from typing import Any
import json
import time
from fastapi import FastAPI, HTTPException, UploadFile, Request
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

_DEBUG_LOG_PATH = r"c:\Projects\AI BI DASHBOARD FINAL\debug-5baeac.log"
_DEBUG_SESSION_ID = "5baeac"

def _dbg(location: str, message: str, data: dict[str, Any] | None = None, *, run_id: str = "run1", hypothesis_id: str = "A") -> None:
    try:
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": _DEBUG_SESSION_ID,
                        "runId": run_id,
                        "hypothesisId": hypothesis_id,
                        "location": location,
                        "message": message,
                        "data": data or {},
                        "timestamp": int(time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass

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

@app.middleware("http")
async def _debug_request_middleware(request: Request, call_next):
    # region agent log
    ct = (request.headers.get("content-type") or "").lower()
    _dbg(
        location="backend/app/main.py:middleware",
        message="incoming request",
        data={"method": request.method, "path": request.url.path, "contentType": ct},
        hypothesis_id="A",
    )
    # endregion agent log
    return await call_next(request)

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


# CSV File Upload Route ---

@app.post("/upload-csv")
@app.post("/upload-csv/")
async def upload_csv(request: Request):
    """
    Upload CSV via multipart form (any file field) OR raw body with Content-Type text/csv or application/octet-stream.
    """
    contents = None
    filename = None
    ct = (request.headers.get("content-type") or "").lower().split(";")[0].strip()

    if "multipart/form-data" in ct:
        # IMPORTANT: request.form() consumes the stream; do NOT call request.body() afterwards.
        try:
            form = await request.form()
            # region agent log
            _dbg(
                location="backend/app/main.py:upload_csv",
                message="multipart form keys/types",
                data={
                    "keys": list(form.keys()),
                    "types": {k: type(form.get(k)).__name__ for k in form.keys()},
                },
                hypothesis_id="D",
            )
            # endregion agent log
            for key in form:
                value = form.get(key)
                if isinstance(value, UploadFile):
                    contents = await value.read()
                    filename = value.filename or "upload.csv"
                    break
                if isinstance(value, str) and ("," in value or "\n" in value):
                    # Form field sent as text (pasted CSV) instead of File
                    contents = value.encode("utf-8")
                    filename = "upload.csv"
                    break
        except Exception as e:
            # region agent log
            _dbg(
                location="backend/app/main.py:upload_csv",
                message="multipart parse failed",
                data={"error": str(e), "contentType": (request.headers.get("content-type") or "")},
                hypothesis_id="C",
            )
            # endregion agent log

        # region agent log
        _dbg(
            location="backend/app/main.py:upload_csv",
            message="multipart parsed",
            data={"filename": filename, "contentBytes": len(contents) if contents else 0},
            hypothesis_id="B",
        )
        # endregion agent log

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="No CSV file found in form-data. In Postman: Body -> form-data, set the CSV field type to File (not Text), and do not manually set the Content-Type header.",
            )
    else:
        # Raw body (Postman 'binary' / 'raw' or pasted CSV text)
        raw = await request.body()
        if raw and (
            ct.startswith("text/csv")
            or ct.startswith("text/plain")
            or ct.startswith("application/octet-stream")
            or not ct
        ):
            # If it's text/*, normalize to UTF-8 bytes (reject obviously-non-CSV JSON)
            if ct.startswith("text/"):
                try:
                    text_body = raw.decode("utf-8-sig", errors="strict")
                    if text_body.lstrip().startswith("{") or text_body.lstrip().startswith("["):
                        raise ValueError("Looks like JSON, not CSV")
                    raw = text_body.encode("utf-8")
                except Exception as e:
                    # region agent log
                    _dbg(
                        location="backend/app/main.py:upload_csv",
                        message="raw text decode failed",
                        data={"error": str(e), "contentType": (request.headers.get("content-type") or "")},
                        hypothesis_id="E",
                    )
                    # endregion agent log
                    raise HTTPException(status_code=400, detail="Raw body could not be decoded as UTF-8 CSV text.")

            contents = raw
            filename = "upload.csv"

    # region agent log
    _dbg(
        location="backend/app/main.py:upload_csv",
        message="parsed upload request (final)",
        data={
            "contentType": (request.headers.get("content-type") or ""),
            "filename": filename,
            "contentBytes": len(contents) if contents else 0,
        },
        hypothesis_id="B",
    )
    # endregion agent log

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Upload failed. Send form-data with a file (any key), or raw body with header Content-Type: text/csv or application/octet-stream."
        )

    if filename and not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        df = pd.read_csv(io.BytesIO(contents), nrows=10000)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")

    base_name = "upload"
    if filename:
        base_name = "".join(c if c.isalnum() or c == "_" else "_" for c in filename[:-4])
    table_name = f"byod_{base_name}_{uuid.uuid4().hex[:8]}"

    with engine.connect() as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)

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
