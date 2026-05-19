#!/usr/bin/env python3
"""
Generate an interactive HTML map of Dementia UK clinic locations.

Reads clinic data from dementia_uk_clinic_locations.csv, geocodes
each postcode using pgeocode (offline), and produces a self-contained
HTML file with a Leaflet.js map.

Usage:
    python generate_clinic_map.py
    python generate_clinic_map.py --input dementia_uk_clinic_locations.csv --output index.html
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import pgeocode


def load_clinics(filepath: str) -> list[dict]:
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File '{filepath}' not found.", file=sys.stderr)
        sys.exit(1)

    clinics = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clinics.append({
                "town": row.get("town", "").strip(),
                "street_address": row.get("street_address", "").strip(),
                "postcode": row.get("postcode", "").strip(),
                "clinic_dates": row.get("clinic_dates", "").strip(),
                "booking_url": row.get("booking_url", "").strip(),
            })
    return clinics


def geocode_clinics(clinics: list[dict]) -> list[dict]:
    nomi = pgeocode.Nominatim("gb")
    geocoded = []
    failed = []

    for clinic in clinics:
        pc = clinic["postcode"]
        if not pc:
            failed.append(clinic["town"])
            continue

        result = nomi.query_postal_code(pc)
        if result is None or math.isnan(result.latitude) or math.isnan(result.longitude):
            failed.append(f"{clinic['town']} ({pc})")
            continue

        clinic["lat"] = round(float(result.latitude), 5)
        clinic["lon"] = round(float(result.longitude), 5)
        geocoded.append(clinic)

    if failed:
        print(f"Warning: Could not geocode {len(failed)} location(s): {', '.join(failed[:10])}")

    return geocoded


def generate_html(clinics: list[dict]) -> str:
    clinics_json = json.dumps(clinics, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dementia UK – Admiral Nurse Clinic Locations</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
  #map {{ width: 100%; height: 100vh; }}

  .clinic-popup {{
    min-width: 220px;
    max-width: 300px;
    font-size: 14px;
    line-height: 1.5;
  }}
  .clinic-popup h3 {{
    margin: 0 0 6px 0;
    font-size: 16px;
    color: #1a3a5c;
  }}
  .clinic-popup .address {{
    color: #555;
    margin-bottom: 8px;
  }}
  .clinic-popup .dates {{
    background: #e8f4f8;
    border-left: 3px solid #2196F3;
    padding: 6px 10px;
    margin: 8px 0;
    border-radius: 0 4px 4px 0;
    font-weight: 500;
  }}
  .clinic-popup .dates-label {{
    font-size: 11px;
    text-transform: uppercase;
    color: #888;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
  }}
  .clinic-popup .book-btn {{
    display: inline-block;
    margin-top: 8px;
    padding: 8px 16px;
    background: #00838f;
    color: #fff;
    text-decoration: none;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 600;
    transition: background 0.2s;
  }}
  .clinic-popup .book-btn:hover {{
    background: #006064;
  }}

  .header-bar {{
    position: absolute;
    top: 12px;
    left: 60px;
    z-index: 1000;
    background: rgba(255,255,255,0.95);
    padding: 10px 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .header-bar h1 {{
    font-size: 16px;
    color: #1a3a5c;
    white-space: nowrap;
  }}
  .header-bar .count {{
    font-size: 13px;
    color: #666;
  }}

  /* --- Postcode lookup panel --- */
  .postcode-panel {{
    position: absolute;
    top: 12px;
    right: 12px;
    z-index: 1000;
    background: rgba(255,255,255,0.97);
    padding: 14px 16px;
    border-radius: 10px;
    box-shadow: 0 2px 14px rgba(0,0,0,0.22);
    width: 340px;
    max-height: calc(100vh - 40px);
    overflow-y: auto;
  }}
  .postcode-panel h2 {{
    font-size: 15px;
    color: #1a3a5c;
    margin-bottom: 8px;
  }}
  .postcode-form {{
    display: flex;
    gap: 6px;
    margin-bottom: 4px;
  }}
  .postcode-form input {{
    flex: 1;
    padding: 9px 12px;
    border: 1px solid #ccc;
    border-radius: 5px;
    font-size: 14px;
    outline: none;
    text-transform: uppercase;
  }}
  .postcode-form input:focus {{
    border-color: #00838f;
    box-shadow: 0 0 0 2px rgba(0,131,143,0.2);
  }}
  .postcode-form button {{
    padding: 9px 14px;
    background: #00838f;
    color: #fff;
    border: none;
    border-radius: 5px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.2s;
  }}
  .postcode-form button:hover {{
    background: #006064;
  }}
  .postcode-form button:disabled {{
    background: #999;
    cursor: not-allowed;
  }}
  .postcode-hint {{
    font-size: 11px;
    color: #999;
    margin-bottom: 6px;
  }}
  .postcode-error {{
    font-size: 12px;
    color: #d32f2f;
    margin-top: 4px;
    display: none;
  }}

  /* --- Nearest clinics results --- */
  .nearest-results {{
    display: none;
    margin-top: 12px;
    border-top: 1px solid #e0e0e0;
    padding-top: 10px;
  }}
  .nearest-results h3 {{
    font-size: 14px;
    color: #1a3a5c;
    margin-bottom: 8px;
  }}
  .nearest-card {{
    background: #f7fbfc;
    border: 1px solid #d4eaf0;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 8px;
    position: relative;
    cursor: pointer;
    transition: border-color 0.2s, box-shadow 0.2s;
  }}
  .nearest-card:hover {{
    border-color: #00838f;
    box-shadow: 0 1px 6px rgba(0,131,143,0.15);
  }}
  .nearest-card .rank {{
    position: absolute;
    top: 8px;
    right: 10px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #00838f;
    color: #fff;
    font-size: 12px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .nearest-card .nc-town {{
    font-weight: 600;
    font-size: 14px;
    color: #1a3a5c;
    margin-bottom: 3px;
    padding-right: 30px;
  }}
  .nearest-card .nc-address {{
    font-size: 12px;
    color: #666;
    margin-bottom: 4px;
  }}
  .nearest-card .nc-distance {{
    font-size: 12px;
    font-weight: 600;
    color: #00838f;
    margin-bottom: 4px;
  }}
  .nearest-card .nc-dates {{
    font-size: 12px;
    color: #333;
    background: #e8f4f8;
    padding: 4px 8px;
    border-radius: 3px;
    margin-bottom: 6px;
  }}
  .nearest-card .nc-book {{
    display: inline-block;
    padding: 5px 12px;
    background: #00838f;
    color: #fff;
    text-decoration: none;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    transition: background 0.2s;
  }}
  .nearest-card .nc-book:hover {{
    background: #006064;
  }}

  .clear-btn {{
    display: none;
    margin-top: 8px;
    padding: 6px 12px;
    background: #eee;
    color: #555;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.2s;
  }}
  .clear-btn:hover {{
    background: #ddd;
  }}

  .legend {{
    position: absolute;
    bottom: 30px;
    left: 12px;
    z-index: 1000;
    background: rgba(255,255,255,0.92);
    padding: 10px 14px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.15);
    font-size: 12px;
    color: #555;
  }}
</style>
</head>
<body>

<div class="header-bar">
  <h1>Admiral Nurse Clinic Locations</h1>
  <span class="count" id="clinicCount"></span>
</div>

<div class="postcode-panel">
  <h2>Find your nearest clinics</h2>
  <div class="postcode-form">
    <input type="text" id="postcodeInput" placeholder="Postcode or town, e.g. M1 1AE or Edinburgh" maxlength="60" />
    <button id="findBtn">Find</button>
  </div>
  <div class="postcode-hint">Enter a UK postcode or town name to find the 3 closest clinic locations</div>
  <div class="postcode-error" id="postcodeError"></div>

  <div class="nearest-results" id="nearestResults">
    <h3>Closest clinics to <span id="originLabel"></span></h3>
    <div id="nearestCards"></div>
  </div>

  <button class="clear-btn" id="clearBtn">Clear &amp; reset map</button>
</div>

<div id="map"></div>

<div class="legend">
  Enter a postcode or town name above to find your nearest clinic, or click markers to explore.
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script>
const clinics = {clinics_json};

document.getElementById('clinicCount').textContent = clinics.length + ' clinics';

// --- Haversine distance (miles) ---
function haversine(lat1, lon1, lat2, lon2) {{
  const R = 3958.8; // Earth radius in miles
  const toRad = d => d * Math.PI / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon/2)**2;
  return R * 2 * Math.asin(Math.sqrt(a));
}}

// --- Initialise map centred on the UK ---
const map = L.map('map', {{
  center: [54.5, -2.5],
  zoom: 6,
  zoomControl: true,
}});

L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19,
}}).addTo(map);

// --- Clinic marker icon ---
const clinicIcon = L.divIcon({{
  className: 'custom-marker',
  html: `<svg width="28" height="40" viewBox="0 0 28 40" xmlns="http://www.w3.org/2000/svg">
    <path d="M14 0C6.27 0 0 6.27 0 14c0 10.5 14 26 14 26s14-15.5 14-26C28 6.27 21.73 0 14 0z" fill="#00838f" stroke="#fff" stroke-width="1.5"/>
    <circle cx="14" cy="13" r="6" fill="#fff"/>
    <text x="14" y="16.5" text-anchor="middle" font-size="11" font-weight="bold" fill="#00838f">+</text>
  </svg>`,
  iconSize: [28, 40],
  iconAnchor: [14, 40],
  popupAnchor: [0, -36],
}});

// --- User location icon (different colour) ---
const userIcon = L.divIcon({{
  className: 'custom-marker',
  html: `<svg width="32" height="44" viewBox="0 0 32 44" xmlns="http://www.w3.org/2000/svg">
    <path d="M16 0C7.16 0 0 7.16 0 16c0 12 16 28 16 28s16-16 16-28C32 7.16 24.84 0 16 0z" fill="#d32f2f" stroke="#fff" stroke-width="2"/>
    <circle cx="16" cy="15" r="7" fill="#fff"/>
    <circle cx="16" cy="15" r="3.5" fill="#d32f2f"/>
  </svg>`,
  iconSize: [32, 44],
  iconAnchor: [16, 44],
  popupAnchor: [0, -40],
}});

// --- Highlighted clinic icon (for the closest 3) ---
const highlightIcon = L.divIcon({{
  className: 'custom-marker',
  html: `<svg width="32" height="44" viewBox="0 0 32 44" xmlns="http://www.w3.org/2000/svg">
    <path d="M16 0C7.16 0 0 7.16 0 16c0 12 16 28 16 28s16-16 16-28C32 7.16 24.84 0 16 0z" fill="#ff6f00" stroke="#fff" stroke-width="2"/>
    <circle cx="16" cy="15" r="7" fill="#fff"/>
    <text x="16" y="19" text-anchor="middle" font-size="12" font-weight="bold" fill="#ff6f00">+</text>
  </svg>`,
  iconSize: [32, 44],
  iconAnchor: [16, 44],
  popupAnchor: [0, -40],
}});

// --- Marker cluster group ---
const markers = L.markerClusterGroup({{
  maxClusterRadius: 45,
  spiderfyOnMaxZoom: true,
  showCoverageOnHover: false,
  zoomToBoundsOnClick: true,
}});

// Build markers for every clinic
const markerMap = {{}};
clinics.forEach((c, idx) => {{
  const popupHtml = `
    <div class="clinic-popup">
      <h3>${{c.town}}</h3>
      <div class="address">
        ${{c.street_address ? c.street_address + '<br>' : ''}}
        ${{c.postcode}}
      </div>
      <div class="dates">
        <div class="dates-label">Next appointments</div>
        ${{c.clinic_dates}}
      </div>
      ${{c.booking_url
        ? `<a class="book-btn" href="${{c.booking_url}}" target="_blank" rel="noopener">Book appointment &rarr;</a>`
        : ''
      }}
    </div>
  `;
  const marker = L.marker([c.lat, c.lon], {{ icon: clinicIcon }})
    .bindPopup(popupHtml, {{ maxWidth: 300 }});
  markers.addLayer(marker);
  markerMap[idx] = marker;
}});

map.addLayer(markers);

// =================================================================
//  Postcode lookup – geocode via postcodes.io and find nearest 3
// =================================================================
let userMarker = null;
let standaloneMarkers = [];
let removedFromCluster = [];
let connectLines = [];

const postcodeInput = document.getElementById('postcodeInput');
const findBtn = document.getElementById('findBtn');
const errorEl = document.getElementById('postcodeError');
const nearestResults = document.getElementById('nearestResults');
const nearestCards = document.getElementById('nearestCards');
const originLabel = document.getElementById('originLabel');
const clearBtn = document.getElementById('clearBtn');

function clearProximityResults() {{
  if (userMarker) {{ map.removeLayer(userMarker); userMarker = null; }}
  standaloneMarkers.forEach(m => map.removeLayer(m));
  standaloneMarkers = [];
  // Restore removed markers back into the cluster group
  removedFromCluster.forEach(m => markers.addLayer(m));
  removedFromCluster = [];
  connectLines.forEach(l => map.removeLayer(l));
  connectLines = [];
  nearestResults.style.display = 'none';
  nearestCards.innerHTML = '';
  clearBtn.style.display = 'none';
  errorEl.style.display = 'none';
  // Re-add cluster layer if removed
  if (!map.hasLayer(markers)) map.addLayer(markers);
}}

async function geocodeLocation(input) {{
  const trimmed = input.trim();
  if (!trimmed) return null;

  // Try postcodes.io first (works for valid UK postcodes)
  try {{
    const pcClean = encodeURIComponent(trimmed);
    const pcResp = await fetch(`https://api.postcodes.io/postcodes/${{pcClean}}`);
    if (pcResp.ok) {{
      const pcData = await pcResp.json();
      if (pcData.status === 200 && pcData.result) {{
        return {{
          label: pcData.result.postcode,
          lat: pcData.result.latitude,
          lon: pcData.result.longitude,
        }};
      }}
    }}
  }} catch (_) {{ /* fall through to place name lookup */ }}

  // Fall back to OpenStreetMap Nominatim for town / city / place names
  try {{
    const query = encodeURIComponent(trimmed + ', United Kingdom');
    const nomResp = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${{query}}&format=json&limit=1&countrycodes=gb`,
      {{ headers: {{ 'Accept': 'application/json' }} }}
    );
    if (nomResp.ok) {{
      const results = await nomResp.json();
      if (results.length > 0) {{
        return {{
          label: results[0].display_name.split(',')[0],
          lat: parseFloat(results[0].lat),
          lon: parseFloat(results[0].lon),
        }};
      }}
    }}
  }} catch (_) {{ /* no result */ }}

  return null;
}}

function findNearestClinics(lat, lon, n) {{
  return clinics
    .map((c, idx) => ({{ ...c, idx, distance: haversine(lat, lon, c.lat, c.lon) }}))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, n);
}}

async function handlePostcodeLookup() {{
  const pc = postcodeInput.value.trim();
  if (!pc) return;

  clearProximityResults();
  findBtn.disabled = true;
  findBtn.textContent = '...';
  errorEl.style.display = 'none';

  try {{
    const geo = await geocodeLocation(pc);
    if (!geo) {{
      errorEl.textContent = `Could not find "${{pc}}". Please check the postcode or place name and try again.`;
      errorEl.style.display = 'block';
      return;
    }}

    // Drop user pin
    userMarker = L.marker([geo.lat, geo.lon], {{ icon: userIcon }})
      .bindPopup(`<div class="clinic-popup"><h3>Your location</h3><div class="address">${{geo.label}}</div></div>`)
      .addTo(map);

    // Find 3 nearest clinics
    const nearest = findNearestClinics(geo.lat, geo.lon, 3);

    // Pull nearest clinic markers out of the cluster and show as standalone orange markers
    nearest.forEach((c, i) => {{
      // Remove the original marker from the cluster group
      const origMarker = markerMap[c.idx];
      if (origMarker) {{
        markers.removeLayer(origMarker);
        removedFromCluster.push(origMarker);
      }}

      const popupHtml = `
        <div class="clinic-popup">
          <h3>#${{i+1}} Nearest — ${{c.town}}</h3>
          <div class="address">
            ${{c.street_address ? c.street_address + '<br>' : ''}}
            ${{c.postcode}}
          </div>
          <div class="nc-distance" style="font-weight:600;color:#00838f;margin:4px 0">${{c.distance.toFixed(1)}} miles away</div>
          <div class="dates">
            <div class="dates-label">Next appointments</div>
            ${{c.clinic_dates}}
          </div>
          ${{c.booking_url
            ? `<a class="book-btn" href="${{c.booking_url}}" target="_blank" rel="noopener">Book appointment &rarr;</a>`
            : ''
          }}
        </div>
      `;
      const sm = L.marker([c.lat, c.lon], {{ icon: highlightIcon }})
        .bindPopup(popupHtml, {{ maxWidth: 300 }})
        .addTo(map);
      standaloneMarkers.push(sm);

      // Draw a line from user to clinic
      const line = L.polyline([[geo.lat, geo.lon], [c.lat, c.lon]], {{
        color: '#ff6f00',
        weight: 2,
        opacity: 0.5,
        dashArray: '6, 8',
      }}).addTo(map);
      connectLines.push(line);
    }});

    // Zoom to show user + nearest clinics
    const bounds = L.latLngBounds([[geo.lat, geo.lon]]);
    nearest.forEach(c => bounds.extend([c.lat, c.lon]));
    map.fitBounds(bounds.pad(0.3));

    // Build the nearest-clinics cards in the panel
    originLabel.textContent = geo.label;
    nearestCards.innerHTML = '';
    nearest.forEach((c, i) => {{
      const card = document.createElement('div');
      card.className = 'nearest-card';
      card.innerHTML = `
        <div class="rank">${{i + 1}}</div>
        <div class="nc-town">${{c.town}}</div>
        <div class="nc-address">${{c.street_address ? c.street_address + ', ' : ''}}${{c.postcode}}</div>
        <div class="nc-distance">${{c.distance.toFixed(1)}} miles away</div>
        <div class="nc-dates">📅 ${{c.clinic_dates}}</div>
        ${{c.booking_url
          ? `<a class="nc-book" href="${{c.booking_url}}" target="_blank" rel="noopener">Book appointment &rarr;</a>`
          : ''
        }}
      `;
      card.addEventListener('click', (e) => {{
        if (e.target.tagName === 'A') return; // let link clicks through
        map.setView([c.lat, c.lon], 14);
        standaloneMarkers[i].openPopup();
      }});
      nearestCards.appendChild(card);
    }});

    nearestResults.style.display = 'block';
    clearBtn.style.display = 'inline-block';

  }} catch (err) {{
    errorEl.textContent = 'Network error – please check your connection and try again.';
    errorEl.style.display = 'block';
    console.error(err);
  }} finally {{
    findBtn.disabled = false;
    findBtn.textContent = 'Find';
  }}
}}

findBtn.addEventListener('click', handlePostcodeLookup);
postcodeInput.addEventListener('keydown', (e) => {{
  if (e.key === 'Enter') handlePostcodeLookup();
}});
clearBtn.addEventListener('click', () => {{
  clearProximityResults();
  postcodeInput.value = '';
  map.setView([54.5, -2.5], 6);
}});


</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Generate an interactive clinic location map.")
    parser.add_argument(
        "--input", "-i",
        default=str(Path(__file__).parent / "data" / "dementia_uk_clinic_locations.csv"),
        help="Path to the clinic CSV file.",
    )
    parser.add_argument(
        "--output", "-o",
        default=str(Path(__file__).parent / "output" / "index.html"),
        help="Path for the output HTML file.",
    )
    args = parser.parse_args()

    print("Loading clinic data ...")
    clinics = load_clinics(args.input)
    print(f"Loaded {len(clinics)} clinics")

    print("Geocoding postcodes (offline) ...")
    geocoded = geocode_clinics(clinics)
    print(f"Geocoded {len(geocoded)} / {len(clinics)} clinics")

    print("Generating map ...")
    html = generate_html(geocoded)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"\nMap written to: {output_path}")
    print(f"Open in your browser: file://{output_path.resolve()}")


if __name__ == "__main__":
    main()
