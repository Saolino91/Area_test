import streamlit as st
import json
import folium
from streamlit_folium import st_folium
import pandas as pd
import os
import socket
from datetime import datetime

st.set_page_config(page_title="Sondaggio TPL Jesi", layout="wide")
st.title("\U0001F4CB Sondaggio sul Trasporto Pubblico Urbano di Jesi")

st.markdown("""
Aiutaci a migliorare il servizio!\n
Clicca sulla mappa per indicare **da dove parti** e **dove vuoi arrivare**.\n
Poi rispondi a poche domande per capire meglio come usi l'autobus.\n
Le risposte sono **anonime** e servono solo per fini statistici.
""")

# ---------------------- Load quartieri ----------------------
with open("data/quartieri_jesi.geojson", "r", encoding="utf-8") as f:
    quartieri_geojson = json.load(f)

# Estrai nome e centroide di ciascun quartiere
quartieri = {}
for feature in quartieri_geojson["features"]:
    nome = feature["properties"].get("layer", "Sconosciuto")
    coords = feature["geometry"]["coordinates"][0]
    lon = sum([p[0] for p in coords]) / len(coords)
    lat = sum([p[1] for p in coords]) / len(coords)
    quartieri[nome] = (lat, lon)

# ---------------------- MAPPA cliccabile ----------------------
st.markdown("#### 1. Clicca sulla mappa per selezionare origine e destinazione")

m = folium.Map(location=[43.518, 13.243], zoom_start=13)
selected = st.session_state.get("selected", {"origine": None, "destinazione": None})

for nome, (lat, lon) in quartieri.items():
    color = "green" if selected["origine"] == nome else "red" if selected["destinazione"] == nome else "blue"
    folium.Marker(
        [lat, lon],
        tooltip=f"{nome}",
        popup=f"Clicca per selezionare: {nome}",
        icon=folium.Icon(color=color)
    ).add_to(m)

clicked = st_folium(m, height=500)

# Match click con quartiere più vicino
if clicked and clicked.get("last_object_clicked_tooltip"):
    clicked_name = clicked["last_object_clicked_tooltip"]
    if selected["origine"] is None:
        selected["origine"] = clicked_name
    elif selected["destinazione"] is None and clicked_name != selected["origine"]:
        selected["destinazione"] = clicked_name
    st.session_state.selected = selected

# ---------------------- FORM ----------------------
if selected["origine"] and selected["destinazione"]:
    st.success(f"Origine: {selected['origine']} → Destinazione: {selected['destinazione']}")

    with st.form("sondaggio_form"):
        freq = st.selectbox("Quante volte prendi l'autobus in una settimana?", [
            "Ogni giorno",
            "2-3 volte a settimana",
            "Solo nel weekend",
            "Raramente",
            "Mai"
        ])

        fascia = st.selectbox("In che fascia oraria viaggi più spesso?", [
            "Mattina (6:00 - 9:00)",
            "Mezzogiorno (9:00 - 13:00)",
            "Pomeriggio (13:00 - 17:00)",
            "Sera (17:00 - 21:00)"
        ])

        motivo = st.selectbox("Perché usi principalmente l'autobus?", [
            "Scuola",
            "Lavoro",
            "Commissioni",
            "Tempo libero",
            "Visite mediche",
            "Altro"
        ])

        suggerimenti = st.text_area("Hai suggerimenti o segnalazioni? (facoltativo)")

        submitted = st.form_submit_button("Invia il sondaggio")

        if submitted:
            ip = socket.gethostbyname(socket.gethostname())
            file_path = "risposte.csv"

            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                if ip in df["ip"].values:
                    st.warning("Hai già compilato il sondaggio da questo dispositivo. Grazie!")
                else:
                    nuova = pd.DataFrame.from_records([{
                        "timestamp": datetime.now().isoformat(),
                        "ip": ip,
                        "origine": selected["origine"],
                        "destinazione": selected["destinazione"],
                        "frequenza": freq,
                        "fascia_oraria": fascia,
                        "motivo": motivo,
                        "suggerimenti": suggerimenti
                    }])
                    nuova.to_csv(file_path, mode="a", index=False, header=False)
                    st.success("Grazie per aver partecipato al sondaggio!")
                    st.session_state.selected = {"origine": None, "destinazione": None}
            else:
                nuova = pd.DataFrame.from_records([{
                    "timestamp": datetime.now().isoformat(),
                    "ip": ip,
                    "origine": selected["origine"],
                    "destinazione": selected["destinazione"],
                    "frequenza": freq,
                    "fascia_oraria": fascia,
                    "motivo": motivo,
                    "suggerimenti": suggerimenti
                }])
                nuova.to_csv(file_path, index=False)
                st.success("Grazie per aver partecipato al sondaggio!")
                st.session_state.selected = {"origine": None, "destinazione": None}

elif not selected["origine"]:
    st.info("Clicca su un quartiere per selezionare l'origine")
elif not selected["destinazione"]:
    st.info("Clicca su un altro quartiere per selezionare la destinazione")
