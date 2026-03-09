# dementia-uk

A repository for code related to Dementia UK.

---

## nbs-clinic-map

Scripts to scrape Dementia UK's Admiral Nurse clinic listings and produce an interactive map.

### Scripts

#### `scrape_clinics.py`

Fetches the [Dementia UK Nationwide clinic page](https://www.dementiauk.org/information-and-support/how-we-can-support-you/admiral-nurse-clinics/nationwide/) and extracts clinic details using regex parsing. For each clinic it captures:

- Town and street address
- UK postcode (extracted separately from the full address)
- Upcoming clinic dates
- Booking URL (SimplyBook or Outlook)

Output is written to `nbs-clinic-map/dementia_uk_clinic_locations.csv`. A preview of the first 15 results is printed to the terminal.

**Usage:**
```bash
python nbs-clinic-map/scrape_clinics.py
```

---

#### `generate_clinic_map.py`

Reads `dementia_uk_clinic_locations.csv` (produced by `scrape_clinics.py`) and generates a self-contained interactive HTML map file.

At generation time, [`pgeocode`](https://pgeocode.readthedocs.io/) converts each UK postcode to a latitude/longitude coordinate using an offline GB dataset (no external API call). Those coordinates are embedded as a JSON array directly into the HTML file.

In the browser, **Leaflet.js** uses those coordinates for all map rendering and interaction — placing markers, clustering, calculating haversine distances for the nearest-clinic search, and opening popups.

Map features:
- **Leaflet.js** base map (OpenStreetMap tiles) centred on the UK
- **Marker clustering** — nearby pins are grouped and expand on zoom
- **Clinic popups** — clicking a marker shows the address, upcoming dates, and a "Book now" button
- **"Find nearest clinics" panel** — enter a UK postcode or town name to locate the 3 closest clinics by straight-line distance (miles), with cards showing address, dates, distance, and a booking link

**Usage:**
```bash
# Default: reads dementia_uk_clinic_locations.csv, writes clinic_map.html
python nbs-clinic-map/generate_clinic_map.py

# Custom input/output paths
python nbs-clinic-map/generate_clinic_map.py --input dementia_uk_clinic_locations.csv --output clinic_map.html
```

**Dependencies:**
```bash
pip install pgeocode
```

### Typical workflow

```bash
# 1. Scrape latest clinic data
python nbs-clinic-map/scrape_clinics.py

# 2. Generate the interactive map
python nbs-clinic-map/generate_clinic_map.py

# 3. Open the map
open nbs-clinic-map/clinic_map.html
```
