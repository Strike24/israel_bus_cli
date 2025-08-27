"""Israel Bus CLI

Interactive or flag-based retrieval of:
1. Nearby stops by address or coordinates
2. Realtime lines (with arrival info) for a stop

Examples:
    python main.py --address "יהודה הנשיא 36 תל אביב" --list-stops --radius 400
    python main.py --address "יהודה הנשיא 36 תל אביב" --first-stop --line 12
    python main.py --stop-id 26629 --line 12
    python main.py --address "יהודה הנשיא 36 תל אביב" --json --first-stop

If no flags are provided the tool enters interactive mode.
"""

from bidi import get_display
import argparse
import sys
import json
from typing import Optional, List, Dict, Any
from bus_info import (
    search_address,
    get_stops_near_location,
    get_lines_by_stop,
    select_lines_by_number,
    extract_stop_name,
    extract_stop_id,
    format_line,
    format_arrival,
)

DEFAULT_RADIUS = 300  # meters

def parse_args():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--address", help="Free text address to geocode (implies non-interactive)")
    parser.add_argument("--address-index", type=int, default=0, help="Index of address result to use (default 0)")
    parser.add_argument("--lat", type=float, help="Latitude (skip geocoding if both lat & lon provided)")
    parser.add_argument("--lon", type=float, help="Longitude (skip geocoding if both lat & lon provided)")
    parser.add_argument("--radius", type=int, default=DEFAULT_RADIUS, help="Radius in meters for nearby stops")
    parser.add_argument("--stop-id", help="Fetch realtime lines for this stop id directly")
    parser.add_argument("--first-stop", action="store_true", help="Automatically select nearest stop (after address lookup)")
    parser.add_argument("--line", help="Filter line number")
    parser.add_argument("--list-stops", action="store_true", help="List stops and exit (unless --first-stop also used)")
    parser.add_argument("--limit-stops", type=int, default=0, help="Limit number of stops displayed (0 = all)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of human readable text")
    parser.add_argument("--no-bidi", action="store_true", help="Disable bidi rendering (raw text)")
    return parser.parse_args()

def prompt_address() -> tuple[float, float]:
    query = input("Search address (or blank to quit): ").strip()
    if not query:
        raise SystemExit
    results = search_address(query)
    if not results:
        print("No results. Try again.")
        return prompt_address()
    for i, place in enumerate(results):
        address = place.get("address", {})
        road = address.get("road", "")
        house_number = address.get("house_number", "")
        city = address.get("city") or address.get("town") or ""
        label = " ".join(x for x in [road, house_number] if x).strip()
        if city:
            label = f"{label}, {city}" if label else city
        print(f"[{i}] {get_display(label)}")
    while True:
        try:
            choice = int(input("Pick address #: "))
            if 0 <= choice < len(results):
                sel = results[choice]
                return float(sel["lat"]), float(sel["lon"])
        except (ValueError, KeyError):
            pass
        print("Invalid choice.")

def list_nearby_stops(lat: float, lon: float, radius: int = DEFAULT_RADIUS, *, limit: int = 0, disable_bidi: bool = False, json_mode: bool = False):
    stops = get_stops_near_location(lat, lon, radius)
    # Sort by numeric distance if present
    def dist_val(s):
        d = s.get("Distance") or s.get("DistanceFromStart")
        try:
            return int(str(d).strip())
        except Exception:
            return 10**9
    stops.sort(key=dist_val)
    if limit > 0:
        stops = stops[:limit]
    if json_mode:
        out = []
        for idx, s in enumerate(stops):
            out.append({
                "index": idx,
                "id": extract_stop_id(s),
                "name": extract_stop_name(s),
                "distance": s.get("Distance") or s.get("DistanceFromStart")
            })
        print(json.dumps({"count": len(out), "radius": radius, "stops": out}, ensure_ascii=False))
        return stops
    if not stops:
        print("No stops found.")
        return []
    print(f"Found {len(stops)} stops within {radius}m:\n")
    for idx, stop in enumerate(stops):
        stop_name = extract_stop_name(stop)
        stop_id = extract_stop_id(stop) or "?"
        distance = stop.get("Distance") or stop.get("DistanceFromStart") or ""
        dist_str = f" - {distance}m" if distance not in (None, "") else ""
        name_disp = stop_name if disable_bidi else get_display(stop_name)
        print(f"[{idx}] {name_disp} (ID: {stop_id}){dist_str}")
    return stops

def show_lines_for_stop(stop: Dict[str, Any] | None = None, *, stop_id: Optional[str] = None, line_filter: Optional[str] = None, json_mode: bool = False, disable_bidi: bool = False):
    if not stop_id and stop:
        stop_id = extract_stop_id(stop)
    if not stop_id:
        print("Can't determine stop id.")
        return
    lines = get_lines_by_stop(stop_id)
    if line_filter:
        lines = select_lines_by_number(lines, line_filter)
    if not lines:
        if json_mode:
            print(json.dumps({"stop_id": stop_id, "lines": []}, ensure_ascii=False))
        else:
            print("No realtime lines.")
        return
    if json_mode:
        payload = []
        for line in lines:
            payload.append({
                "line": format_line(line),
                "arrival": format_arrival(line),
                "raw": line,
            })
        print(json.dumps({"stop_id": stop_id, "lines": payload}, ensure_ascii=False))
        return
    print(f"Lines at stop {stop_id}:")
    for line in lines:
        base = format_line(line)
        arrival = format_arrival(line)
        print(" -", f"{base} [{arrival}]")

def interactive_main():
    lat, lon = prompt_address()
    while True:
        print("\nMenu: 1) Nearby stops 2) Change address 3) Quit")
        choice = input("> ").strip()
        if choice == "1":
            try:
                radius_in = input(f"Radius meters (default {DEFAULT_RADIUS}): ").strip()
                radius_val = int(radius_in) if radius_in else DEFAULT_RADIUS
            except ValueError:
                radius_val = DEFAULT_RADIUS
            stops = list_nearby_stops(lat, lon, radius_val)
            if not stops:
                continue
            sel = input("Pick stop # to view lines (blank to return): ").strip()
            if sel.isdigit():
                idx = int(sel)
                if 0 <= idx < len(stops):
                    show_lines_for_stop(stops[idx])
        elif choice == "2":
            lat, lon = prompt_address()
        elif choice == "3" or choice.lower() in {"q", "quit", "exit"}:
            break
        else:
            print("Unknown option.")

def main():
    args = parse_args()
    # If any non-interactive flag provided we go non-interactive
    non_interactive = any([
        args.address, args.lat is not None, args.lon is not None, args.stop_id, args.first_stop, args.list_stops, args.line, args.json
    ])
    if not non_interactive:
        interactive_main()
        return
    disable_bidi = args.no_bidi
    lat: Optional[float] = None
    lon: Optional[float] = None
    # Coordinates override address search
    if args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
    elif args.address:
        addr_results = search_address(args.address)
        if not addr_results:
            print("No address results", file=sys.stderr)
            sys.exit(2)
        if args.address_index < 0 or args.address_index >= len(addr_results):
            print("address-index out of range", file=sys.stderr)
            sys.exit(2)
        sel = addr_results[args.address_index]
        lat, lon = float(sel["lat"]), float(sel["lon"])
    # If we still don't have coordinates and need them -> error
    if (args.list_stops or args.first_stop) and (lat is None or lon is None):
        print("Need --address or --lat/--lon for stop lookup", file=sys.stderr)
        sys.exit(2)
    chosen_stop: Optional[Dict[str, Any]] = None
    stops: List[Dict[str, Any]] = []
    if lat is not None and lon is not None and (args.list_stops or args.first_stop):
        stops = list_nearby_stops(lat, lon, args.radius, limit=args.limit_stops, disable_bidi=disable_bidi, json_mode=args.json and not args.first_stop)
        if args.first_stop and stops:
            chosen_stop = stops[0]
            if not args.json:
                name_disp = extract_stop_name(chosen_stop)
                if not disable_bidi:
                    name_disp = get_display(name_disp)
                print(f"Selected nearest stop: {name_disp} (ID: {extract_stop_id(chosen_stop)})")
        if args.list_stops and not args.first_stop:
            return
    # Direct stop id override
    stop_id = args.stop_id or (extract_stop_id(chosen_stop) if chosen_stop else None)
    if stop_id:
        show_lines_for_stop(chosen_stop, stop_id=stop_id, line_filter=args.line, json_mode=args.json, disable_bidi=disable_bidi)
    elif args.line:
        print("Line filter specified but no stop id context", file=sys.stderr)
        sys.exit(2)
    # Done

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye")