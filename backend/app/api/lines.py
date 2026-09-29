from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Line
router = APIRouter(prefix="/lines", tags=["lines"])

class LineIn(BaseModel):
    code: str
    name: str
    planned_headway_min: float = 8.0
    bunch_threshold: float = 3.0
    large_threshold: float = 15.0
    early_tolerance_min: float = Field(default=0.0, ge=0)
    late_tolerance_min: float = Field(default=0.0, ge=0)

class LineUpdate(BaseModel):
    name: str | None = None
    planned_headway_min: float | None = None
    bunch_threshold: float | None = None
    large_threshold: float | None = None
    early_tolerance_min: float | None = Field(default=None, ge=0)
    late_tolerance_min: float | None = Field(default=None, ge=0)

def line_dict(r: Line) -> dict:
    return {"id": r.id, "code": r.code, "name": r.name, "planned_headway_min": r.planned_headway_min,
            "bunch_threshold": r.bunch_threshold, "large_threshold": r.large_threshold,
            "early_tolerance_min": r.early_tolerance_min, "late_tolerance_min": r.late_tolerance_min}

@router.get("")
def list_lines(db: Session = Depends(get_db)):
    rows = db.scalars(select(Line).order_by(Line.id)).all()
    return [line_dict(r) for r in rows]

@router.post("", status_code=201)
def create_line(body: LineIn, db: Session = Depends(get_db)):
    line = Line(**body.model_dump())
    db.add(line); db.commit(); db.refresh(line)
    return line_dict(line)

@router.put("/{line_id}")
def update_line(line_id: int, body: LineUpdate, db: Session = Depends(get_db)):
    line = db.get(Line, line_id)
    if not line: raise HTTPException(404, "线路不存在")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(line, field, value)
    db.commit(); db.refresh(line)
    return line_dict(line)
