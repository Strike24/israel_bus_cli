import requests
from typing import List, Dict, Any, Optional
from bidi import get_display

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
    """Return a human readable arrival info string for a realtime line object.

    Utilises MinutesToArrival, Distance, and DtArrival if present.
    """
    # Minutes to arrival
    mins_raw = line.get("MinutesToArrival")
    mins: Optional[int] = None
    try:
        # Some APIs may return string with spaces
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

    # Distance (kilometers from stop)
    dist_raw = line.get("Distance")
    dist_part = ""
    try:
        if dist_raw is not None:
            dist_val = int(str(dist_raw).strip())
            if dist_val > 0:
                dist_part = f"{dist_val} km"
    except (ValueError, TypeError):
        pass

    # Scheduled arrival timestamp
    ts = line.get("DtArrival")
    ts_part = ""
    if ts and isinstance(ts, str) and not ts.startswith("9999-"):
        # Expect ISO format; we just take HH:MM
        try:
            time_section = ts.split("T", 1)[1]
            hhmm = time_section[:5]
            ts_part = hhmm + " (scheduled)" #for example: 14:30 (scheduled)
        except Exception:
            ts_part = ""

    parts = [p for p in [mins_part, dist_part, ts_part] if p]
    return " | ".join(parts)