# Galicia Food Map
[🌍 Launch interactive map](https://davidmurado-hub.github.io/galicia-food-map/)


Interactive map of Burger King, McDonald's and kebab locations in Galicia, Spain. Built with Leaflet and OpenStreetMap data processed in Python.

## Overview

The application displays restaurant locations with category-specific markers, marker clustering, location counts and selectable street, satellite and topographic basemaps.

Geospatial data is retrieved through the Overpass API, normalized in Python and stored as a local JavaScript dataset. The application runs entirely in the browser and requires no backend.

## Getting started

Requires Python 3.9 or later. No external Python packages are needed.

```bash
python -m http.server 8000
```

Open [localhost:8000](http://localhost:8000). An internet connection is required for map tiles and Leaflet libraries.

## Data processing

Update the dataset from OpenStreetMap:

```bash
python scripts/prepare_data.py
```

Alternatively, import the bundled GeoJSON files:

```bash
python scripts/prepare_data.py --importar data/raw/restaurantes.geojson data/raw/kebabs.geojson
```

Run the unit tests:

```bash
python -m unittest discover -s tests
```

## Data sources

Restaurant data is provided by [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) under the Open Database License (ODbL). Map tiles are provided by Esri and OpenTopoMap, subject to their respective terms.

The bundled dataset is a snapshot with an undocumented extraction date and does not represent an exhaustive inventory of restaurants. Locations derived from non-point geometries are approximate.

## Authors

David Murado and Jorge Crespo.

Originally developed as a university project. No software license has been assigned.

