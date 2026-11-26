import json
from datetime import date
from pathlib import Path

from langchain_core.tools import tool


@tool
def lookup_window(station: str, day: str) -> dict:
    """按站点（如东站）与 ISO 服务日期 YYYY-MM-DD 查已发布自提班次。缺项表示未发布。"""
    try:
        date.fromisoformat(day)
    except ValueError:
        return {"status": "invalid_date", "expected": "YYYY-MM-DD", "station": station}
    rows = json.loads(Path(__file__).with_name("windows.json").read_text())
    for row in rows:
        if (row["station"], row["day"]) == (station, day):
            return {**row, "status": "published"}
    return {"station": station, "day": day, "status": "unpublished"}


TOOLS = [lookup_window]
