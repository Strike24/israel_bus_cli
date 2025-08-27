"""CLI entry point (interactive + flag modes)."""
from __future__ import annotations
import argparse, sys, json
from typing import Optional, List, Dict, Any

try:
    from bidi import get_display  # type: ignore
except Exception:  # pragma: no cover
    def get_display(s: str) -> str:  # fallback noop
        return s

from .bus_info import (
    search_address,
    get_stops_near_location,
    get_lines_by_stop,
    select_lines_by_number,
    extract_stop_name,
    extract_stop_id,
    format_line,
    format_arrival,
)
from . import __version__

DEFAULT_RADIUS = 300

def parse_args():
    p = argparse.ArgumentParser(prog="israel-bus", description="Israel bus CLI (unofficial)")
    p.add_argument("--address")
    p.add_argument("--address-index", type=int, default=0)
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--radius", type=int, default=DEFAULT_RADIUS)
    p.add_argument("--stop-id")
    p.add_argument("--first-stop", action="store_true")
    p.add_argument("--line")
    p.add_argument("--list-stops", action="store_true")
    p.add_argument("--limit-stops", type=int, default=0)
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-bidi", action="store_true")
    p.add_argument("--version", action="store_true", help="Print version and exit")
    return p.parse_args()

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

def list_nearby_stops(lat: float, lon: float, radius: int, *, limit: int = 0, disable_bidi: bool = False, json_mode: bool = False):
    stops = get_stops_near_location(lat, lon, radius)
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
        data = [{"index": i, "id": extract_stop_id(s), "name": extract_stop_name(s), "distance": s.get("Distance") or s.get("DistanceFromStart")} for i, s in enumerate(stops)]
        print(json.dumps({"count": len(data), "radius": radius, "stops": data}, ensure_ascii=False))
        return stops
    if not stops:
        print("No stops found.")
        return []
    print(f"Found {len(stops)} stops within {radius}m:\n")
    for idx, s in enumerate(stops):
        name = extract_stop_name(s)
        stop_id = extract_stop_id(s) or "?"
        distance = s.get("Distance") or s.get("DistanceFromStart") or ""
        dist_str = f" - {distance}" if distance not in (None, "") else ""
        name_disp = name if disable_bidi else get_display(name)
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
        payload = [{"line": format_line(l), "arrival": format_arrival(l), "raw": l} for l in lines]
        print(json.dumps({"stop_id": stop_id, "lines": payload}, ensure_ascii=False))
        return
    print(f"Lines at stop {stop_id}:")
    for l in lines:
        base = format_line(l)
        arrival = format_arrival(l)
        text = f"{base} [{arrival}]"
        print(" -", text if disable_bidi else get_display(text))

def interactive_main():
    lat, lon = prompt_address()
    while True:
        print("\nMenu: 1) Nearby stops 2) Change address 3) Quit")
        choice = input("> ").strip()
        if choice == "1":
            radius = DEFAULT_RADIUS
            try:
                radius_in = input(f"Radius meters (default {DEFAULT_RADIUS}): ").strip()
                radius = int(radius_in) if radius_in else DEFAULT_RADIUS
            except ValueError:
                pass
            stops = list_nearby_stops(lat, lon, radius)
            if not stops:
                continue
            sel = input("Pick stop # to view lines (blank to return): ").strip()
            if sel.isdigit():
                idx = int(sel)
                if 0 <= idx < len(stops):
                    show_lines_for_stop(stops[idx])
        elif choice == "2":
            lat, lon = prompt_address()
        elif choice in {"3", "q", "quit", "exit"}:
            break
        else:
            print("Unknown option.")

def main():
    args = parse_args()
    if args.version:
        print(__version__)
        return
    non_interactive = any([
        args.address, args.lat is not None, args.lon is not None, args.stop_id, args.first_stop, args.list_stops, args.line, args.json
    ])
    if not non_interactive:
        interactive_main()
        return
    disable_bidi = args.no_bidi
    lat: Optional[float] = None
    lon: Optional[float] = None
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
    stop_id = args.stop_id or (extract_stop_id(chosen_stop) if chosen_stop else None)
    if stop_id:
        show_lines_for_stop(chosen_stop, stop_id=stop_id, line_filter=args.line, json_mode=args.json, disable_bidi=disable_bidi)
    elif args.line:
        print("Line filter specified but no stop id context", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":  # pragma: no cover
    main()
