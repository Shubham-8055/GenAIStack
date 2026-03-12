"""
External DB helper — connects to a user's external database and queries
their transaction table with dynamic column mappings.
"""
from typing import List
from sqlalchemy import create_engine, text


def query_external_db(
    connection_string: str,
    table_name: str,
    column_mappings: dict,
    extracted_params: dict,
    tool_agent_fields: list = None,
    limit: int = 10,
) -> List[dict]:
    """
    Query an external database for transactions.

    Args:
        connection_string: DB connection string (postgresql://..., mysql://..., etc.)
        table_name: The table to query.
        column_mappings: {date_col, amount_col, status_col, ...} — maps logical names to actual column names.
        extracted_params: LLM-extracted params {date, amount, aadhaar_last4, ...}
        tool_agent_fields: List of custom field defs [{name, label}]
        limit: Max results.

    Returns:
        List of dicts with all columns from the result.
    """
    tool_agent_fields = tool_agent_fields or []

    try:
        engine = create_engine(connection_string, pool_pre_ping=True)

        # Build WHERE clauses
        conditions = []
        bind_params = {}

        # Date filter (with ±1 day fuzzy match)
        date_col = column_mappings.get("date_col", "txn_date")
        date_val = extracted_params.get("date")
        if date_val:
            conditions.append(f"CAST({date_col} AS DATE) BETWEEN :date_start AND :date_end")
            bind_params["date_start"] = date_val  # Will be parsed by DB
            bind_params["date_end"] = date_val

        # Amount filter
        amount_col = column_mappings.get("amount_col", "amount")
        amount_val = extracted_params.get("amount")
        if amount_val is not None:
            conditions.append(f"{amount_col} = :amount")
            bind_params["amount"] = amount_val

        # Custom field filters
        for field in tool_agent_fields:
            field_name = field.get("name", "")
            field_val = extracted_params.get(field_name)
            if field_val:
                # Check if there's a column mapping for this field
                col_name = column_mappings.get(f"{field_name}_col", field_name)
                conditions.append(f"CAST({col_name} AS VARCHAR) = :f_{field_name}")
                bind_params[f"f_{field_name}"] = str(field_val)

        # Build query
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order_col = column_mappings.get("date_col", "txn_date")
        query = f"SELECT * FROM {table_name} WHERE {where_clause} ORDER BY {order_col} DESC LIMIT :lim"
        bind_params["lim"] = limit

        print(f"[ExternalDB] Query: {query}")
        print(f"[ExternalDB] Params: {bind_params}")

        with engine.connect() as conn:
            result = conn.execute(text(query), bind_params)
            rows = [dict(row._mapping) for row in result]
            print(f"[ExternalDB] Found {len(rows)} results")
            return rows

    except Exception as e:
        print(f"[ExternalDB] Error: {e}")
        return []


def test_external_connection(connection_string: str, table_name: str) -> dict:
    """Test if we can connect and access the table."""
    try:
        engine = create_engine(connection_string, pool_pre_ping=True)
        with engine.connect() as conn:
            # Check table exists and get column names
            result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 1"))
            columns = list(result.keys())
            row_count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()

            return {
                "success": True,
                "columns": columns,
                "row_count": row_count,
                "message": f"Connected successfully! Table '{table_name}' has {row_count} rows and {len(columns)} columns.",
            }
    except Exception as e:
        return {
            "success": False,
            "columns": [],
            "row_count": 0,
            "message": f"Connection failed: {str(e)}",
        }


def format_external_results(rows: list, column_mappings: dict, tool_agent_fields: list = None) -> str:
    """Format external DB query results into readable markdown."""
    tool_agent_fields = tool_agent_fields or []

    if not rows:
        return ("No matching transactions found. Please check the details "
                "and try again with the correct parameters.")

    result_lines = [f"Found **{len(rows)}** matching transaction(s):\n"]

    status_col = column_mappings.get("status_col", "status")
    amount_col = column_mappings.get("amount_col", "amount")
    date_col = column_mappings.get("date_col", "txn_date")

    for i, row in enumerate(rows, 1):
        status = str(row.get(status_col, "unknown")).lower()
        status_emoji = {"success": "✅", "failed": "❌", "pending": "⏳"}.get(status, "❓")

        # Build table rows from all columns
        table_rows = []
        for col, val in row.items():
            # Format the column name nicely
            nice_name = col.replace("_", " ").title()
            if col == status_col:
                table_rows.append(f"| **{nice_name}** | {status_emoji} {str(val).upper()} |")
            elif col == amount_col:
                table_rows.append(f"| **{nice_name}** | ₹{val} |")
            else:
                table_rows.append(f"| **{nice_name}** | {val} |")

        result_lines.append(
            f"### Transaction {i}\n"
            f"| Field | Details |\n"
            f"|---|---|\n"
            + "\n".join(table_rows) + "\n"
        )

    return "\n".join(result_lines)
