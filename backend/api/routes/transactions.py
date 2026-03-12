"""
Transaction management routes — seed sample data, CSV import, list transactions,
and external DB test connection.
"""
import csv
import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.engine import get_db
from backend.db import crud
from backend.models.database import Transaction
from backend.models.schemas import TransactionResponse
from backend.core.external_db import test_external_connection

router = APIRouter(prefix="/projects/{project_id}/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all transactions for a project."""
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return await crud.get_transactions(db, project_id)


@router.post("/seed")
async def seed_transactions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Seed 20 sample transactions for testing the tool-call agent."""
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    config = await crud.get_agent_config(db, project_id)
    fields = config.tool_agent_fields if config else []

    count = await crud.seed_sample_transactions(db, project_id, tool_agent_fields=fields)
    return {"status": "seeded", "count": count, "project_id": str(project_id)}


@router.post("/import-csv")
async def import_csv(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Import transactions from a CSV file.
    Expected columns: date, amount, status, txn_type, bank_name, rrn, remarks
    Plus any custom field columns matching the configured tool_agent_fields names.
    """
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    config = await crud.get_agent_config(db, project_id)
    field_names = [f["name"] for f in (config.tool_agent_fields or [])]

    # Read CSV
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # Handle BOM
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows_imported = 0
    errors = []

    for i, row in enumerate(reader, 1):
        try:
            # Parse date
            date_str = row.get("date", "") or row.get("txn_date", "") or row.get("Date", "")
            if not date_str:
                errors.append(f"Row {i}: Missing date column")
                continue

            try:
                txn_date = datetime.fromisoformat(date_str.strip())
            except ValueError:
                # Try common formats
                for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        txn_date = datetime.strptime(date_str.strip(), fmt)
                        break
                    except ValueError:
                        continue
                else:
                    errors.append(f"Row {i}: Could not parse date '{date_str}'")
                    continue

            if txn_date.tzinfo is None:
                txn_date = txn_date.replace(tzinfo=timezone.utc)

            # Parse amount
            amount_str = row.get("amount", "") or row.get("Amount", "") or "0"
            amount = float(str(amount_str).replace(",", "").replace("₹", "").strip())

            # Build custom fields
            custom = {}
            aadhaar_val = ""
            for fname in field_names:
                val = row.get(fname, "") or ""
                if val:
                    custom[fname] = val.strip()
                    if fname == "aadhaar_last4":
                        aadhaar_val = val.strip()

            txn = Transaction(
                project_id=project_id,
                txn_date=txn_date,
                amount=amount,
                aadhaar_last4=aadhaar_val,
                status=(row.get("status", "") or row.get("Status", "") or "pending").strip().lower(),
                txn_type=(row.get("txn_type", "") or row.get("type", "") or row.get("Type", "") or "debit").strip().lower(),
                bank_name=(row.get("bank_name", "") or row.get("bank", "") or row.get("Bank", "") or "").strip(),
                rrn=(row.get("rrn", "") or row.get("RRN", "") or "").strip(),
                remarks=(row.get("remarks", "") or row.get("Remarks", "") or "").strip(),
                custom_fields=custom,
            )
            db.add(txn)
            rows_imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    if rows_imported > 0:
        await db.commit()

    return {
        "status": "imported",
        "rows_imported": rows_imported,
        "errors": errors[:10],  # Return first 10 errors max
        "total_errors": len(errors),
    }


class TestConnectionRequest(BaseModel):
    connection_string: str
    table_name: str


@router.post("/test-connection")
async def test_connection(
    project_id: uuid.UUID,
    body: TestConnectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Test an external database connection."""
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    result = test_external_connection(body.connection_string, body.table_name)
    return result
