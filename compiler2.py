import re
import time
from pathlib import Path

import requests
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import plotly.graph_objects as go


# ==================================================
# Einstellungen
# ==================================================

INPUT_FILE = Path("personen.csv")

DEFAULT_MAP_VIEW = "world"

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

USER_AGENT = "WikidataMapScript/0.1 (your-email@example.com)"

WORLD_MAP_URL = (
    "https://naturalearth.s3.amazonaws.com/"
    "110m_cultural/ne_110m_admin_0_countries.zip"
)


# ==================================================
# Hilfsfunktionen
# ==================================================

def slugify(text):
    text = str(text).strip().lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    text = text.replace("ß", "ss")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_")


def load_input_file(path=INPUT_FILE):
    """
    Lädt personen.csv.
    Erwartete Spalten:
    qid,name,map_view

    map_view ist optional.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Input-Datei nicht gefunden: {path}\n"
            "Lege eine CSV-Datei mit mindestens der Spalte 'qid' an."
        )

    df = pd.read_csv(path)

    if "qid" not in df.columns:
        raise ValueError("Die Input-Datei braucht eine Spalte namens 'qid'.")

    if "name" not in df.columns:
        df["name"] = ""

    if "map_view" not in df.columns:
        df["map_view"] = DEFAULT_MAP_VIEW

    df["qid"] = df["qid"].astype(str).str.strip()
    df["name"] = df["name"].fillna("").astype(str).str.strip()
    df["map_view"] = df["map_view"].fillna(DEFAULT_MAP_VIEW).astype(str).str.strip()

    df.loc[df["map_view"] == "", "map_view"] = DEFAULT_MAP_VIEW

    allowed_views = {"world", "europe", "central_europe", "germany"}

    invalid_views = sorted(set(df["map_view"]) - allowed_views)
    if invalid_views:
        raise ValueError(
            "Ungültige map_view-Werte in der CSV: "
            + ", ".join(invalid_views)
            + "\nErlaubt sind: world, europe, central_europe, germany"
        )

    df = df[df["qid"] != ""].copy()

    return df


def get_map_bounds(view):
    """
    Gibt Kartenausschnitt zurück:
    xmin, xmax, ymin, ymax
    """
    bounds = {
        "world": (-180, 180, -60, 85),
        "europe": (-12, 35, 34, 72),
        "central_europe": (3, 23, 45, 56.5),
        "germany": (5, 16, 47, 55.5),
    }

    if view not in bounds:
        raise ValueError(
            f"Unbekannter map_view: {view}. "
            "Erlaubt sind: world, europe, central_europe, germany"
        )

    return bounds[view]


# ==================================================
# Wikidata
# ==================================================

def query_wikidata(qids):
    """
    Holt Geburtsjahr, Todesjahr, Geburtsort, Todesort
    sowie Koordinaten der Orte aus Wikidata.
    """
    if isinstance(qids, str):
        qids = [qids]

    qids = [str(qid).strip() for qid in qids if str(qid).strip()]

    if not qids:
        return pd.DataFrame()

    values_block = " ".join(f"wd:{qid}" for qid in qids)

    query = f"""
    PREFIX bd: <http://www.bigdata.com/rdf#>
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX p: <http://www.wikidata.org/prop/>
    PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
    PREFIX wikibase: <http://wikiba.se/ontology#>

    SELECT ?person ?personLabel
           ?birthYear ?birthPlaceLabel ?birthLat ?birthLon
           ?deathYear ?deathPlaceLabel ?deathLat ?deathLon
    WHERE {{
      VALUES ?person {{ {values_block} }}

      OPTIONAL {{
        ?person wdt:P569 ?birthDate .
        BIND(YEAR(?birthDate) AS ?birthYear)
      }}

      OPTIONAL {{
        ?person wdt:P570 ?deathDate .
        BIND(YEAR(?deathDate) AS ?deathYear)
      }}

      OPTIONAL {{
        ?person wdt:P19 ?birthPlace .
        ?birthPlace p:P625 ?birthCoordStatement .
        ?birthCoordStatement psv:P625 ?birthCoordNode .
        ?birthCoordNode wikibase:geoLatitude ?birthLat .
        ?birthCoordNode wikibase:geoLongitude ?birthLon .
      }}

      OPTIONAL {{
        ?person wdt:P20 ?deathPlace .
        ?deathPlace p:P625 ?deathCoordStatement .
        ?deathCoordStatement psv:P625 ?deathCoordNode .
        ?deathCoordNode wikibase:geoLatitude ?deathLat .
        ?deathCoordNode wikibase:geoLongitude ?deathLon .
      }}

      SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "de,en".
      }}
    }}
    """

    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    }

    last_error = None

    for attempt in range(3):
        try:
            response = requests.post(
                SPARQL_ENDPOINT,
                data={
                    "query": query,
                    "format": "json",
                },
                headers=headers,
                timeout=60,
            )

            if response.status_code != 200:
                print("Wikidata-Fehlerantwort:")
                print(response.text[:2000])

            response.raise_for_status()
            data = response.json()
            break

        except requests.exceptions.HTTPError as error:
            last_error = error
            print(f"Versuch {attempt + 1}/3 fehlgeschlagen: {error}")
            time.sleep(3)

    else:
        raise last_error

    rows = []

    for item in data["results"]["bindings"]:
        rows.append({
            "qid": item.get("person", {}).get("value", "").split("/")[-1],
            "wikidata_label": item.get("personLabel", {}).get("value"),
            "birth_year": item.get("birthYear", {}).get("value"),
            "birth_place": item.get("birthPlaceLabel", {}).get("value"),
            "birth_lat": item.get("birthLat", {}).get("value"),
            "birth_lon": item.get("birthLon", {}).get("value"),
            "death_year": item.get("deathYear", {}).get("value"),
            "death_place": item.get("deathPlaceLabel", {}).get("value"),
            "death_lat": item.get("deathLat", {}).get("value"),
            "death_lon": item.get("deathLon", {}).get("value"),
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    for col in ["birth_lat", "birth_lon", "death_lat", "death_lon"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["birth_year", "death_year"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    df = (
        df.sort_values(["qid"])
        .groupby("qid", as_index=False)
        .first()
    )

    return df


# ==================================================
# Daten für das Spiel vorbereiten
# ==================================================

def prepare_game_data():
    """
    Lädt CSV, Wikidata-Daten und verbindet beides.
    """
    input_df = load_input_file(INPUT_FILE)

    qids = input_df["qid"].tolist()
    wikidata_df = query_wikidata(qids)

    if wikidata_df.empty:
        raise ValueError("Keine Daten aus Wikidata gefunden.")

    df = wikidata_df.merge(input_df, on="qid", how="left")

    df["display_name"] = df.apply(
        lambda row: (
            row["name"]
            if isinstance(row["name"], str) and row["name"].strip()
            else row["wikidata_label"]
            if isinstance(row["wikidata_label"], str) and row["wikidata_label"].strip()
            else row["qid"]
        ),
        axis=1,
    )

    return df


def load_land_map():
    """
    Lädt die Weltkarte und entfernt Ländergrenzen.
    """
    world = gpd.read_file(WORLD_MAP_URL)
    land = world.dissolve()
    return land


# ==================================================
# Karte für einzelne Person zeichnen
# ==================================================

def draw_person_map(land, row):
    """
    Erstellt eine Matplotlib-Figur für genau eine Person.
    Gibt zurück:
    fig, person_name
    """
    map_view = row["map_view"]

    fig, ax = plt.subplots(figsize=(14, 9))

    land.plot(
        ax=ax,
        color="whitesmoke",
        edgecolor="black",
        linewidth=0.6,
    )

    xmin, xmax, ymin, ymax = get_map_bounds(map_view)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_axis_off()

    label_dx = (xmax - xmin) * 0.015
    label_dy = (ymax - ymin) * 0.025

    person_name = row["display_name"]

    # Geburt = grün
    if pd.notna(row["birth_lat"]) and pd.notna(row["birth_lon"]):
        ax.scatter(
            row["birth_lon"],
            row["birth_lat"],
            s=110,
            marker="o",
            color="green",
            zorder=3,
        )

        if pd.notna(row["birth_year"]):
            ax.text(
                row["birth_lon"] + label_dx,
                row["birth_lat"] + label_dy,
                str(int(row["birth_year"])),
                fontsize=13,
                fontweight="bold",
                color="green",
                zorder=5,
                bbox=dict(
                    facecolor="white",
                    edgecolor="none",
                    alpha=0.8,
                    pad=2,
                ),
            )

    # Tod = rot
    if pd.notna(row["death_lat"]) and pd.notna(row["death_lon"]):
        ax.scatter(
            row["death_lon"],
            row["death_lat"],
            s=120,
            marker="x",
            color="red",
            linewidths=2.5,
            zorder=3,
        )

        if pd.notna(row["death_year"]):
            ax.text(
                row["death_lon"] + label_dx,
                row["death_lat"] - label_dy,
                str(int(row["death_year"])),
                fontsize=13,
                fontweight="bold",
                color="red",
                zorder=5,
                bbox=dict(
                    facecolor="white",
                    edgecolor="none",
                    alpha=0.8,
                    pad=2,
                ),
            )

    return fig, person_name


def draw_person_map_plotly(row, show_title=False):
    """
    Interaktive Karte für Streamlit/Plotly.
    Marker und Text bleiben beim Zoomen gleich groß.
    """
    map_view = row["map_view"]
    xmin, xmax, ymin, ymax = get_map_bounds(map_view)

    person_name = row["display_name"]

    fig = go.Figure()

    # Geburt = grün
    if pd.notna(row["birth_lat"]) and pd.notna(row["birth_lon"]):
        birth_text = ""
        if pd.notna(row["birth_year"]):
            birth_text = str(int(row["birth_year"]))

        fig.add_trace(
            go.Scattergeo(
                lon=[row["birth_lon"]],
                lat=[row["birth_lat"]],
                mode="markers+text",
                marker=dict(
                    size=14,
                    color="green",
                    symbol="circle",
                ),
                text=[birth_text],
                textposition="top right",
                textfont=dict(
                    size=18,
                    color="green",
                    family="Arial Black",
                ),
                name="Geburt",
                hoverinfo="skip",
            )
        )

    # Tod = rot
    if pd.notna(row["death_lat"]) and pd.notna(row["death_lon"]):
        death_text = ""
        if pd.notna(row["death_year"]):
            death_text = str(int(row["death_year"]))

        fig.add_trace(
            go.Scattergeo(
                lon=[row["death_lon"]],
                lat=[row["death_lat"]],
                mode="markers+text",
                marker=dict(
                    size=13,
                    color="red",
                    symbol="x",
                    line=dict(width=3),
                ),
                text=[death_text],
                textposition="bottom right",
                textfont=dict(
                    size=18,
                    color="red",
                    family="Arial Black",
                ),
                name="Tod",
                hoverinfo="skip",
            )
        )

    title = person_name if show_title else ""

    fig.update_layout(
        title=title,
        height=650,
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
        paper_bgcolor="white",
        plot_bgcolor="white",
        dragmode="pan",
    )

    fig.update_geos(
        projection_type="mercator",
        lonaxis=dict(
            range=[xmin, xmax],
            showgrid=False
        ),
        lataxis=dict(
            range=[ymin, ymax],
            showgrid=False
        ),
        showland=True,
        landcolor="whitesmoke",
        showocean=True,
        oceancolor="white",
        showcountries=False,
        showcoastlines=True,
        coastlinecolor="black",
        coastlinewidth=1,
        showframe=False,
        bgcolor="white",
    )

    return fig, person_name