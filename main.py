from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="CarbonKhata API",
    description="Carbon accounting for manufacturing MSMEs",
    version="0.1.0"
)

# Illustrative demo factors only; not verified reporting factors.
FACTORS = {
    "electricity": 0.71,
    "diesel": 2.68,
    "lpg": 3.00
}


class CarbonInput(BaseModel):
    electricity_kwh: float = Field(default=0, ge=0)
    diesel_litres: float = Field(default=0, ge=0)
    lpg_kg: float = Field(default=0, ge=0)
    production_units: float = Field(gt=0)


@app.get("/")
def home():
    return {"project": "CarbonKhata", "status": "running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/calculate")
def calculate(data: CarbonInput):
    scope_1 = (
        data.diesel_litres * FACTORS["diesel"]
        + data.lpg_kg * FACTORS["lpg"]
    )
    scope_2 = data.electricity_kwh * FACTORS["electricity"]
    total = scope_1 + scope_2

    return {
        "scope_1_kg_co2e": round(scope_1, 3),
        "scope_2_kg_co2e": round(scope_2, 3),
        "total_kg_co2e": round(total, 3),
        "total_tonnes_co2e": round(total / 1000, 6),
        "intensity_kg_co2e_per_unit": round(
            total / data.production_units, 6
        ),
        "factor_status": "illustrative_demo_only"
    }
