from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.all_models import UsageRecord, ProviderConfiguration
from app.schemas.all_schemas import UsageRecordOut, UsageSummaryOut

router = APIRouter(prefix="/api/usage", tags=["Usage"])


@router.get("/records", response_model=List[UsageRecordOut])
def get_usage_records(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(UsageRecord).order_by(UsageRecord.created_at.desc()).limit(limit).all()


@router.get("/summary", response_model=UsageSummaryOut)
def get_usage_summary(db: Session = Depends(get_db)):
    records = db.query(UsageRecord).all()

    total_requests = len(records)
    manual_requests = sum(1 for r in records if r.mode == "manual")
    api_requests = sum(1 for r in records if r.mode == "api")
    total_tokens = sum(r.total_tokens for r in records)
    total_cost = sum(r.estimated_cost_usd for r in records)

    # Provider breakdown
    by_provider: Dict[str, Dict[str, Any]] = {}
    providers = db.query(ProviderConfiguration).all()
    for p in providers:
        by_provider[p.id] = {
            "display_name": p.display_name,
            "default_mode": p.default_mode,
            "api_configured": p.api_key_configured,
            "requests_count": 0,
            "tokens": 0,
            "estimated_cost_usd": 0.0,
            "monthly_limit_usd": p.usage_limit_monthly_usd
        }

    for r in records:
        pid = r.provider
        if pid not in by_provider:
            by_provider[pid] = {
                "display_name": pid.capitalize(),
                "default_mode": r.mode,
                "api_configured": False,
                "requests_count": 0,
                "tokens": 0,
                "estimated_cost_usd": 0.0,
                "monthly_limit_usd": 0.0
            }
        by_provider[pid]["requests_count"] += 1
        by_provider[pid]["tokens"] += r.total_tokens
        by_provider[pid]["estimated_cost_usd"] = round(
            by_provider[pid]["estimated_cost_usd"] + r.estimated_cost_usd, 4
        )

    return UsageSummaryOut(
        total_requests=total_requests,
        manual_requests=manual_requests,
        api_requests=api_requests,
        total_tokens=total_tokens,
        estimated_total_cost_usd=round(total_cost, 4),
        by_provider=by_provider
    )
