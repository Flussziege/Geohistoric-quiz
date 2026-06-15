import streamlit as st


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

st.button(
    label= "Start",
)