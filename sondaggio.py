import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

st.set_page_config(page_title="Trova Fermate più Vicine", layout="wide")
st.title("📍 Trova le Fermate più Vicine")

st.markdown("Inserisci un indirizzo reale (via e numero civico) di partenza e arrivo. Il sistema ti darà le fermate più vicine.")

# ------------------ Load fermate autobus ------------------
fermate_df = pd.read_csv("stops.txt")
fermate = [
    {
        "stop_name": row["stop_name"],
        "lat": row["stop_lat"],
        "lon": row["stop_lon"]
    }
    for _, row in fermate_df.iterrows()
]

# ------------------ Geocodifica ------------------
geolocator = Nominatim(user_agent="jesi_tpl_survey")

def geocodifica(indirizzo):
    try:
        location = geolocator.geocode(f"{indirizzo}, Jesi, Italia")
        if location:
            return (location.latitude, location.longitude)
    except:
        return None

    return None

def fermata_piu_vicina(lat, lon):
    punto = (lat, lon)
    return min(fermate, key=lambda f: geodesic(punto, (f["lat"], f["lon"])).meters)

# ------------------ Input ------------------
via_partenza = st.text_input("🛫 Via e numero civico di partenza (es. Via Roma 30)")
via_arrivo = st.text_input("🛬 Via e numero civico di arrivo (es. Via Paradiso 12)")

if via_partenza and via_arrivo:
    coord_partenza = geocodifica(via_partenza)
    coord_arrivo = geocodifica(via_arrivo)

    if coord_partenza and coord_arrivo:
        fermata_o = fermata_piu_vicina(*coord_partenza)
        fermata_d = fermata_piu_vicina(*coord_arrivo)

        st.success(f"📍 Fermata più vicina alla partenza: **{fermata_o['stop_name']}**")
        st.success(f"📍 Fermata più vicina all’arrivo: **{fermata_d['stop_name']}**")
    else:
        st.error("❌ Non siamo riusciti a trovare uno degli indirizzi. Assicurati che sia scritto correttamente.")
