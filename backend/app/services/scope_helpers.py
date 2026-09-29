"""报告与时间轴组装时用的参与集辅助函数。

参与集只认检测引擎本次产出的事件：偏离班标记为 ``deviation``，
不得再被涂成串车 / 大间隔端点；任何入口都不得回退去吃未裁剪的原始集合。
"""
from __future__ import annotations

BUNCHING = "bunching"
LARGE_GAP = "large_gap"
DEVIATION = "deviation"
NORMAL = "normal"

def flatten_marks(marks: list[dict]) -> list[dict]:
    out: list[dict] = []
    for m in marks:
        item = dict(m)
        item.setdefault('visible', True)
        out.append(item)
    return out

def annotate_mark_statuses(marks: list[dict], stop_events: list[dict]) -> list[dict]:
    """按本次检测事件给某一站点的轴点打状态。

    偏离优先：班次一旦在偏离事件里，就只标 ``deviation``，
    串车 / 大间隔端点集里天然不含它（引擎已把偏离班移出配对集）。
    """
    deviated: dict[str, dict] = {}
    bunch_endpoints: set[str] = set()
    large_endpoints: set[str] = set()
    for e in stop_events:
        status = e.get("status")
        if status == DEVIATION:
            deviated[e["trip_no"]] = e
        elif status == BUNCHING:
            bunch_endpoints.add(e["earlier_trip"])
            bunch_endpoints.add(e["later_trip"])
        elif status == LARGE_GAP:
            large_endpoints.add(e["earlier_trip"])
            large_endpoints.add(e["later_trip"])
    out: list[dict] = []
    for m in marks:
        item = dict(m)
        trip_no = item["trip_no"]
        if trip_no in deviated:
            item["status"] = DEVIATION
            item["status_kind"] = deviated[trip_no].get("status_kind")
            item["deviation_min"] = deviated[trip_no].get("deviation_min")
        elif trip_no in bunch_endpoints:
            item["status"] = BUNCHING
        elif trip_no in large_endpoints:
            item["status"] = LARGE_GAP
        else:
            item["status"] = NORMAL
        out.append(item)
    return out
