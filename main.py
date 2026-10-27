import sqlite3
import uuid
import re
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ocr import extract_text
from pdf_report import generate_carbon_report


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATABASE_PATH = BASE_DIR / "carbonkhata.db"

UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

ALLOWED_DOCUMENT_TYPES = {
    "electricity_bill",
    "diesel_invoice",
    "lpg_invoice",
    "other"
}

app = FastAPI(
    title="CarbonKhata API",
    description="Carbon accounting for manufacturing MSMEs",
    version="0.4.0"
)

# Illustrative demo factors only.
# These factors are not validated for formal reporting.
FACTORS = {
    "electricity": 0.71,
    "diesel": 2.68,
    "lpg": 3.00
}


# -------------------- REQUEST MODELS --------------------

class CarbonInput(BaseModel):
    electricity_kwh: float = Field(default=0, ge=0)
    diesel_litres: float = Field(default=0, ge=0)
    lpg_kg: float = Field(default=0, ge=0)
    production_units: float = Field(gt=0)


class ExtractionReview(BaseModel):
    corrected_text: str = Field(min_length=1, max_length=50000)
    approve: bool = False


# -------------------- DATABASE --------------------

def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialise_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                document_type TEXT NOT NULL,
                content_type TEXT,
                file_size INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'awaiting_ocr'
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS extractions (
                document_id TEXT PRIMARY KEY,
                extracted_text TEXT NOT NULL,
                extraction_method TEXT NOT NULL,
                characters_extracted INTEGER NOT NULL,
                extracted_at TEXT NOT NULL,
                review_status TEXT NOT NULL DEFAULT 'needs_review',
                FOREIGN KEY(document_id) REFERENCES documents(id)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS reduction_targets (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                baseline_kg_co2e REAL NOT NULL,
                reduction_percent REAL NOT NULL,
                deadline TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS calculation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calculated_at TEXT NOT NULL,
                electricity_kwh REAL NOT NULL,
                diesel_litres REAL NOT NULL,
                lpg_kg REAL NOT NULL,
                production_units REAL NOT NULL,
                scope_1_kg_co2e REAL NOT NULL,
                scope_2_kg_co2e REAL NOT NULL,
                total_kg_co2e REAL NOT NULL,
                intensity_kg_co2e_per_unit REAL NOT NULL
            )
        """)


initialise_database()


# -------------------- HEALTH --------------------

@app.get("/health")
def health():
    return {"status": "healthy"}


# -------------------- EMISSIONS CALCULATOR --------------------

@app.post("/calculate")
def calculate(data: CarbonInput):
    scope_1 = (
        data.diesel_litres * FACTORS["diesel"]
        + data.lpg_kg * FACTORS["lpg"]
    )

    scope_2 = data.electricity_kwh * FACTORS["electricity"]
    total = scope_1 + scope_2
    intensity = total / data.production_units
    calculated_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO calculation_history (
                calculated_at,
                electricity_kwh,
                diesel_litres,
                lpg_kg,
                production_units,
                scope_1_kg_co2e,
                scope_2_kg_co2e,
                total_kg_co2e,
                intensity_kg_co2e_per_unit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            calculated_at,
            data.electricity_kwh,
            data.diesel_litres,
            data.lpg_kg,
            data.production_units,
            round(scope_1, 3),
            round(scope_2, 3),
            round(total, 3),
            round(intensity, 6)
        ))

    return {
        "scope_1_kg_co2e": round(scope_1, 3),
        "scope_2_kg_co2e": round(scope_2, 3),
        "total_kg_co2e": round(total, 3),
        "total_tonnes_co2e": round(total / 1000, 6),
        "intensity_kg_co2e_per_unit": round(intensity, 6),
        "factor_status": "illustrative_demo_only",
        "calculated_at": calculated_at
    }


# -------------------- CALCULATION HISTORY --------------------

@app.get("/history")
def get_calculation_history(limit: int = 20):
    limit = max(1, min(limit, 100))

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT *
            FROM calculation_history
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

    return {"history": [dict(row) for row in rows]}


# -------------------- REDUCTION RECOMMENDATIONS --------------------

@app.post("/recommendations")
def get_recommendations(data: CarbonInput):
    contributions = {
        "electricity": data.electricity_kwh * FACTORS["electricity"],
        "diesel": data.diesel_litres * FACTORS["diesel"],
        "lpg": data.lpg_kg * FACTORS["lpg"],
    }
    total = sum(contributions.values())
    labels = {"electricity": "Electricity", "diesel": "Diesel", "lpg": "LPG"}
    actions = {
        "electricity": [
            ("Run an energy walk-through", "Check idle equipment, compressed-air leaks, and machines left running between shifts.", "Start with a short weekly meter and equipment checklist."),
            ("Review high-load equipment", "Compare the largest electrical loads and schedule maintenance or efficient replacements where practical.", "Use equipment nameplates and operating hours to prioritise reviews."),
            ("Assess renewable electricity", "Check rooftop solar feasibility or a suitable renewable electricity tariff for your site.", "Request a site-specific feasibility estimate before investing."),
        ],
        "diesel": [
            ("Reduce avoidable fuel use", "Track diesel by vehicle, generator, or machine to identify idling and unusually high consumption.", "Record litres and operating hours weekly."),
            ("Improve maintenance and scheduling", "Keep engines maintained and combine trips or machine runs where operationally possible.", "Compare fuel per operating hour before and after changes."),
            ("Evaluate lower-carbon alternatives", "Assess electrification or other lower-carbon options for suitable equipment when replacement is due.", "Compare lifecycle cost, reliability, and local power availability."),
        ],
        "lpg": [
            ("Check burners and heat processes", "Inspect burners, insulation, and temperature settings for avoidable heat loss.", "Log LPG use against production output for each shift."),
            ("Improve process scheduling", "Reduce unnecessary warm-up time and avoid keeping heat-intensive equipment running when idle.", "Track operating hours and LPG consumption together."),
            ("Review heat recovery options", "Ask a qualified technician whether waste heat recovery or process insulation is practical.", "Estimate feasibility before making equipment changes."),
        ],
    }
    ranked = sorted(contributions.items(), key=lambda item: item[1], reverse=True)
    recommendations = []
    if total <= 0:
        recommendations.append({"priority": 1, "source": "All sources", "title": "Enter current consumption", "reason": "No emissions were calculated from the supplied consumption values.", "action": "Enter electricity, diesel, or LPG usage to receive source-specific recommendations."})
    else:
        for source, value in ranked:
            if value <= 0:
                continue
            share = value / total * 100
            title, reason, action = actions[source][0]
            recommendations.append({"priority": len(recommendations) + 1, "source": labels[source], "share_percent": round(share, 1), "emissions_kg_co2e": round(value, 3), "title": title, "reason": f"{labels[source]} contributes {share:.1f}% of the calculated footprint ({value:.3f} kg CO₂e). {reason}", "action": action})
        # Add a second useful action for the largest source without inventing savings estimates.
        if ranked and ranked[0][1] > 0:
            source = ranked[0][0]
            title, reason, action = actions[source][1]
            recommendations.insert(1, {"priority": 2, "source": labels[source], "share_percent": round(ranked[0][1] / total * 100, 1), "emissions_kg_co2e": round(ranked[0][1], 3), "title": title, "reason": reason, "action": action})
    return {"total_kg_co2e": round(total, 3), "recommendations": recommendations[:4], "note": "Priorities are based on the supplied consumption and illustrative demo emission factors. No guaranteed savings are implied."}


# -------------------- PERSISTENT REDUCTION TARGET --------------------

class ReductionTargetInput(BaseModel):
    baseline_kg_co2e: float = Field(gt=0)
    reduction_percent: float = Field(gt=0, le=100)
    deadline: str = Field(min_length=10, max_length=10)


def target_progress(target, current_kg_co2e=None):
    if target is None:
        return {"configured": False, "message": "Set a baseline, reduction percentage, and deadline to start tracking."}
    baseline = float(target["baseline_kg_co2e"])
    reduction = float(target["reduction_percent"])
    target_value = baseline * (1 - reduction / 100)
    current = None if current_kg_co2e is None else max(0.0, float(current_kg_co2e))
    progress = None
    if current is not None:
        progress = 100.0 if current <= target_value else max(0.0, min(100.0, (baseline - current) / (baseline - target_value) * 100))
    return {"configured": True, "baseline_kg_co2e": round(baseline, 3), "reduction_percent": reduction, "target_kg_co2e": round(target_value, 3), "deadline": target["deadline"], "updated_at": target["updated_at"], "current_kg_co2e": None if current is None else round(current, 3), "progress_percent": None if progress is None else round(progress, 1), "target_reached": None if current is None else current <= target_value, "reduction_achieved_percent": None if current is None else round(max(-1000.0, (baseline-current)/baseline*100), 1)}


@app.get("/targets")
def get_reduction_target(current_kg_co2e: float | None = None):
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM reduction_targets WHERE id = 1").fetchone()
    return target_progress(row, current_kg_co2e)


@app.put("/targets")
def save_reduction_target(data: ReductionTargetInput):
    try:
        from datetime import date
        date.fromisoformat(data.deadline)
    except ValueError:
        raise HTTPException(422, "Deadline must be a valid date in YYYY-MM-DD format.")
    updated_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO reduction_targets (id, baseline_kg_co2e, reduction_percent, deadline, updated_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                baseline_kg_co2e = excluded.baseline_kg_co2e,
                reduction_percent = excluded.reduction_percent,
                deadline = excluded.deadline,
                updated_at = excluded.updated_at
        """, (data.baseline_kg_co2e, data.reduction_percent, data.deadline, updated_at))
        row = connection.execute("SELECT * FROM reduction_targets WHERE id = 1").fetchone()
    return target_progress(row)




# -------------------- PDF CARBON REPORT --------------------

@app.post("/reports/carbon-pdf")
def download_carbon_report(data: CarbonInput):
    total = (
        data.electricity_kwh * FACTORS["electricity"]
        + data.diesel_litres * FACTORS["diesel"]
        + data.lpg_kg * FACTORS["lpg"]
    )

    with get_connection() as connection:
        target = connection.execute(
            "SELECT * FROM reduction_targets WHERE id = 1"
        ).fetchone()

    target_data = target_progress(target, total)

    try:
        report_path = generate_carbon_report(
            data.model_dump(),
            target=target_data if target_data["configured"] else None
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc))

    return FileResponse(
        path=report_path,
        media_type="application/pdf",
        filename=report_path.name
    )


# -------------------- DOCUMENT UPLOAD --------------------

@app.post("/documents/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...)
):
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(400, "Unsupported document type.")

    original_name = Path(file.filename or "").name
    extension = Path(original_name).suffix.lower()

    if not original_name or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            "Upload a PDF, JPG, JPEG, or PNG file."
        )

    document_id = str(uuid.uuid4())
    stored_filename = document_id + extension
    destination = UPLOAD_DIR / stored_filename
    size = 0

    try:
        with destination.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                size += len(chunk)

                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        413,
                        "File exceeds the 10 MB limit."
                    )

                output.write(chunk)

        if size == 0:
            raise HTTPException(400, "The uploaded file is empty.")

        uploaded_at = datetime.now(timezone.utc).isoformat()

        with get_connection() as connection:
            connection.execute("""
                INSERT INTO documents (
                    id,
                    original_filename,
                    stored_filename,
                    document_type,
                    content_type,
                    file_size,
                    uploaded_at,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                original_name,
                stored_filename,
                document_type,
                file.content_type,
                size,
                uploaded_at,
                "awaiting_ocr"
            ))

        return {
            "id": document_id,
            "filename": original_name,
            "document_type": document_type,
            "file_size_bytes": size,
            "uploaded_at": uploaded_at,
            "status": "awaiting_ocr"
        }

    except Exception:
        if destination.exists():
            destination.unlink()
        raise

    finally:
        await file.close()


# -------------------- DOCUMENT LIST --------------------

@app.get("/documents")
def list_documents():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                id,
                original_filename,
                document_type,
                content_type,
                file_size,
                uploaded_at,
                status
            FROM documents
            ORDER BY uploaded_at DESC
        """).fetchall()

    return {
        "documents": [dict(row) for row in rows]
    }


# -------------------- SINGLE DOCUMENT --------------------

@app.get("/documents/{document_id}")
def get_document(document_id: str):
    with get_connection() as connection:
        row = connection.execute("""
            SELECT
                id,
                original_filename,
                document_type,
                content_type,
                file_size,
                uploaded_at,
                status
            FROM documents
            WHERE id = ?
        """, (document_id,)).fetchone()

    if row is None:
        raise HTTPException(404, "Document not found.")

    return dict(row)


# -------------------- OCR EXTRACTION --------------------

@app.post("/documents/{document_id}/extract")
def extract_document(document_id: str):
    with get_connection() as connection:
        document = connection.execute("""
            SELECT stored_filename
            FROM documents
            WHERE id = ?
        """, (document_id,)).fetchone()

    if document is None:
        raise HTTPException(404, "Document not found.")

    file_path = UPLOAD_DIR / document["stored_filename"]

    try:
        result = extract_text(str(file_path))

    except FileNotFoundError:
        raise HTTPException(
            404,
            "Stored document file not found."
        )

    except ValueError as error:
        raise HTTPException(400, str(error))

    except Exception as error:
        if "tesseract" in str(error).lower():
            raise HTTPException(
                503,
                "Image OCR requires the Tesseract engine to be installed."
            )

        raise HTTPException(
            422,
            "Could not extract text from this document."
        )

    extracted_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO extractions (
                document_id,
                extracted_text,
                extraction_method,
                characters_extracted,
                extracted_at,
                review_status
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(document_id) DO UPDATE SET
                extracted_text = excluded.extracted_text,
                extraction_method = excluded.extraction_method,
                characters_extracted = excluded.characters_extracted,
                extracted_at = excluded.extracted_at,
                review_status = 'needs_review'
        """, (
            document_id,
            result["text"],
            result["method"],
            result["characters_extracted"],
            extracted_at,
            "needs_review"
        ))

        connection.execute("""
            UPDATE documents
            SET status = ?
            WHERE id = ?
        """, ("needs_review", document_id))

    return {
        "document_id": document_id,
        "extraction_method": result["method"],
        "characters_extracted": result["characters_extracted"],
        "extracted_text": result["text"],
        "review_status": "needs_review",
        "message": "Review extracted text before using it in calculations."
    }


# -------------------- GET EXTRACTION --------------------

@app.get("/documents/{document_id}/extraction")
def get_extraction(document_id: str):
    with get_connection() as connection:
        row = connection.execute("""
            SELECT
                extracted_text,
                extraction_method,
                characters_extracted,
                extracted_at,
                review_status
            FROM extractions
            WHERE document_id = ?
        """, (document_id,)).fetchone()

    if row is None:
        raise HTTPException(
            404,
            "No extraction found for this document."
        )

    return {
        "document_id": document_id,
        **dict(row)
    }


# -------------------- DOWNLOAD ORIGINAL DOCUMENT --------------------

@app.get("/documents/{document_id}/file")
def download_document(document_id: str):
    with get_connection() as connection:
        row = connection.execute("""
            SELECT
                stored_filename,
                original_filename,
                content_type
            FROM documents
            WHERE id = ?
        """, (document_id,)).fetchone()

    if row is None:
        raise HTTPException(404, "Document not found.")

    path = UPLOAD_DIR / row["stored_filename"]

    if not path.is_file():
        raise HTTPException(404, "Stored file not found.")

    return FileResponse(
        path=path,
        media_type=row["content_type"] or "application/octet-stream",
        filename=row["original_filename"]
    )


# -------------------- REVIEW AND APPROVAL --------------------

@app.post("/documents/{document_id}/review")
def review_extraction(
    document_id: str,
    review: ExtractionReview
):
    reviewed_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        existing = connection.execute("""
            SELECT document_id
            FROM extractions
            WHERE document_id = ?
        """, (document_id,)).fetchone()

        if existing is None:
            raise HTTPException(
                404,
                "No extraction found for this document."
            )

        status = (
            "approved"
            if review.approve
            else "needs_review"
        )

        connection.execute("""
            UPDATE extractions
            SET
                extracted_text = ?,
                review_status = ?,
                extracted_at = ?
            WHERE document_id = ?
        """, (
            review.corrected_text,
            status,
            reviewed_at,
            document_id
        ))

        connection.execute("""
            UPDATE documents
            SET status = ?
            WHERE id = ?
        """, (status, document_id))

    return {
        "document_id": document_id,
        "review_status": status,
        "reviewed_at": reviewed_at,
        "message": (
            "Extraction approved."
            if review.approve
            else "Corrections saved. Review is still pending."
        )
    }




# -------------------- APPROVED BILL VALUE SUGGESTION --------------------

def parse_consumption_value(text: str, document_type: str):
    """
    Extract one clearly labelled consumption quantity from reviewed text.
    This intentionally does not infer consumption from a bill's currency amount.
    """
    number = r"([0-9][0-9,]*(?:\.[0-9]+)?)"

    patterns = {
        "electricity_bill": [
            re.compile(
                rf"(?:electricity\s+consumed|energy\s+consumed|units\s+consumed|"
                rf"consumed\s+units|total\s+units|consumption\s+units|"
                rf"electricity\s+usage)\s*[:=\-]?\s*{number}\s*(?:kwh|units?)\b",
                re.IGNORECASE,
            ),
            re.compile(
                rf"(?:electricity\s+consumed|energy\s+consumed|units\s+consumed|"
                rf"consumed\s+units|total\s+units|consumption\s+units)\s*[:=\-]?\s*{number}\b",
                re.IGNORECASE,
            ),
        ],
        "diesel_invoice": [
            re.compile(
                rf"(?:diesel(?:\s+(?:quantity|consumed|purchased|usage))?|"
                rf"quantity\s+of\s+diesel|fuel\s+quantity)\s*[:=\-]?\s*{number}\s*"
                rf"(?:litres?|liters?|ltrs?|ltr|l)\b",
                re.IGNORECASE,
            ),
            re.compile(
                rf"(?:quantity|volume)\s*[:=\-]?\s*{number}\s*(?:litres?|liters?|ltrs?|ltr)\b",
                re.IGNORECASE,
            ),
        ],
        "lpg_invoice": [
            re.compile(
                rf"(?:lpg(?:\s+(?:quantity|consumed|usage))?|"
                rf"liquefied\s+petroleum\s+gas|gas\s+quantity)\s*[:=\-]?\s*{number}\s*kg\b",
                re.IGNORECASE,
            ),
            re.compile(
                rf"(?:quantity|net\s+weight|cylinder\s+weight)\s*[:=\-]?\s*{number}\s*kg\b",
                re.IGNORECASE,
            ),
        ],
    }

    field_map = {
        "electricity_bill": ("electricity_kwh", "kWh"),
        "diesel_invoice": ("diesel_litres", "litres"),
        "lpg_invoice": ("lpg_kg", "kg"),
    }

    if document_type not in patterns:
        return None

    for pattern in patterns[document_type]:
        match = pattern.search(text)
        if match:
            raw_value = match.group(1).replace(",", "")
            try:
                value = float(raw_value)
            except ValueError:
                continue
            if value < 0:
                continue
            field, unit = field_map[document_type]
            return {
                "field": field,
                "value": value,
                "unit": unit,
                "matched_text": match.group(0).strip(),
            }

    return None


@app.get("/documents/{document_id}/consumption")
def suggest_document_consumption(document_id: str):
    with get_connection() as connection:
        row = connection.execute("""
            SELECT
                d.document_type,
                d.status,
                e.extracted_text,
                e.review_status
            FROM documents d
            LEFT JOIN extractions e ON e.document_id = d.id
            WHERE d.id = ?
        """, (document_id,)).fetchone()

    if row is None:
        raise HTTPException(404, "Document not found.")

    if row["status"] != "approved" or row["review_status"] != "approved":
        raise HTTPException(
            409,
            "Approve the reviewed extraction before using bill values."
        )

    suggestion = parse_consumption_value(
        row["extracted_text"] or "",
        row["document_type"],
    )

    if suggestion is None:
        raise HTTPException(
            422,
            "Could not confidently identify a consumption quantity. "
            "Edit the extracted text to include a clear label and unit, "
            "for example: 'Electricity Consumed: 1250 kWh', then approve it again."
        )

    return {
        "document_id": document_id,
        "document_type": row["document_type"],
        **suggestion,
        "message": "Consumption quantity found in the approved text. Verify it before calculating.",
    }


# -------------------- DASHBOARD --------------------

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)


@app.get("/dashboard", include_in_schema=False)
@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(
        BASE_DIR / "static" / "index.html"
    )

