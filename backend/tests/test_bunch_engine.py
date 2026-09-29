from datetime import datetime, timedelta
from app.services.bunch_engine import classify_gap, detect_bunching, events_to_dicts

def test_classify_bunching():
    assert classify_gap(2.0, 8.0, 3.0, 15.0)[0] == "bunching"

def test_classify_large():
    assert classify_gap(16.0, 8.0, 3.0, 15.0)[0] == "large_gap"

def test_classify_normal():
    assert classify_gap(8.0, 8.0, 3.0, 15.0)[0] == "normal"

def test_detect_bunching_events():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "A", "trip_no": "T3", "actual_arrive": base + timedelta(minutes=20)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert len(events) == 2
    assert events[0].status == "bunching"
    assert events[1].status == "large_gap"

def _planned(trip_no, planned, actual):
    return {"stop_name": "A", "trip_no": trip_no, "planned_arrive": planned, "actual_arrive": actual}

def test_late_deviation_excluded_from_pairing():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        _planned("T1", base, base),
        _planned("T2", base + timedelta(minutes=8), base + timedelta(minutes=8)),
        _planned("T3", base + timedelta(minutes=16), base + timedelta(minutes=26)),
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=2.0, late_tolerance_min=5.0)
    dev = [e for e in events if e.status == "deviation"]
    gaps = [e for e in events if e.status != "deviation"]
    assert len(dev) == 1
    assert dev[0].trip_no == "T3"
    assert dev[0].deviation_min == 10.0
    # T3 偏离后不再与邻班配对，只剩 T1→T2
    assert len(gaps) == 1
    assert (gaps[0].earlier_trip, gaps[0].later_trip) == ("T1", "T2")

def test_early_deviation_flagged():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        _planned("T1", base, base),
        _planned("T2", base + timedelta(minutes=8), base + timedelta(minutes=3)),
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=2.0, late_tolerance_min=5.0)
    dev = [e for e in events if e.status == "deviation"]
    assert len(dev) == 1
    assert dev[0].trip_no == "T2"
    assert dev[0].deviation_min == -5.0
    assert "早" in dev[0].suggestion

def test_within_band_still_pairs():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        _planned("T1", base, base),
        _planned("T2", base + timedelta(minutes=8), base + timedelta(minutes=11)),
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=2.0, late_tolerance_min=5.0)
    assert all(e.status != "deviation" for e in events)
    assert len(events) == 1
    assert events[0].gap_min == 11.0

def test_zero_bands_disable_deviation():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        _planned("T1", base, base),
        _planned("T2", base + timedelta(minutes=8), base + timedelta(minutes=30)),
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert all(e.status != "deviation" for e in events)
    assert len(events) == 1
    assert events[0].status == "large_gap"

def test_missing_planned_arrive_not_deviated():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=30)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=2.0, late_tolerance_min=5.0)
    assert all(e.status != "deviation" for e in events)
    assert len(events) == 1

def test_deviation_event_serializes():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [_planned("T1", base, base + timedelta(minutes=20))]
    data = events_to_dicts(detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=2.0, late_tolerance_min=5.0))
    assert len(data) == 1
    assert data[0]["status"] == "deviation"
    assert data[0]["trip_no"] == "T1"
    assert data[0]["deviation_min"] == 20.0
    assert data[0]["planned_arrive"] == base.isoformat()
