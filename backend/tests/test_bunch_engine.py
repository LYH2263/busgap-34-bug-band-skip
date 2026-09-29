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

def _trips(specs):
    """specs: list of (trip_no, planned_offset_min, actual_offset_min) at stop A."""
    base = datetime(2026, 1, 1, 8, 0)
    return [_planned(no, base + timedelta(minutes=p), base + timedelta(minutes=a))
            for no, p, a in specs]

BAND = dict(early_tolerance_min=2.0, late_tolerance_min=5.0)

def test_middle_deviation_breaks_both_adjacent_pairs():
    # T2 晚到出带（实际仍在 T1/T3 之间）：T1→T2、T2→T3 两个邻班配对都必须拿掉，
    # 且 T1/T3 不得隔着 T2 跨班补配。
    arrivals = _trips([("T1", 0, 0), ("T2", 8, 14), ("T3", 16, 16)])
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, **BAND)
    dev = [e for e in events if e.status == "deviation"]
    gaps = [e for e in events if e.status != "deviation"]
    assert [(e.trip_no, e.status_kind) for e in dev] == [("T2", "late")]
    assert gaps == []

def test_deviation_excluded_from_pair_endpoint_sets():
    # T3 晚到偏离：它既不能当 T2→T3 的 later，也不能当 T3→T4 的 earlier；
    # T2 与 T4 之间隔着真实到站的 T3，不得跨班补配。
    arrivals = _trips([("T1", 0, 0), ("T2", 8, 8), ("T3", 16, 22), ("T4", 24, 24)])
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, **BAND)
    pairs = [(e.earlier_trip, e.later_trip) for e in events if e.status != "deviation"]
    assert pairs == [("T1", "T2")]
    dev_trips = {e.trip_no for e in events if e.status == "deviation"}
    assert dev_trips == {"T3"}
    assert "T3" not in {t for pair in pairs for t in pair}

def test_zero_band_never_flags_deviation_with_plans():
    # 两个允许分钟都为 0 / 缺省时接近只比间隔：即使相对计划严重偏移，也不得打偏离。
    arrivals = _trips([("T1", 0, 0), ("T2", 8, 32), ("T3", 16, 30)])
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert all(e.status != "deviation" for e in events)
    # 实际顺序 T1 → T3(30) → T2(32)：大间隔后紧跟 2 分钟串车
    assert [(e.earlier_trip, e.later_trip, e.status) for e in events] == [
        ("T1", "T3", "large_gap"), ("T3", "T2", "bunching")]

def test_band_change_uses_fresh_band():
    # 同一批到站：宽带宽下在带内只比间隔；收成窄带宽后出带班必须立刻变偏离。
    arrivals = _trips([("T1", 0, 0), ("T2", 8, 12)])
    wide = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=10.0, late_tolerance_min=10.0)
    assert [e.status for e in wide] == ["normal"]
    narrow = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=1.0, late_tolerance_min=1.0)
    assert [(e.status, e.trip_no) for e in narrow if e.status == "deviation"] == [("deviation", "T2")]
    assert [e for e in narrow if e.status != "deviation"] == []

def test_within_band_threshold_pairing_still_applies():
    # 带内仍按现网阈值两两比：T2 在带内（仅早 1 分钟）但与 T1 间隔 2 分钟，照样判串车。
    arrivals = _trips([("T1", 0, 0), ("T2", 3, 2)])
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, **BAND)
    assert len(events) == 1
    assert events[0].status == "bunching"
    assert (events[0].earlier_trip, events[0].later_trip) == ("T1", "T2")

def test_early_and_late_deviation_status_kind():
    arrivals = _trips([("T1", 0, -5), ("T2", 16, 25)])
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, **BAND)
    kinds = {e.trip_no: e.status_kind for e in events if e.status == "deviation"}
    assert kinds == {"T1": "early", "T2": "late"}
    # 偏离建议不得再像串车一样催“后车缓行或抽稀”
    assert all("建议后车缓行或抽稀" not in e.suggestion for e in events if e.status == "deviation")
