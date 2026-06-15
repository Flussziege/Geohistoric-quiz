import random

import streamlit as st
import matplotlib.pyplot as plt

import compiler2


# ==================================================
# Streamlit-Grundeinstellungen
# ==================================================

st.set_page_config(
    page_title="Geohistorisches Quiz",
    layout="wide"
)


# ==================================================
# Daten laden
# ==================================================

@st.cache_data(show_spinner="Lade Wikidata-Daten...")
def load_game_data():
    input_df = compiler2.load_input_file(compiler2.INPUT_FILE)

    qids = input_df["qid"].tolist()
    wikidata_df = compiler2.query_wikidata(qids)

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


@st.cache_resource(show_spinner="Lade Weltkarte...")
def load_land_map():
    world = compiler2.gpd.read_file(compiler2.WORLD_MAP_URL)
    land = world.dissolve()
    return land


def choose_random_person(df):
    index = random.randrange(len(df))
    st.session_state.current_index = index
    st.session_state.show_solution = False


# ==================================================
# Session State vorbereiten
# ==================================================

if "current_index" not in st.session_state:
    st.session_state.current_index = None

if "show_solution" not in st.session_state:
    st.session_state.show_solution = False


# ==================================================
# Daten vorbereiten
# ==================================================

df = load_game_data()
land = load_land_map()


# ==================================================
# Layout
# ==================================================

left, center, right = st.columns([1, 2, 1])

with center:
    st.title("Geohistorisches Quiz")

    st.write(
        "Errate die historische Figur anhand von Geburts- und Todesdaten."
    )

    with st.expander("Anleitung"):
        st.write(
            """
            Mit Spielbeginn wird eine Karte angezeigt.  
            Grün markiert den Geburtsort, rot markiert den Todesort.  
            Neben den Punkten stehen die jeweiligen Jahre.  
            
            Ziel ist es, aus diesen Informationen die historische Figur zu erraten.
            """
        )

    col_start, col_new = st.columns(2)

    with col_start:
        if st.button("Start", type="primary", use_container_width=True):
            choose_random_person(df)

    with col_new:
        if st.button("Neue Person", use_container_width=True):
            choose_random_person(df)


# ==================================================
# Spielanzeige
# ==================================================

if st.session_state.current_index is not None:
    row = df.iloc[st.session_state.current_index]

    st.divider()

    fig, person_name = compiler2.draw_person_map(land, row)

    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    guess = st.text_input("Wer ist die gesuchte Person?")

    col_check, col_solution = st.columns(2)

    with col_check:
        if st.button("Antwort prüfen", use_container_width=True):
            if guess.strip().lower() == person_name.strip().lower():
                st.success("Richtig!")
            else:
                st.error("Leider falsch.")

    with col_solution:
        if st.button("Lösung anzeigen", use_container_width=True):
            st.session_state.show_solution = True

    if st.session_state.show_solution:
        st.info(f"Die gesuchte Person ist: **{person_name}**")

else:
    st.info("Klicke auf **Start**, um das Quiz zu beginnen.")