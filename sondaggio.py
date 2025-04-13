import streamlit as st
import json
import folium
from streamlit_folium import st_folium
import pandas as pd
import os
import socket
from datetime import datetime
from shapely.geometry import shape, Point
from geopy.distance import geodesic

st.set_page_config(page_title="Sondaggio TPL Jesi", layout="wide")
st.title("\U0001F4CB Sondaggio sul Trasporto Pubblico Urbano di Jesi")

st.markdown("""
Aiutaci a migliorare il servizio!

Inserisci **via di partenza** e **via di arrivo**. Il sistema cercherà la fermata più vicina e il quartiere.
""")

# ---------------------- Load quartieri ----------------------
with open("quartieri_jesi.geojson", "r", encoding="utf-8") as f:
    quartieri_geojson = json.load(f)

quartieri = {}
for feature in quartieri_geojson["features"]:
    nome = feature["properties"].get("layer", "Sconosciuto")
    geom = shape(feature["geometry"])
    quartieri[nome] = geom

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

# ---------------------- Load vie (senza geopandas) ----------------------
with open("vie_jesi.geojson", "r", encoding="utf-8") as f:
    vie_geojson = json.load(f)

# Estrai nomi vie
nomi_vie = sorted({f["properties"].get("name", "") for f in vie_geojson["features"] if f["properties"].get("name")})

# ---------------------- Funzioni ----------------------
def trova_fermata_piu_vicina(lat, lon):
    punto = (lat, lon)
    return min(fermate, key=lambda f: geodesic(punto, (f["lat"], f["lon"])).meters)

def trova_quartiere(lat, lon):
    punto = Point(lon, lat)
    for nome, geom in quartieri.items():
        if geom.contains(punto):
            return nome
    return "Fuori Jesi"

def centroide_via(nome_via):
    matching = [shape(f["geometry"]) for f in vie_geojson["features"] if f["properties"].get("name") == nome_via]
    if matching:
        union = matching[0] if len(matching) == 1 else matching[0].union(*matching[1:])
        return union.centroid.y, union.centroid.x
    return None

# ---------------------- Input indirizzi ----------------------
st.markdown("### ✍️ Inserisci la tua partenza e destinazione")
via_partenza = st.selectbox("📍 Da dove parti?", nomi_vie)
via_arrivo = st.selectbox("🏁 Dove vuoi arrivare?", nomi_vie)

sessione_ready = False

if via_partenza and via_arrivo:
    coord_partenza = centroide_via(via_partenza)
    coord_arrivo = centroide_via(via_arrivo)

    if coord_partenza and coord_arrivo:
        fermata_o = trova_fermata_piu_vicina(*coord_partenza)
        fermata_d = trova_fermata_piu_vicina(*coord_arrivo)

        origine = trova_quartiere(fermata_o["lat"], fermata_o["lon"])
        destinazione = trova_quartiere(fermata_d["lat"], fermata_d["lon"])

        st.success(f"Origine: {origine} (fermata {fermata_o['stop_name']})")
        st.success(f"Destinazione: {destinazione} (fermata {fermata_d['stop_name']})")

        st.session_state["origine"] = origine
        st.session_state["destinazione"] = destinazione
        sessione_ready = True
    else:
        st.error("Non siamo riusciti a trovare le coordinate per una delle vie selezionate.")

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
