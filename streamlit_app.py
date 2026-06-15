import streamlit as st
import pandas as pd
import random

import compiler
import personen.csv

st.set_page_config(layout="wide")

left, center, right = st.columns([1, 2, 1])

person = None

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
    # Source - https://stackoverflow.com/a/43477355
    # Posted by Open AI - Opting Out, modified by community. See post 'Timeline' for change history
    # Retrieved 2026-06-15, License - CC BY-SA 3.0


    df = pd.read_csv("datei.csv")

    zeile = df.sample(n=1).iloc[0]

    Name = zeile.iloc[0]
    quid = zeile.iloc[1]
    map_size = zeile.iloc[2]

    fig = compiler.main(quid)

