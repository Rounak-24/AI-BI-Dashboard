"""Dynamic schema context for LLM - queries database at runtime and injects table/column info."""
from sqlalchemy import inspect

from app.database import engine
from app.config import DATABASE_URL

_IS_POSTGRES = "postgresql" in DATABASE_URL
def get_schema_context(table_names: list[str] | None = None) -> str:
    """
    Query the database schema at runtime and return a string for the LLM prompt.
    If table_names is provided, only those tables are included (for CSV/BYOD scope).
    """
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()
    tables_to_include = table_names if table_names else all_tables

    missing = [t for t in tables_to_include if t not in all_tables]
    if missing:
        return f"Error: Table(s) not found: {missing}. Only query tables that exist."

    parts = []
    for table_name in tables_to_include:
        columns = inspector.get_columns(table_name)
        col_info = []
        for col in columns:
            col_type = str(col["type"]) if col.get("type") else "TEXT"
            col_info.append(f"  - {col['name']} ({col_type})")
        parts.append(f"Table: {table_name}\n" + "\n".join(col_info))

    schema_text = "\n\n".join(parts) if parts else "No tables found."
    scope_note = f" (scoped to: {', '.join(tables_to_include)})" if table_names else ""
    db_name = "PostgreSQL" if _IS_POSTGRES else "SQLite"

    return f"""## Available Database Schema ({db_name}){scope_note}

{schema_text}

You MUST only use the tables listed above. Do not reference any other tables.

## Important Notes
- Use only SELECT queries. No INSERT, UPDATE, DELETE, DROP, or ALTER.
- Use proper {db_name} syntax. For strings use single quotes.
- For aggregate queries, use appropriate GROUP BY clauses.
- If the user's question cannot be answered by these tables and columns, respond with the UNABLE_TO_ANSWER format.
"""
