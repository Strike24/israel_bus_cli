import requests
from typing import List, Dict, Any, Optional
from bidi import get_display
from datetime import datetime, timedelta
try:  # Python 3.9+
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

NOMINATIM_USER_AGENT = "IsraelBusCLI/1.0 (+https://github.com/)"  # customize if publishing

def get_stops_near_location(lat: float, lon: float, radius: int = 250) -> List[Dict[str, Any]]:
    """Return list of nearby bus stops within radius (meters).

    API: /GetBusstopListByRadius/1/{lat}/{lon}/{radius}/he/false
    """
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
    """Return realtime lines for a given stop id."""
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
    """Filter lines by their 'Shilut' (line number) exact match."""
    if not number:
        return lines
    return [line for line in lines if str(line.get("Shilut")) == str(number)]

def search_address(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search for an address using the OpenStreetMap Nominatim API.

    Returns up to 'limit' result objects each containing address + lat/lon.
    """
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
    """Attempt to extract a human readable stop name from varying API keys."""
    name_keys = ["BusStopName", "Busstopnamehe", "Name", "name", "StopName"]
    for k in name_keys:
        v = stop.get(k)
        if v:
            return str(v)
    return str(stop.get("Makat") or stop.get("BusStopId") or "Unknown Stop")

def extract_stop_id(stop: Dict[str, Any]) -> Optional[str]:
    """Extract a usable stop id for follow-up calls."""
    id_keys = ["BusStopId", "Makat", "Id", "StopId", "StopCode"]
    for k in id_keys:
        v = stop.get(k)
        if v:
            return str(v)
    return None

def format_line(line: Dict[str, Any]) -> str:
    """Format a line dict into a readable string (line number + destination)."""
    number = line.get("Shilut") or line.get("Line", "?")
    dest = line.get("DestinationName") or line.get("DestinationQuarterName") or "?"
    operator = line.get("CompanyName") or line.get("CompanyHebrewName") or ""
    return f"{number} -> {get_display(dest)} {('('+get_display(operator)+')') if operator else ''}".strip()

def format_arrival(line: Dict[str, Any]) -> str:
    """Return human readable arrival info (mins, distance, scheduled/ETA time).

    If DtArrival is a placeholder (e.g. 0001-01-01..., 9999-..., or midnight with data),
    we compute an ETA from current time + MinutesToArrival instead of showing 00:00.
    """
    # Minutes to arrival (primary real-time indicator)
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

    # Distance (units unclear; treat as kilometers only if big, else meters)
    dist_raw = line.get("Distance")
    dist_part = ""
    try:
        if dist_raw is not None:
            dist_val = int(str(dist_raw).strip())
            if dist_val > 0:
                # Heuristic: values under 1000 likely meters, else km
                if dist_val < 1000:
                    dist_part = f"{dist_val}m"
                else:
                    dist_part = f"{dist_val/1000:.1f}km"
    except (ValueError, TypeError):
        pass

    ts = line.get("DtArrival")
    ts_part = ""
    placeholder = False
    if isinstance(ts, str):
        if ts.startswith("9999-") or ts.startswith("0001-"):
            placeholder = True
        # Many feeds provide 00:00:00 when only relative minutes known
        elif ts.endswith("00:00:00") and (mins is not None and mins > 0):
            placeholder = True
    # Determine timezone
    tz = None
    if ZoneInfo is not None:
        try:
            tz = ZoneInfo("Asia/Jerusalem")
        except Exception:  # pragma: no cover
            tz = None
    now = datetime.now(tz) if tz else datetime.now()

    if not placeholder and isinstance(ts, str):
        # Try to parse ISO timestamp
        try:
            iso = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso)
            if dt.tzinfo is None and tz:
                dt = dt.replace(tzinfo=tz)
            hhmm = dt.astimezone(tz).strftime("%H:%M") if tz else dt.strftime("%H:%M")
            ts_part = f"{hhmm} (sched)"
        except Exception:
            placeholder = True  # fallback to computed ETA

    if (placeholder or not ts_part) and mins is not None and mins >= 0:
        eta = now + timedelta(minutes=mins)
        ts_part = f"~{eta.strftime('%H:%M')}"

    parts = [p for p in [mins_part, ts_part] if p]
    return " | ".join(parts)