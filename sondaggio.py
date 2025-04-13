import streamlit as st
import requests
import pandas as pd
import os
import socket
import json
from datetime import datetime
from geopy.distance import geodesic
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
from shapely.geometry import shape, Point

st.set_page_config(page_title="Sondaggio TPL Jesi", layout="wide")
st.title(":clipboard: Sondaggio sul Trasporto Pubblico Urbano di Jesi")

# ---------------------- Stato ----------------------
if "step" not in st.session_state:
    st.session_state.step = 1
if "luogo_partenza" not in st.session_state:
    st.session_state.luogo_partenza = None
if "luogo_arrivo" not in st.session_state:
    st.session_state.luogo_arrivo = None

# ---------------------- Geocodifica ----------------------
def cerca_luoghi(query):
    if len(query) < 3:
        return []
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{query}, Jesi, Italia",
        "format": "json",
        "addressdetails": 1,
        "limit": 5
    }
    headers = {"User-Agent": "conerobus-tpl-jesi/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error("Errore nella richiesta di geocodifica.")
    return []

# ---------------------- Caricamento Fermate ----------------------
fermate_df = pd.read_csv("stops.txt")
fermate = [
    {
        "stop_id": row["stop_id"],
        "stop_name": row["stop_name"],
        "lat": float(row["stop_lat"]),
        "lon": float(row["stop_lon"])
    }
    for _, row in fermate_df.iterrows()
]

# ---------------------- Caricamento Quartieri ----------------------
with open("quartieri_jesi.geojson", "r", encoding="utf-8") as f:
    geojson_quartieri = json.load(f)

quartieri = {}
for feat in geojson_quartieri["features"]:
    nome = feat["properties"].get("layer", "Sconosciuto")
    geom = shape(feat["geometry"])
    quartieri[nome] = geom

def trova_quartiere(lat, lon):
    punto = Point(lon, lat)
    for nome, geom in quartieri.items():
        if geom.contains(punto):
            return nome
    return None

def fermata_piu_vicina(lat, lon):
    return min(fermate, key=lambda f: geodesic((lat, lon), (f["lat"], f["lon"])).meters)

step = st.session_state.step

# ---------------------- Step 1: Luogo di partenza ----------------------
if step == 1:
    st.header("Step 1: Da dove parti?")
    via_partenza_input = st.text_input("Inserisci via, negozio o piazza di partenza")
    scelte_part = cerca_luoghi(via_partenza_input) if via_partenza_input else []

    if scelte_part:
        labels = [f["display_name"] for f in scelte_part]
        scelta = st.selectbox("Seleziona il punto di partenza:", labels, key="sel_part")
        scelta_originale = next((f for f in scelte_part if f["display_name"] == scelta), None)
        st.session_state.luogo_partenza = scelta_originale
        if scelta_originale:
            st.success(f"Hai selezionato: {scelta_originale['display_name']}")
        if st.button("Avanti"):
            st.session_state.step = 2

# ---------------------- Step 2: Luogo di arrivo ----------------------
elif step == 2:
    st.header("Step 2: Dove vuoi arrivare?")
    via_arrivo_input = st.text_input("Inserisci via, negozio o piazza di arrivo")
    scelte_arr = cerca_luoghi(via_arrivo_input) if via_arrivo_input else []

    if scelte_arr:
        labels = [f["display_name"] for f in scelte_arr]
        scelta = st.selectbox("Seleziona il punto di arrivo:", labels, key="sel_arr")
        scelta_originale = next((f for f in scelte_arr if f["display_name"] == scelta), None)
        st.session_state.luogo_arrivo = scelta_originale
        if scelta_originale:
            st.success(f"Hai selezionato: {scelta_originale['display_name']}")
        if st.button("Avanti"):
            st.session_state.step = 3

# ---------------------- Step 4: Prossimo modulo ----------------------
elif step == 4:
    st.header("Hai completato la prima parte del sondaggio!")
    st.markdown("Prosegui con la sezione successiva... (in fase di sviluppo)")
