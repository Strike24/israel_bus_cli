"""Main entry point for the Israel Bus CLI application.

Simple flow:
1. Ask user for an address, pick result.
2. Show nearby stops (with index & id) within a radius.
3. Let user pick a stop to view realtime lines.
4. Optionally filter lines by number.
"""

from bidi import get_display
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

def list_nearby_stops(lat: float, lon: float, radius: int = DEFAULT_RADIUS):
    stops = get_stops_near_location(lat, lon, radius)
    if not stops:
        print("No stops found.")
        return []
    print(f"Found {len(stops)} stops within {radius}m:\n")
    for idx, stop in enumerate(stops):
        stop_name = extract_stop_name(stop)
        stop_id = extract_stop_id(stop) or "?"
        print(f"[{idx}] {get_display(stop_name)} (ID: {stop_id})")
    return stops

def show_lines_for_stop(stop):
    stop_id = extract_stop_id(stop)
    if not stop_id:
        print("Can't determine stop id.")
        return
    lines = get_lines_by_stop(stop_id)
    if not lines:
        print("No realtime lines.")
        return
    number_filter = input("Filter by line number (Enter for all): ").strip()
    filtered = lines
    if number_filter:
        filtered = select_lines_by_number(lines, number_filter)
    if not filtered:
        print("No lines match filter.")
        return
    print(f"Lines at stop {stop_id}:")
    for line in filtered:
        base = format_line(line)
        arrival = format_arrival(line)
        print(" -", f"{base} [{arrival}]")

def main():
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

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye")