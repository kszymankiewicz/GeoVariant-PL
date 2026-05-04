# GeoVariant-PL

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)

**A reproducible geospatial pipeline for geocoding and visualizing categorical variant data from administrative records in Poland.**

GeoVariant-PL takes tabular occurrence records with Polish administrative location data (voivodeship, county, commune, locality), resolves them to geographic coordinates via the OpenStreetMap Nominatim API, and generates both interactive and publication-ready static maps with color-coded variant categories.

The pipeline was originally developed for the spatial analysis of epidemiological data on wild boar (*Sus scrofa*) in Poland, including the distribution of viral genetic variants across administrative units. It is fully generic and can be applied to any dataset that follows the input format described below.

---

## Author

**Krzesimir Szymankiewicz**  
Department of Virology and Viral Animal Diseases  
National Veterinary Research Institute  
57 Partyzantów Avenue, 24-100 Puławy, Poland  
📧 krzesimir.szymankiewicz@piwet.pulawy.pl

---

## Repository structure

```
GeoVariant-PL/
├── data/
│   └── example_data.csv          # Synthetic example dataset (100 records)
├── result/
│   ├── geo_cache.json             # Coordinate cache (auto-generated)
│   └── result_example.xlsx        # Geocoded output (auto-generated)
├── scripts/
│   ├── geocode.py                 # Step 1 – geocoding via Nominatim
│   ├── plot_maps.py               # Step 2 – interactive HTML + static PNG maps
│   └── plot_maps_geopandas.py     # Step 2 (alt) – static choropleth maps
├── README.md
├── LICENSE
└── requirements.txt
```

---

## Data availability

Due to legal and biosecurity restrictions, the original dataset cannot be shared publicly. This repository includes a **synthetic example dataset** (`data/example_data.csv`, 100 records) that mirrors the structure of the original data and can be used to run and test the full pipeline without modification.

---

## Input data format

The input file (tab-separated CSV or `.xlsx`) must contain the following columns:

| Column | Description |
|---|---|
| `id` | Record identifier |
| `species` | Species name |
| `voivodeship` | Administrative level 1 (Poland) |
| `county` | Administrative level 2 |
| `commune` | Administrative level 3 |
| `locality` | Locality name |
| `v1` | Variant / category column 1 |
| `v2` | Variant / category column 2 |
| `v3` | Variant / category column 3 |

Variant columns accept Roman numerals `I`, `II`, `III`, `IV`. Records with values `x`, `X`, or `.` are treated as missing and excluded from all maps.

---

## Requirements

Python 3.10 or higher is recommended.

```bash
pip install -r requirements.txt
```

Main dependencies: `pandas`, `openpyxl`, `geopy`, `certifi`, `folium`, `geopandas`, `matplotlib`, `unidecode`.

---

## Usage

### Step 1 — Geocode locations

```bash
python scripts/geocode.py
```

Builds a geocoding query from each unique combination of locality, commune, county, and voivodeship, then queries the [Nominatim](https://nominatim.openstreetmap.org/) API (rate-limited to 1 request/second in accordance with the usage policy). Results are written to `result/result_example.xlsx` with `X` (latitude) and `Y` (longitude) columns appended.

Intermediate results are cached in `result/geo_cache.json` every 50 queries — the process is safe to interrupt and resume. To skip API calls and use only cached coordinates, set `USE_CACHE_ONLY = True` at the top of `geocode.py`.

### Step 2 — Generate maps

```bash
python scripts/plot_maps.py
```

Produces one interactive HTML map and one static PNG map per variant column. Maps include:

- Color-coded point markers by variant value:

| Value | Color |
|---|---|
| I | Steel blue |
| II | Soft red |
| III | Green |
| IV | Purple |

- Voivodeship borders from a local shapefile (English labels)
- Major city markers with labels
- Interactive tooltip with record details (HTML maps)
- In-map legend

> **Shapefile required:** The voivodeship boundary shapefile is not included in this repository. Download `wojewodztwa.shp` (`.dbf`, `.shx`) from the Polish Central Statistical Office at [https://www.gis.gov.pl](https://www.gis.gov.pl) and place the files in `data/shp/`. The script automatically handles reprojection to WGS84 and corrects common encoding issues (mojibake) found in GUS files.

### Step 3 — Choropleth maps (optional)

```bash
python scripts/plot_maps_geopandas.py
```

Aggregates variant counts by voivodeship and produces choropleth PNG maps using a sequential color scale. Requires the same shapefile as Step 2.

---

## Output files

| File | Description |
|---|---|
| `result/result_example.xlsx` | Input data with `X` (latitude) and `Y` (longitude) appended |
| `result/maps/map_v1.html` | Interactive Folium map — variant 1 |
| `result/maps/map_v2.html` | Interactive Folium map — variant 2 |
| `result/maps/map_v3.html` | Interactive Folium map — variant 3 |
| `result/maps/map_v1.png` | Static PNG map — variant 1 |
| `result/maps/map_v2.png` | Static PNG map — variant 2 |
| `result/maps/map_v3.png` | Static PNG map — variant 3 |
| `result/maps/choropleth_v*.png` | Choropleth maps per variant (optional) |

---

## Technical notes

- **Encoding robustness:** GUS shapefiles are sometimes saved with UTF-8 content misread as latin-1 (mojibake). The pipeline detects and corrects this automatically before matching voivodeship names to their English translations.
- **Geocoding accuracy:** Nominatim accuracy depends on OpenStreetMap coverage for small Polish localities. Inspect `geo_cache.json` for entries with `[null, null]` coordinates, which indicate failed lookups that may require manual correction.
- **Font handling:** The script selects the best available system font automatically (Arial on macOS, FreeSans on Linux). All map labels are ASCII-safe to avoid rendering issues with Polish diacritics in Matplotlib.
- **Adaptability:** The pipeline is designed for Polish administrative data. Adapting it to other countries requires modifying the query string in `geocode.py` and replacing the voivodeship shapefile.

---

## Citation

If you use this software in your research, please cite it using the DOI above or the metadata provided in the Zenodo record associated with this repository.

> Szymankiewicz, K. (2024). *GeoVariant-PL: A geospatial pipeline for geocoding and variant visualization from administrative records in Poland*. Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

The MIT License allows free use, modification, and distribution of this software, including for commercial purposes, provided that the original author credit is retained.
