import requests
from typing import List, Dict, Any, Optional
try:
    from bidi import get_display  # type: ignore
except Exception:  # pragma: no cover
    def get_display(s: str) -> str:
        return s
from datetime import datetime, timedelta
try:  # Python 3.9+
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

NOMINATIM_USER_AGENT = "IsraelBusCLI/0.1.0 (+https://github.com/Strike24/israel_bus_cli)"

def get_stops_near_location(lat: float, lon: float, radius: int = 250) -> List[Dict[str, Any]]:
    url = f"https://bus.gov.il/WebApi/api/passengerinfo/GetBusstopListByRadius/1/{lat}/{lon}/{radius}/he/false"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data if isinstance(data, list) else []
        return []
    except requests.RequestException:
        return []

def get_lines_by_stop(stop_id: str) -> List[Dict[str, Any]]:
    url = f"https://bus.gov.il/WebApi/api/passengerinfo/GetRealtimeBusLineListByBustop/{stop_id}/he/false"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data if isinstance(data, list) else []
        return []
    except requests.RequestException:
        return []

def select_lines_by_number(lines: List[Dict[str, Any]], number: str) -> List[Dict[str, Any]]:
    if not number:
        return lines
    return [line for line in lines if str(line.get("Shilut")).strip() == str(number).strip()]

def search_address(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    if not query:
        return []
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": limit,
        "accept-language": "he,en"
    }
    headers = {"User-Agent": NOMINATIM_USER_AGENT}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data if isinstance(data, list) else []
        return []
    except requests.RequestException:
        return []

def extract_stop_name(stop: Dict[str, Any]) -> str:
    name_keys = ["BusStopName", "Busstopnamehe", "Name", "name", "StopName"]
    for k in name_keys:
        v = stop.get(k)
        if v:
            return str(v)
    return str(stop.get("Makat") or stop.get("BusStopId") or "Unknown Stop")

def extract_stop_id(stop: Dict[str, Any]) -> Optional[str]:
    id_keys = ["BusStopId", "Makat", "Id", "StopId", "StopCode"]
    for k in id_keys:
        v = stop.get(k)
        if v:
            return str(v)
    return None

def format_line(line: Dict[str, Any]) -> str:
    number = str(line.get("Shilut") or line.get("Line") or "?").strip()
    dest = line.get("DestinationName") or line.get("DestinationQuarterName") or line.get("Destination") or "?"
    description = line.get("Description") or dest
    operator = line.get("CompanyName") or line.get("CompanyHebrewName") or line.get("OperatorName") or ""
    base = f"{number} {description}".strip()
    if operator:
        base += f" ({operator})"
    return base

def format_arrival(line: Dict[str, Any]) -> str:
    mins_raw = line.get("MinutesToArrival")
    mins: Optional[int] = None
    try:
        if mins_raw is not None:
            mins = int(str(mins_raw).strip())
    except (ValueError, TypeError):
        mins = None

    if mins is None:
        mins_part = "? min"
    elif mins <= 0:
        mins_part = "Due"
    elif mins == 1:
        mins_part = "1 min"
    else:
        mins_part = f"{mins} min"

    dist_raw = line.get("Distance")
    dist_part = ""
    try:
        if dist_raw is not None:
            dist_val = int(str(dist_raw).strip())
            if dist_val >= 0:
                # Treat as number of stops (heuristic)
                dist_part = f"{dist_val} stops"
    except (ValueError, TypeError):
        pass

    ts = line.get("DtArrival")
    ts_part = ""
    placeholder = False
    if isinstance(ts, str):
        if ts.startswith("9999-") or ts.startswith("0001-"):
            placeholder = True
        elif ts.endswith("00:00:00") and (mins is not None and mins > 0):
            placeholder = True
    try:
        from zoneinfo import ZoneInfo  # type: ignore
        tz = ZoneInfo("Asia/Jerusalem")
    except Exception:
        tz = None
    now = datetime.now(tz) if tz else datetime.now()
    if not placeholder and isinstance(ts, str):
        try:
            iso = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso)
            if dt.tzinfo is None and tz:
                dt = dt.replace(tzinfo=tz)
            hhmm = dt.astimezone(tz).strftime("%H:%M") if tz else dt.strftime("%H:%M")
            ts_part = f"{hhmm} (sched)"
        except Exception:
            placeholder = True
    if (placeholder or not ts_part) and mins is not None and mins >= 0:
        eta = now + timedelta(minutes=mins)
        ts_part = f"~{eta.strftime('%H:%M')}"
    parts = [p for p in [mins_part, dist_part, ts_part] if p]
    return " | ".join(parts)

__all__ = [
    "get_stops_near_location",
    "get_lines_by_stop",
    "select_lines_by_number",
    "search_address",
    "extract_stop_name",
    "extract_stop_id",
    "format_line",
    "format_arrival",
]
