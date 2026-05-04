import pandas as pd
import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import unidecode
import os
import warnings
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")

# =========================
# PARAMETERS
# =========================
INPUT_FILE = "./result/result_example.csv"
OUTPUT_DIR = "./result/maps"
SHP_FILE   = "./data/shp/wojewodztwa.shp"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# Font selection (with Polish/Latin Extended support)
# =========================
MAP_FONT = "DejaVu Sans"
for candidate in ["FreeSans", "Arial", "Helvetica", "Carlito", "Liberation Sans"]:
    try:
        fm.findfont(fm.FontProperties(family=candidate), fallback_to_default=False)
        MAP_FONT = candidate
        break
    except Exception:
        continue
print(f"Font: {MAP_FONT}")

# =========================
# Load data
# =========================
df = pd.read_csv(INPUT_FILE)
print("Columns:", df.columns.tolist())
print(f"Records loaded: {len(df)}")
for col in ["v1", "v2", "v3"]:
    if col in df.columns:
        print(f"  {col} → unique values: {sorted(df[col].dropna().unique())}")

# =========================
# Load shapefile – always reproject to WGS84
# =========================
gdf = gpd.read_file(SHP_FILE)
if gdf.crs is None:
    gdf = gdf.set_crs(epsg=2180)   # GUS files are typically PL-1992
gdf = gdf.to_crs(epsg=4326)

# English voivodeship names – keyed by unidecode-normalised string
# Robust against encoding issues, mixed case, trailing spaces, cp1250 artefacts
VOIVODESHIP_EN: dict[str, str] = {
    "dolnoslaskie":        "Lower Silesia",
    "kujawsko-pomorskie":  "Kuyavian-Pomeranian",
    "lubelskie":           "Lublin",
    "lubuskie":            "Lubusz",
    "lodzkie":             "Lodz",
    "malopolskie":         "Lesser Poland",
    "mazowieckie":         "Masovian",
    "opolskie":            "Opole",
    "podkarpackie":        "Subcarpathian",
    "podlaskie":           "Podlaskie",
    "pomorskie":           "Pomeranian",
    "slaskie":             "Silesian",
    "swietokrzyskie":      "Holy Cross",
    "warminsko-mazurskie": "Warmian-Masurian",
    "wielkopolskie":       "Greater Poland",
    "zachodniopomorskie":  "West Pomeranian",
}

def fix_encoding(s: str) -> str:
    """Fix mojibake: UTF-8 bytes misread as latin-1 (common in GUS shapefiles)."""
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s   # already correct UTF-8

def to_english(raw_name: object) -> str:
    """Translate Polish voivodeship name to English.
    Robust against mojibake, mixed case, and trailing whitespace.
    """
    fixed   = fix_encoding(str(raw_name).strip())
    normalized = unidecode.unidecode(fixed).lower()
    result  = VOIVODESHIP_EN.get(normalized)
    if result is None:
        print(f"  [WARNING] Voivodeship not matched: {raw_name!r} -> {fixed!r} -> {normalized!r}")
        return fixed   # show at least the fixed (readable) name
    return result

# Add English name column to GeoDataFrame
gdf["NAME_EN"] = gdf["JPT_NAZWA_"].apply(to_english)

voivodeships_geojson = gdf.to_json()

gdf["centroid_lat"] = gdf.geometry.centroid.y
gdf["centroid_lon"] = gdf.geometry.centroid.x

lon_min, lat_min, lon_max, lat_max = gdf.total_bounds
print(f"Bounding box: lon {lon_min:.2f}–{lon_max:.2f}, lat {lat_min:.2f}–{lat_max:.2f}")

# =========================
# Major Polish cities
# =========================
CITIES = [
    ("Warsaw",        52.2297,  21.0122),
    ("Krakow",        50.0647,  19.9450),
    ("Lodz",          51.7592,  19.4560),
    ("Wroclaw",       51.1079,  17.0385),
    ("Poznan",        52.4064,  16.9252),
    ("Gdansk",        54.3520,  18.6466),
    ("Szczecin",      53.4285,  14.5528),
    ("Bydgoszcz",     53.1235,  18.0084),
    ("Lublin",        51.2465,  22.5684),
    ("Katowice",      50.2649,  19.0238),
    ("Bialystok",     53.1325,  23.1688),
    ("Rzeszow",       50.0412,  21.9991),
    ("Kielce",        50.8661,  20.6286),
    ("Olsztyn",       53.7784,  20.4801),
    ("Opole",         50.6751,  17.9213),
    ("Zielona Gora",  51.9356,  15.5062),
]

# =========================
# Roman numeral → integer
# =========================
ROMAN_TO_INT: dict[str, int] = {"I": 1, "II": 2, "III": 3, "IV": 4}

def roman_to_int(value: object) -> int | None:
    if pd.isnull(value):  # type: ignore[arg-type]
        return None
    if isinstance(value, str):
        return ROMAN_TO_INT.get(value.strip().upper())
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None

# =========================
# Colors — accessible palette
# =========================
COLOR_MAP: dict[int, str] = {
    1: "#4393c3",   # steel blue   – I
    2: "#d6604d",   # soft red     – II
    3: "#4dac26",   # fresh green  – III
    4: "#7b3294",   # purple       – IV
}

LEGEND_LABELS: dict[int, str] = {1: "I", 2: "II", 3: "III", 4: "IV"}

def get_color(value: object) -> str | None:
    n = roman_to_int(value)
    if n is None:
        return None
    return COLOR_MAP.get(n)

def should_skip(value: object) -> bool:
    if pd.isnull(value):  # type: ignore[arg-type]
        return True
    if isinstance(value, str) and value.strip().lower() in ("x", "."):
        return True
    return False

# =========================
# HTML legend – clean card style
# =========================
def add_legend(map_obj: folium.Map, used_values: set[int], column_name: str) -> None:
    items = ""
    for val in sorted(used_values):
        color = COLOR_MAP.get(val, "#aaa")
        label = LEGEND_LABELS.get(val, str(val))
        items += f"""
        <div style="display:flex;align-items:center;margin-bottom:8px;">
          <div style="width:14px;height:14px;border-radius:50%;background:{color};
               margin-right:10px;flex-shrink:0;
               box-shadow:0 1px 3px rgba(0,0,0,0.25);"></div>
          <span style="font-size:13px;color:#333;">Variant {label}</span>
        </div>"""

    html = f"""
    <div style="
        position:fixed; bottom:36px; right:20px;
        background:rgba(255,255,255,0.96);
        border:none;
        border-radius:10px;
        padding:14px 18px;
        font-family:'Segoe UI',Arial,sans-serif;
        z-index:9999;
        box-shadow:0 4px 16px rgba(0,0,0,0.14);
        min-width:150px;">
      <div style="font-size:11px;font-weight:600;letter-spacing:0.08em;
                  text-transform:uppercase;color:#888;margin-bottom:10px;">
        {column_name.upper()}
      </div>
      {items}
    </div>"""
    map_obj.get_root().html.add_child(folium.Element(html))  # type: ignore[union-attr]

# =========================
# Interactive HTML map (Folium)
# =========================
def create_html_map(column_name: str) -> None:
    if column_name not in df.columns:
        print(f"[SKIPPED] Column '{column_name}' not found.")
        return

    valid_rows = df[df["X"].notnull() & df["Y"].notnull()].copy()
    if valid_rows.empty:
        return

    m = folium.Map(location=[52.0, 19.5], zoom_start=6, tiles=None)

    folium.TileLayer(tiles="", attr=" ", name="white",
                     overlay=False, control=False).add_to(m)

    m.get_root().html.add_child(folium.Element(  # type: ignore[union-attr]
        "<style>.leaflet-container{background:#f8f9fa !important;}</style>"
    ))

    # Voivodeships – pastel green fill, English tooltip
    folium.GeoJson(
        voivodeships_geojson,
        name="Voivodeships",
        style_function=lambda _: {
            "fillColor":   "#c8e6c9",
            "color":       "#4a4a4a",
            "weight":      1.8,
            "fillOpacity": 0.9,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME_EN"],
            aliases=["Voivodeship:"],
            localize=False,
            style="font-family:Arial;font-size:13px;"
        )
    ).add_to(m)

    # Voivodeship labels – English, uppercase
    for _, woj in gdf.iterrows():
        folium.Marker(
            location=[float(woj["centroid_lat"]), float(woj["centroid_lon"])],
            icon=folium.DivIcon(
                html=(f'<div style="font-size:8px;font-family:Arial,sans-serif;'
                      f'font-weight:700;color:#444;text-align:center;'
                      f'white-space:nowrap;pointer-events:none;letter-spacing:0.04em;">'
                      f'{str(woj["NAME_EN"]).upper()}</div>'),
                icon_size=(140, 20),
                icon_anchor=(70, 10),
            )
        ).add_to(m)

    # Cities
    for city_name, lat, lon in CITIES:
        folium.CircleMarker(
            location=[lat, lon], radius=4, color="#666",
            fill=True, fill_color="#fff", fill_opacity=1.0,
            weight=1.5, tooltip=city_name,
        ).add_to(m)
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=(f'<div style="font-size:9px;font-family:Arial,sans-serif;'
                      f'color:#222;margin-left:7px;margin-top:-6px;'
                      f'white-space:nowrap;pointer-events:none;">{city_name}</div>'),
                icon_size=(110, 16), icon_anchor=(0, 8),
            )
        ).add_to(m)

    # Data points
    used_values: set[int] = set()
    for _, row in valid_rows.iterrows():
        raw_val = row[column_name]
        if should_skip(raw_val):
            continue
        color = get_color(raw_val)
        if color is None:
            continue
        n = roman_to_int(raw_val)
        if n is not None:
            used_values.add(n)
        parts = [f"{f}: {row[f]}" for f in
                 ["id", "species", "locality", "commune", "county", "voivodeship"]
                 if f in row and pd.notnull(row[f])]
        parts.append(f"{column_name}: {raw_val}")
        folium.CircleMarker(
            location=[float(row["X"]), float(row["Y"])],
            radius=7, color=color, fill=True, fill_color=color,
            fill_opacity=0.88, weight=1.2,
            tooltip=" | ".join(parts),
        ).add_to(m)

    if used_values:
        add_legend(m, used_values, column_name)

    out = os.path.join(OUTPUT_DIR, f"map_{column_name}.html")
    m.save(out)
    print(f"  HTML: {out}")

# =========================
# Static PNG map (Matplotlib)
# =========================
def create_png_map(column_name: str) -> None:
    if column_name not in df.columns:
        return

    valid_rows = df[df["X"].notnull() & df["Y"].notnull()].copy()
    if valid_rows.empty:
        return

    fig, ax = plt.subplots(figsize=(12, 12), dpi=200)
    fig.patch.set_facecolor("#f8f9fa")
    ax.set_facecolor("#f8f9fa")

    # Voivodeships
    gdf.plot(ax=ax, color="#c8e6c9", edgecolor="#4a4a4a", linewidth=0.8)

    # English voivodeship labels (ASCII-safe for matplotlib)
    for _, woj in gdf.iterrows():
        ax.annotate(
            unidecode.unidecode(str(woj["NAME_EN"])).upper(),
            xy=(float(woj["centroid_lon"]), float(woj["centroid_lat"])),
            ha="center", va="center",
            fontsize=4.5, color="#444444", fontweight="bold",
            fontfamily=MAP_FONT,
        )

    # Cities
    for city_name, lat, lon in CITIES:
        ax.plot(lon, lat, "o", markersize=3, color="white",
                markeredgecolor="#555555", markeredgewidth=0.8, zorder=4)
        ax.annotate(
            unidecode.unidecode(city_name), xy=(lon, lat),
            xytext=(3, 3), textcoords="offset points",
            fontsize=4.5, color="#222222", zorder=5,
            fontfamily=MAP_FONT,
        )

    # Data points
    used_values: set[int] = set()
    plotted = 0
    for _, row in valid_rows.iterrows():
        raw_val = row[column_name]
        if should_skip(raw_val):
            continue
        color = get_color(raw_val)
        if color is None:
            continue
        n = roman_to_int(raw_val)
        if n is not None:
            used_values.add(n)
        ax.plot(
            float(row["Y"]), float(row["X"]),
            "o", markersize=5.5, color=color,
            markeredgecolor="white", markeredgewidth=0.5,
            zorder=6, alpha=0.90,
        )
        plotted += 1

    # Legend – clean, right side
    if used_values:
        handles = [
            mpatches.Patch(
                color=COLOR_MAP[v],
                label=f"Variant {LEGEND_LABELS[v]}"
            )
            for v in sorted(used_values)
        ]
        legend = ax.legend(
            handles=handles,
            title=column_name.upper(),
            title_fontsize=7,
            loc="lower right",
            frameon=True,
            fontsize=7,
            framealpha=0.95,
            edgecolor="#cccccc",
            borderpad=0.8,
            labelspacing=0.6,
        )
        legend.get_frame().set_linewidth(0.6)

    ax.set_title(f"Variant distribution - {column_name.upper()}",
                 fontsize=11, pad=10, fontfamily=MAP_FONT, color="#333333")
    ax.set_axis_off()

    margin = 0.3
    ax.set_xlim(lon_min - margin, lon_max + margin)
    ax.set_ylim(lat_min - margin, lat_max + margin)

    out = os.path.join(OUTPUT_DIR, f"map_{column_name}.png")
    plt.savefig(out, dpi=200, bbox_inches="tight",
                facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"  PNG:  {out}  ({plotted} points)")


# =========================
# Generate maps
# =========================
for col in ["v1", "v2", "v3"]:
    print(f"\n── {col} ──")
    create_html_map(col)
    create_png_map(col)