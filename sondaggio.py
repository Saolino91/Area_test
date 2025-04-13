import streamlit as st
import requests
import pandas as pd
import os
import socket
from datetime import datetime

st.set_page_config(page_title="Sondaggio TPL Jesi", layout="wide")
st.title("\U0001F4CB Sondaggio sul Trasporto Pubblico Urbano di Jesi")

st.markdown("""
Aiutaci a migliorare il servizio!

Inizia scrivendo **da dove parti** e **dove vuoi arrivare**: puoi inserire una **via, una piazza, un negozio o un parcheggio**. Il sistema troverà automaticamente le coordinate.
""")

# ---------------------- Funzione per geocodifica Nominatim ----------------------
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

# ---------------------- Input partenza e arrivo ----------------------
st.markdown("### 📍 Inserisci i luoghi")
via_partenza_input = st.text_input("Da dove parti?")
via_arrivo_input = st.text_input("Dove vuoi arrivare?")

scelte_part = cerca_luoghi(via_partenza_input) if via_partenza_input else []
scelte_arr = cerca_luoghi(via_arrivo_input) if via_arrivo_input else []

luogo_partenza = None
luogo_arrivo = None

if scelte_part:
    labels = [f"{s['display_name']}" for s in scelte_part]
    scelta = st.selectbox("Seleziona il luogo di partenza:", labels, key="sel_part")
    luogo_partenza = next((s for s in scelte_part if s["display_name"] == scelta), None)

if scelte_arr:
    labels = [f"{s['display_name']}" for s in scelte_arr]
    scelta = st.selectbox("Seleziona il luogo di arrivo:", labels, key="sel_arr")
    luogo_arrivo = next((s for s in scelte_arr if s["display_name"] == scelta), None)

# ---------------------- Visualizza coordinate ----------------------
if luogo_partenza and luogo_arrivo:
    lat1, lon1 = float(luogo_partenza["lat"]), float(luogo_partenza["lon"])
    lat2, lon2 = float(luogo_arrivo["lat"]), float(luogo_arrivo["lon"])

    st.success(f"Partenza: {luogo_partenza['display_name']}\nCoordinate: ({lat1}, {lon1})")
    st.success(f"Arrivo: {luogo_arrivo['display_name']}\nCoordinate: ({lat2}, {lon2})")

    # ---------------------- Salvataggio nel CSV ----------------------
    with st.form("salvataggio_dati"):
        conferma = st.form_submit_button("✅ Conferma e salva")
        if conferma:
            ip = socket.gethostbyname(socket.gethostname())
            file_path = "risposte_grezze.csv"

            nuova = pd.DataFrame.from_records([{
                "timestamp": datetime.now().isoformat(),
                "ip": ip,
                "partenza": luogo_partenza['display_name'],
                "lat_p": lat1,
                "lon_p": lon1,
                "arrivo": luogo_arrivo['display_name'],
                "lat_a": lat2,
                "lon_a": lon2
            }])

            if os.path.exists(file_path):
                nuova.to_csv(file_path, mode="a", index=False, header=False)
            else:
                nuova.to_csv(file_path, index=False)

            st.success("📍 Dati salvati con successo! Ora puoi continuare con il sondaggio.")

else:
    st.info("Scrivi almeno 3 lettere per cercare la via o il luogo.")
