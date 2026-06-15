import random
import unicodedata

import streamlit as st

import compiler2 as compiler


# ==================================================
# Streamlit Einstellungen
# ==================================================

st.set_page_config(
    page_title="Geohistorisches Quiz",
    layout="wide"
)


# ==================================================
# Hilfsfunktionen
# ==================================================

@st.cache_data(show_spinner="Lade Wikidata-Daten...")
def load_game_data():
    return compiler.prepare_game_data()


def normalize_text(text):
    """
    Macht Antworten vergleichbarer:
    - Kleinbuchstaben
    - Akzente entfernen
    - überflüssige Leerzeichen entfernen
    """
    text = str(text).strip().lower()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )

    text = " ".join(text.split())

    return text


def choose_random_person():
    """
    Wählt eine neue zufällige Person.
    Verhindert möglichst, dass dieselbe Person zweimal direkt nacheinander kommt.
    """
    df = st.session_state.df

    if len(df) == 0:
        return

    old_index = st.session_state.get("current_index")

    possible_indices = list(range(len(df)))

    if old_index is not None and len(possible_indices) > 1:
        possible_indices.remove(old_index)

    st.session_state.current_index = random.choice(possible_indices)
    st.session_state.show_solution = False
    st.session_state.feedback = None

    # sorgt dafür, dass das Antwortfeld bei neuer Person geleert wird
    st.session_state.input_counter += 1


def start_game():
    st.session_state.game_started = True
    choose_random_person()


def check_answer(guess, correct_name):
    if not guess:
        st.session_state.feedback = "empty"
        return

    user_answer = normalize_text(guess)
    correct_answer = normalize_text(correct_name)

    if user_answer == correct_answer:
        st.session_state.feedback = "correct"
    else:
        st.session_state.feedback = "wrong"


# ==================================================
# Session State
# ==================================================

if "game_started" not in st.session_state:
    st.session_state.game_started = False

if "current_index" not in st.session_state:
    st.session_state.current_index = None

if "show_solution" not in st.session_state:
    st.session_state.show_solution = False

if "feedback" not in st.session_state:
    st.session_state.feedback = None

if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0


# ==================================================
# Daten laden
# ==================================================

try:
    df = load_game_data()
    st.session_state.df = df

except Exception as error:
    st.error("Die Spieldaten konnten nicht geladen werden.")
    st.exception(error)
    st.stop()


# ==================================================
# Startmenü
# ==================================================

if not st.session_state.game_started:
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

                Grün markiert den Geburtsort.  
                Rot markiert den Todesort.  
                Neben den Punkten stehen die jeweiligen Jahre.

                Ziel ist es, aus diesen Informationen die historische Figur zu erraten.
                """
            )

        if st.button(
            "Start",
            type="primary",
            use_container_width=True
        ):
            start_game()
            st.rerun()


# ==================================================
# Quiz Ansicht
# ==================================================

else:
    st.title("Geohistorisches Quiz")

    row = df.iloc[st.session_state.current_index]

    fig, person_name = compiler.draw_person_map_plotly(
        row,
        show_title=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
        }
    )

    all_names = sorted(df["display_name"].dropna().unique())

    guess = st.selectbox(
        "Wer ist die gesuchte Person?",
        options=all_names,
        index=None,
        placeholder="Namen eingeben oder auswählen...",
        key=f"guess_{st.session_state.input_counter}"
    )

    col_check, col_solution, col_next = st.columns(3)

    with col_check:
        if st.button(
            "Antwort prüfen",
            use_container_width=True
        ):
            check_answer(guess, person_name)

    with col_solution:
        if st.button(
            "Lösung anzeigen",
            use_container_width=True
        ):
            st.session_state.show_solution = True

    with col_next:
        if st.button(
            "Neue Person",
            type="primary",
            use_container_width=True
        ):
            choose_random_person()
            st.rerun()

    if st.session_state.feedback == "empty":
        st.warning("Bitte gib zuerst einen Namen ein oder wähle einen aus.")

    elif st.session_state.feedback == "correct":
        st.success("Richtig!")

    elif st.session_state.feedback == "wrong":
        st.error("Leider falsch.")

    if st.session_state.show_solution:
        st.info(f"Die gesuchte Person ist: **{person_name}**")