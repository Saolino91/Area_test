import streamlit as st
import requests
import pandas as pd
import os
import socket
from datetime import datetime
from geopy.distance import geodesic

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
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return []

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

# ---------------------- Step 3: Conferma e salvataggio ----------------------
elif step == 3:
    luogo_partenza = st.session_state.luogo_partenza
    luogo_arrivo = st.session_state.luogo_arrivo
    if luogo_partenza and luogo_arrivo:
        lat1, lon1 = float(luogo_partenza["lat"]), float(luogo_partenza["lon"])
        lat2, lon2 = float(luogo_arrivo["lat"]), float(luogo_arrivo["lon"])

        fermata_o = fermata_piu_vicina(lat1, lon1)
        fermata_d = fermata_piu_vicina(lat2, lon2)

        st.markdown(f"<span style='color:green'><b>Partenza:</b> {luogo_partenza['display_name']}</span>", unsafe_allow_html=True)
        st.code(f"Coordinate: ({lat1}, {lon1})", language="text")
        st.info(f"Fermata più vicina: {fermata_o['stop_name']} (ID: {fermata_o['stop_id']})")

        st.markdown(f"<span style='color:blue'><b>Arrivo:</b> {luogo_arrivo['display_name']}</span>", unsafe_allow_html=True)
        st.code(f"Coordinate: ({lat2}, {lon2})", language="text")
        st.info(f"Fermata più vicina: {fermata_d['stop_name']} (ID: {fermata_d['stop_id']})")

        if st.button("Conferma e vai al sondaggio"):
            ip = socket.gethostbyname(socket.gethostname())
            file_path = "risposte_grezze.csv"
            nuova = pd.DataFrame.from_records([{
                "timestamp": datetime.now().isoformat(),
                "ip": ip,
                "partenza": luogo_partenza['display_name'],
                "lat_p": lat1,
                "lon_p": lon1,
                "fermata_p": fermata_o['stop_name'],
                "id_fermata_p": fermata_o['stop_id'],
                "arrivo": luogo_arrivo['display_name'],
                "lat_a": lat2,
                "lon_a": lon2,
                "fermata_a": fermata_d['stop_name'],
                "id_fermata_a": fermata_d['stop_id']
            }])
            if os.path.exists(file_path):
                nuova.to_csv(file_path, mode="a", index=False, header=False)
            else:
                nuova.to_csv(file_path, index=False)
            st.success(":white_check_mark: Coordinate e fermate salvate correttamente!")
            st.session_state.step = 4

# ---------------------- Step 4: Prossimo modulo ----------------------
elif step == 4:
    st.header("Hai completato la prima parte del sondaggio!")
    st.markdown("Prosegui con la sezione successiva... (in fase di sviluppo)")
