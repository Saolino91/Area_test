import streamlit as st
import json
import pandas as pd
import os
import socket
from datetime import datetime
from shapely.geometry import Point
from geopy.distance import geodesic

st.set_page_config(page_title="Sondaggio TPL Jesi", layout="wide")
st.title("\U0001F4CB Sondaggio sul Trasporto Pubblico Urbano di Jesi")

st.markdown("""
Aiutaci a migliorare il servizio!

Seleziona **via di partenza** e **via di arrivo** dalle vie esistenti. Il sistema troverà automaticamente la fermata più vicina.
""")

# ---------------------- Load fermate autobus ----------------------
fermate_df = pd.read_csv("stops.txt")
fermate = [
    {
        "stop_id": row["stop_id"],
        "stop_name": row["stop_name"],
        "lat": row["stop_lat"],
        "lon": row["stop_lon"]
    }
    for _, row in fermate_df.iterrows()
]

# ---------------------- Load vie da GeoJSON ----------------------
with open("vie_jesi.geojson", "r", encoding="utf-8") as f:
    vie_geojson = json.load(f)

vie_dict = {}
for feature in vie_geojson["elements"]:
    if feature["type"] == "way":
        tags = feature.get("tags", {})
        nome_via = tags.get("name")
        nodes = feature.get("geometry", [])
        if nome_via and nodes:
            lat = sum(p["lat"] for p in nodes) / len(nodes)
            lon = sum(p["lon"] for p in nodes) / len(nodes)
            vie_dict[nome_via] = (lat, lon)

nomi_vie = sorted(vie_dict.keys())

# ---------------------- Input indirizzi ----------------------
st.markdown("### ✍️ Seleziona la via di partenza e di arrivo")
via_partenza = st.selectbox("📍 Da dove parti?", nomi_vie)
via_arrivo = st.selectbox("🏁 Dove vuoi arrivare?", nomi_vie)

sessione_ready = False

def trova_fermata_piu_vicina(lat, lon):
    punto = (lat, lon)
    return min(fermate, key=lambda f: geodesic(punto, (f["lat"], f["lon"])).meters)

if via_partenza and via_arrivo:
    coord_partenza = vie_dict.get(via_partenza)
    coord_arrivo = vie_dict.get(via_arrivo)

    if coord_partenza and coord_arrivo:
        fermata_o = trova_fermata_piu_vicina(*coord_partenza)
        fermata_d = trova_fermata_piu_vicina(*coord_arrivo)

        st.success(f"Fermata più vicina alla partenza: {fermata_o['stop_name']}")
        st.success(f"Fermata più vicina all'arrivo: {fermata_d['stop_name']}")

        st.session_state["origine"] = fermata_o["stop_name"]
        st.session_state["destinazione"] = fermata_d["stop_name"]
        sessione_ready = True
    else:
        st.error("❌ Coordinate non trovate per una delle vie.")

# ---------------------- FORM ----------------------
if sessione_ready:
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

            nuova = pd.DataFrame.from_records([{
                "timestamp": datetime.now().isoformat(),
                "ip": ip,
                "origine": st.session_state["origine"],
                "destinazione": st.session_state["destinazione"],
                "frequenza": freq,
                "fascia_oraria": fascia,
                "motivo": motivo,
                "suggerimenti": suggerimenti
            }])

            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                if ip in df["ip"].values:
                    st.warning("Hai già compilato il sondaggio da questo dispositivo. Grazie!")
                else:
                    nuova.to_csv(file_path, mode="a", index=False, header=False)
                    st.success("Grazie per aver partecipato al sondaggio!")
                    st.session_state["origine"] = None
                    st.session_state["destinazione"] = None
            else:
                nuova.to_csv(file_path, index=False)
                st.success("Grazie per aver partecipato al sondaggio!")
                st.session_state["origine"] = None
                st.session_state["destinazione"] = None
