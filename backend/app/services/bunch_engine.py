"""Bus bunching: planned headway vs actual arrival gaps.

参与集规则（报告 / 建议 / 时间轴必须同一套）：
1. 启用带宽（早到或晚到容忍分钟 > 0）时，先按实际到站顺序逐班判偏离；
2. 出带的班先记 ``deviation`` 事件，并且不进入邻班串车 / 大间隔配对集；
3. 串车 / 大间隔只在“相邻两班都在带内”时才生成，偏离优先、与继续配对互斥；
4. 两个允许分钟都为 0 时带宽关闭，只按实际间隔两两比较，绝不无故打偏离；
5. 带内的班一律按现网 bunch / large 阈值两两比较。
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime

@dataclass
class GapEvent:
    stop_name: str
    earlier_trip: str
    later_trip: str
    gap_min: float
    planned_headway_min: float
    status: str
    suggestion: str

@dataclass
class DeviationEvent:
    stop_name: str
    trip_no: str
    deviation_min: float
    planned_arrive: str
    actual_arrive: str
    status: str
    status_kind: str
    suggestion: str

def classify_gap(gap_min: float, planned_headway_min: float, bunch_threshold: float, large_threshold: float) -> tuple[str, str]:
    if gap_min < bunch_threshold:
        return ("bunching", f"间隔 {gap_min:.1f} 分钟低于串车阈值 {bunch_threshold}，建议后车缓行或抽稀。")
    if gap_min > large_threshold:
        return ("large_gap", f"间隔 {gap_min:.1f} 分钟超过大间隔阈值 {large_threshold}，建议前车减速或加发。")
    return ("normal", f"间隔接近计划 {planned_headway_min:.1f} 分钟，保持即可。")

def deviation_minutes(arrival: dict) -> float | None:
    planned = arrival.get("planned_arrive")
    if planned is None:
        return None
    return (arrival["actual_arrive"] - planned).total_seconds() / 60.0

def band_is_active(early_tolerance_min: float, late_tolerance_min: float) -> bool:
    """两个允许分钟都为 0 时带宽关闭，只比间隔，不判偏离。"""
    return early_tolerance_min > 0 or late_tolerance_min > 0

def is_deviated(deviation_min: float, early_tolerance_min: float, late_tolerance_min: float) -> bool:
    return deviation_min < -early_tolerance_min or deviation_min > late_tolerance_min

def deviation_kind(deviation_min: float) -> str:
    return "early" if deviation_min < 0 else "late"

def classify_deviation(deviation_min: float, early_tolerance_min: float, late_tolerance_min: float) -> str:
    if deviation_min < -early_tolerance_min:
        return (f"实际到站比计划早 {abs(deviation_min):.1f} 分钟，超出允许早到带宽 "
                f"{early_tolerance_min:g} 分钟，标记偏离；该班不参与串车/大间隔配对，无需缓行抽稀。")
    return (f"实际到站比计划晚 {deviation_min:.1f} 分钟，超出允许晚到带宽 "
            f"{late_tolerance_min:g} 分钟，标记偏离；该班不参与串车/大间隔配对，无需缓行抽稀。")

def detect_bunching(arrivals: list[dict], planned_headway_min: float, bunch_threshold: float, large_threshold: float,
                    early_tolerance_min: float = 0.0, late_tolerance_min: float = 0.0) -> list[GapEvent | DeviationEvent]:
    band_active = band_is_active(early_tolerance_min, late_tolerance_min)
    by_stop: dict[str, list[dict]] = {}
    for a in arrivals:
        by_stop.setdefault(a["stop_name"], []).append(a)
    events: list[GapEvent | DeviationEvent] = []
    for stop, items0 in by_stop.items():
        items = sorted(items0, key=lambda x: x["actual_arrive"])
        # 逐班判偏离：出带只记偏离事件，并标掉它，绝不进入任何配对
        dev_of: dict[str, float | None] = {}
        for a in items:
            dev = deviation_minutes(a) if band_active else None
            if dev is not None and is_deviated(dev, early_tolerance_min, late_tolerance_min):
                dev_of[a["trip_no"]] = dev
                events.append(DeviationEvent(
                    stop, a["trip_no"], round(dev, 2),
                    a["planned_arrive"].isoformat(), a["actual_arrive"].isoformat(),
                    "deviation", deviation_kind(dev),
                    classify_deviation(dev, early_tolerance_min, late_tolerance_min)))
            else:
                dev_of[a["trip_no"]] = None
        # 只对原始到站顺序里的真邻班两两比较，且两端都必须在带内。
        # 偏离班被抽走后，两侧的班不跨班补配（偏离优先、与继续配对互斥）。
        for i in range(1, len(items)):
            prev, cur = items[i - 1], items[i]
            if dev_of[prev["trip_no"]] is not None or dev_of[cur["trip_no"]] is not None:
                continue
            gap_min = (cur["actual_arrive"] - prev["actual_arrive"]).total_seconds() / 60.0
            status, suggestion = classify_gap(gap_min, planned_headway_min, bunch_threshold, large_threshold)
            events.append(GapEvent(stop, prev["trip_no"], cur["trip_no"], round(gap_min, 2), planned_headway_min, status, suggestion))
    return events

def events_to_dicts(events: list[GapEvent | DeviationEvent]) -> list[dict]:
    return [asdict(e) for e in events]
