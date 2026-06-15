import streamlit as st

import streamlit as st

st.set_page_config(layout="wide")

left, center, right = st.columns([1, 2, 1])

with center:

    st.title("Geohistorisches Quiz")
    st.write(
        "Errate die historische Figur anhand von Geburts und Todesdaten!"
    )

    with st.expander("Anleitung"):
        st.write('''
            Mit Spielbeginn wird eine Karte angezeigt, auf der mit grün der Geburtsort und mit rot der Todesort einer
                historischen Figur markiert ist. Zusätzlich sind die entsprechenden Jahre angegeben.
            Ziel ist es aus diesen Informationen soll die Figur korrekt erraten werden.
        ''')


    clicked = st.button(
        "Start",
        type="primary",
        width="stretch"
    )

if clicked:
    st.success("Button wurde geklickt!")