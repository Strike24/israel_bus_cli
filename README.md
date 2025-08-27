# Israel Bus CLI 🚌🚍
CLI & Python API for searching Israeli bus stops and realtime line arrival info (unofficial, uses public Web endpoints).

## Install

```
pip install israel-bus-cli
```

## Quick usage (CLI)

Search address and list nearby stops (JSON):
```
israel-bus --address "דיזינגוף 220 תל אביב" --list-stops --json
```

Get lines for the first (nearest) stop, filter line 12:
```
israel-bus --address "דיזינגוף 220 תל אביב" --first-stop --line 12
```

Direct by stop id:
```
israel-bus --stop-id 26629 --line 12 --json
```

Interactive mode (no flags):
```
israel-bus
```

## Python API
```python
from israel_bus_cli import search_address, get_stops_near_location, get_lines_by_stop

addr = search_address("דיזינגוף 220 תל אביב")[0]
lat, lon = float(addr['lat']), float(addr['lon'])
stops = get_stops_near_location(lat, lon)
lines = get_lines_by_stop('26629')
```

## Disclaimer
Not affiliated with official transit authorities. API structure may change.

## License
MIT


## Development


