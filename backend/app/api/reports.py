import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Arrival, BunchReport, Line, Trip
from app.services.bunch_engine import DeviationEvent, detect_bunching, events_to_dicts
from app.services.scope_helpers import flatten_marks
router = APIRouter(prefix="/reports", tags=["reports"])

def detect_line_events(line: Line, db: Session, stop_name: str | None = None) -> list:
    """报告 / 建议 / 时间轴共用同一套判定；每次按线路当前带宽重算，不吃旧带结果。"""
    trips = db.scalars(select(Trip).where(Trip.line_id == line.id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    arrivals = db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids))).all()
    payload = [{"stop_name": a.stop_name, "trip_no": trip_no_map[a.trip_id],
                "actual_arrive": a.actual_arrive, "planned_arrive": a.planned_arrive}
               for a in arrivals if stop_name is None or a.stop_name == stop_name]
    return detect_bunching(payload, line.planned_headway_min, line.bunch_threshold, line.large_threshold,
                           line.early_tolerance_min or 0.0, line.late_tolerance_min or 0.0)

@router.get("")
def list_reports(db: Session = Depends(get_db)):
    rows = db.scalars(select(BunchReport).order_by(BunchReport.id.desc())).all()
    return [{"id": r.id, "line_id": r.line_id, "stop_name": r.stop_name,
             "created_at": r.created_at.isoformat(), "events": json.loads(r.summary_json)} for r in rows]

@router.post("/run")
def run_detection(line_id: int, stop_name: str | None = None, db: Session = Depends(get_db)):
    line = db.get(Line, line_id)
    if not line: raise HTTPException(404, "线路不存在")
    data = events_to_dicts(detect_line_events(line, db, stop_name))
    report = BunchReport(line_id=line_id, stop_name=stop_name or "*", created_at=datetime.utcnow(),
                         summary_json=json.dumps(data, ensure_ascii=False))
    db.add(report); db.commit(); db.refresh(report)
    return {"id": report.id, "events": data}

@router.get("/suggestions")
def suggestions(line_id: int, db: Session = Depends(get_db)):
    result = run_detection(line_id=line_id, stop_name=None, db=db)
    return {"line_id": line_id, "suggestions": [e for e in result["events"] if e["status"] != "normal"]}

@router.get("/timeline")
def timeline(line_id: int, stop_name: str = "市民中心", db: Session = Depends(get_db)):
    line = db.get(Line, line_id)
    if not line: raise HTTPException(404, "线路不存在")
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    arrivals = sorted(db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids), Arrival.stop_name == stop_name)).all(),
                      key=lambda a: a.actual_arrive)
    if not arrivals: return {"stop_name": stop_name, "marks": []}
    # 与报告 / 建议同一套判定：已偏离班在轴上标偏离，不再被钉成串车端点
    events = detect_line_events(line, db, stop_name)
    trip_status: dict[str, str] = {}
    paired: set[str] = set()
    rank = {"normal": 0, "large_gap": 1, "bunching": 2}
    for e in events:
        if isinstance(e, DeviationEvent):
            trip_status[e.trip_no] = "deviation"
            continue
        for no in (e.earlier_trip, e.later_trip):
            if trip_status.get(no) == "deviation":
                continue
            paired.add(no)
            if rank.get(e.status, 0) > rank.get(trip_status.get(no, "normal"), 0):
                trip_status[no] = e.status
    t0 = arrivals[0].actual_arrive
    span = max((arrivals[-1].actual_arrive - t0).total_seconds(), 1)
    marks = []
    for a in arrivals:
        no = trip_no_map[a.trip_id]
        marks.append({"trip_no": no, "actual_arrive": a.actual_arrive.isoformat(),
                      "pct": round((a.actual_arrive - t0).total_seconds() / span * 100, 2),
                      "status": trip_status.get(no, "normal"), "paired": no in paired})
    return {"stop_name": stop_name, "marks": flatten_marks(marks)}
