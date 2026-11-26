# Galicia Food Map

An interactive geospatial explorer of selected fast-food locations in Galicia, Spain, built using Python, JavaScript, Leaflet and OpenStreetMap data.

## Features

- Street, satellite and topographic basemaps (with topographic fallback).
- Individual and clustered restaurant markers, with category-specific SVG icons.
- Location counts for Burger King, McDonald's and kebab shops.
- Popups with available cuisine information and a reference marker for Lalín.
- Reproducible data import from Overpass JSON or GeoJSON, with deduplication by source identifier.

## Quick start

Requires Python 3.9+ for the local server and data preparation; no third-party Python packages are required.

```bash
python -m http.server 8000
```

Open http://localhost:8000 in a browser. Internet access is required for map tiles and CDN libraries; restaurant records are bundled locally.

## Data pipeline

```text
OpenStreetMap → Overpass queries → JSON / GeoJSON → Python normalization → local JS dataset → Leaflet map
```

Refresh from Overpass (replaces the snapshot):

```bash
python scripts/prepare_data.py
```

Or import bundled exports (merges by identifier with existing records):

```bash
python scripts/prepare_data.py --importar data/raw/restaurantes.geojson data/raw/kebabs.geojson
```

## Project structure

```text
index.html         Web entry point
assets/css/        Interface styles
assets/js/         Map logic
assets/icons/      SVG markers
data/              Bundled dataset and raw exports
queries/           Overpass queries
scripts/           Python data preparation
tests/             Offline unit tests
```

Run tests with `python -m unittest discover -s tests`.

## Data and limitations

Data: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), under the Open Database License (ODbL). The bundled snapshot comes from the original project exports; the exact extraction timestamp is not documented. Counts reflect matching OSM records, not an exhaustive census of restaurants or guaranteed distinct physical businesses. Non-point geometries use an approximate vertex-average location when imported from GeoJSON. Map tiles are supplied by Esri and OpenTopoMap; provider terms apply. The Lalín photograph is linked rather than redistributed.

## Deployment

After obtaining permission to publish, enable GitHub Pages from Settings → Pages → Deploy from a branch → main → / (root). No build step is needed.

## Authors

David Murado and Jorge Crespo. Originally developed as a university assignment and adapted for a portfolio presentation. Confirm both authors' consent and any course-material permissions before public release. No software license is asserted until the rights holders agree on one.
