import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from app.config import GROQ_API_KEY
from app.schema_utils import get_schema_context

load_dotenv()

UNABLE_TO_ANSWER_JSON = {
    "error": "UNABLE_TO_ANSWER",
    "sql": None,
    "data": [],
    "chart_type": None,
    "insight": "The question cannot be answered with the available data. Please ask about customer behaviour metrics, demographics, shopping preferences, city tiers, or other fields in the dataset.",
}

SYSTEM_PROMPT = """You are a Business Intelligence assistant that converts natural language questions into PostgreSQL queries.

{schema_context}

## Rules
1. Generate ONLY read-only SELECT SQL. Never modify data.
2. Use proper PostgreSQL syntax. For strings use single quotes.
3. If the question cannot be answered by the schema above, return EXACTLY this JSON (no other text):
   {{"error": "UNABLE_TO_ANSWER", "sql": null, "data": [], "chart_type": null, "insight": "Brief explanation of why the data cannot answer this question."}}

4. Think step by step (chain-of-thought) before outputting the final response.
5. For your final response, output a single JSON object with this structure (no markdown, no code block):
   {{
     "sql": "SELECT ...",
     "chart_type": "bar|line|pie|area|table",
     "insight": "One sentence business insight about the result."
   }}

Choose chart_type based on the data:
- bar: comparisons across categories
- line: trends over ordered values
- pie: proportions of a whole
- area: cumulative or stacked trends
- table: raw data, multiple dimensions, or when chart type is unclear
"""


def _build_system_prompt(table_names: list[str] | None = None) -> str:
    return SYSTEM_PROMPT.format(schema_context=get_schema_context(table_names))


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY") or GROQ_API_KEY
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY environment variable is required. "
            "Set it in .env or: export GROQ_API_KEY=your_key"
        )
    return Groq(api_key=api_key)


def generate_sql_and_metadata(
    user_prompt: str,
    conversation_history: list[dict[str, str]] | None = None,
    previous_sql: str | None = None,
    previous_prompt: str | None = None,
    execution_error: str | None = None,
    table_names: list[str] | None = None,
) -> dict[str, Any]:
    """
    Use Groq to generate SQL and metadata. Supports follow-up context and self-correction.

    Returns:
        {
            "sql": str | None,
            "chart_type": str | None,
            "insight": str,
            "error": str | None  # "UNABLE_TO_ANSWER" when question cannot be answered
        }
    """
    client = _get_client()

    context_parts = [user_prompt]
    if previous_sql and execution_error:
        context_parts.append(
            f"\nThe previous SQL failed with error:\n{execution_error}\n\n"
            "Please fix the SQL and return a valid query."
        )
    elif previous_sql and not execution_error:
        ctx = f"Previous SQL: {previous_sql}"
        if previous_prompt:
            ctx = f"Previous question: {previous_prompt}. {ctx}"
        context_parts.append(f"\n(Follow-up. {ctx})")

    user_content = (
        "## User Question\n"
        + "".join(context_parts)
        + "\n\nOutput the JSON object (sql, chart_type, insight) with no other text:"
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _build_system_prompt(table_names)},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
    )

    text = (response.choices[0].message.content or "").strip()

    if "```json" in text:
        text = re.sub(r"^```json\s*", "", text)
    if "```" in text:
        text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        if "UNABLE_TO_ANSWER" in text.upper():
            return {
                "error": "UNABLE_TO_ANSWER",
                "sql": None,
                "chart_type": None,
                "insight": "The question cannot be answered with the available data.",
            }
        raise ValueError(f"LLM returned invalid JSON: {text[:500]}")

    if data.get("error") == "UNABLE_TO_ANSWER":
        return {
            "error": "UNABLE_TO_ANSWER",
            "sql": None,
            "chart_type": None,
            "insight": data.get("insight", "Cannot answer with available data."),
        }

    sql = data.get("sql", "")
    if sql:
        sql_upper = sql.upper()
        for verb in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]:
            if verb in sql_upper:
                return {
                    "error": "UNABLE_TO_ANSWER",
                    "sql": None,
                    "chart_type": None,
                    "insight": "Only read-only SELECT queries are allowed.",
                }

    return {
        "sql": sql or None,
        "chart_type": data.get("chart_type", "table"),
        "insight": data.get("insight", "No insight provided."),
        "error": None,
    }
