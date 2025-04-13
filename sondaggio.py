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
from geopy.geocoders import Nominatim

st.set_page_config(page_title="Sondaggio TPL Jesi", layout="wide")
st.title("\U0001F4CB Sondaggio sul Trasporto Pubblico Urbano di Jesi")

st.markdown("""
Aiutaci a migliorare il servizio!

Inserisci **via e numero civico** di partenza e di arrivo. Il sistema troverà automaticamente la fermata più vicina.
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

# ---------------------- Funzioni ----------------------
geolocator = Nominatim(user_agent="tpl_jesi_app")

def geocodifica_indirizzo(indirizzo):
    try:
        location = geolocator.geocode(f"{indirizzo}, Jesi, Italia")
        if location:
            return location.latitude, location.longitude
    except:
        return None
    return None

def trova_fermata_piu_vicina(lat, lon):
    punto = (lat, lon)
    return min(fermate, key=lambda f: geodesic(punto, (f["lat"], f["lon"])).meters)

# ---------------------- Input indirizzi ----------------------
st.markdown("### ✍️ Inserisci la tua partenza e destinazione con via e numero")
via_partenza = st.text_input("📍 Da dove parti? (Es. Via Roma 23)")
via_arrivo = st.text_input("🏁 Dove vuoi arrivare? (Es. Via Paradiso 45)")

sessione_ready = False

if via_partenza and via_arrivo:
    coord_partenza = geocodifica_indirizzo(via_partenza)
    coord_arrivo = geocodifica_indirizzo(via_arrivo)

    if coord_partenza and coord_arrivo:
        fermata_o = trova_fermata_piu_vicina(*coord_partenza)
        fermata_d = trova_fermata_piu_vicina(*coord_arrivo)

        st.success(f"Fermata più vicina alla partenza: {fermata_o['stop_name']}")
        st.success(f"Fermata più vicina all'arrivo: {fermata_d['stop_name']}")

        st.session_state["origine"] = fermata_o["stop_name"]
        st.session_state["destinazione"] = fermata_d["stop_name"]
        sessione_ready = True
    else:
        st.error("❌ Non siamo riusciti a trovare le coordinate per una delle vie inserite.")

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
