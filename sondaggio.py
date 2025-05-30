import streamlit as st
import requests
import os
import pandas as pd
import socket
import json
from datetime import datetime
from geopy.distance import geodesic
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
from shapely.geometry import shape, Point
from pathlib import Path  # Utilizziamo pathlib per la gestione dei file

# Configurazione della pagina
st.set_page_config(page_title="Sondaggio TPL Jesi", layout="wide")
st.title(":clipboard: Sondaggio sul Trasporto Pubblico Urbano di Jesi")

# ---------------------- Stato della Sessione ----------------------
if "step" not in st.session_state:
    st.session_state.step = 1
if "luogo_partenza" not in st.session_state:
    st.session_state.luogo_partenza = None
if "luogo_arrivo" not in st.session_state:
    st.session_state.luogo_arrivo = None

# ---------------------- Funzione di Geocodifica ----------------------
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

# Recupero dello step corrente
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

# ---------------------- Step 3: Conferma e Visualizzazione ----------------------
elif step == 3:
    # Recupero dei dati salvati nella sessione
    luogo_partenza = st.session_state.get("luogo_partenza")
    luogo_arrivo = st.session_state.get("luogo_arrivo")
    
    if not luogo_partenza or not luogo_arrivo:
        st.error("Errore: Devi completare gli step precedenti per scegliere un punto di partenza e uno di arrivo.")
    else:
        # Conversione delle coordinate in float
        lat1, lon1 = float(luogo_partenza["lat"]), float(luogo_partenza["lon"])
        lat2, lon2 = float(luogo_arrivo["lat"]), float(luogo_arrivo["lon"])
        
        fermata_o = fermata_piu_vicina(lat1, lon1)
        fermata_d = fermata_piu_vicina(lat2, lon2)
        
        quartiere_p = trova_quartiere(fermata_o["lat"], fermata_o["lon"])
        quartiere_a = trova_quartiere(fermata_d["lat"], fermata_d["lon"])
        
        # Visualizzazione dei dettagli
        st.markdown(f"<span style='color:green'><b>Partenza:</b> {luogo_partenza['display_name']}</span>", unsafe_allow_html=True)
        st.code(f"Coordinate: ({lat1}, {lon1})", language="text")
        st.info(f"Fermata più vicina: {fermata_o['stop_name']} (ID: {fermata_o['stop_id']})")
        
        st.markdown(f"<span style='color:blue'><b>Arrivo:</b> {luogo_arrivo['display_name']}</span>", unsafe_allow_html=True)
        st.code(f"Coordinate: ({lat2}, {lon2})", language="text")
        st.info(f"Fermata più vicina: {fermata_d['stop_name']} (ID: {fermata_d['stop_id']})")
        
        # Visualizzazione della mappa con i quartieri e le fermate
        quartiere_colori = {
            "Smia - Zona Industriale": "orange",
            "Coppi - Giardini": "green",
            "Prato": "red",
            "Minonna": "blue",
            "Paradiso": "yellow",
            "San Francesco": "magenta",
            "Erbarella - San Pietro Martire": "purple",
            "San Giuseppe": "brown",
            "Centro Storico": "black",
            "Via Roma": "darkblue"
        }
        
        m = folium.Map(location=[(lat1 + lat2) / 2, (lon1 + lon2) / 2], zoom_start=14)
        
        for feat in geojson_quartieri["features"]:
            nome = feat["properties"].get("layer", "Sconosciuto")
            if nome not in [quartiere_p, quartiere_a]:
                continue
            colore = quartiere_colori.get(nome, "#cccccc")
            folium.GeoJson(
                feat,
                name=nome,
                style_function=lambda f, c=colore: {
                    "fillColor": c,
                    "color": "black",
                    "weight": 1.5,
                    "fillOpacity": 0.6
                }
            ).add_to(m)
            
            centroide = shape(feat["geometry"]).centroid
            folium.Marker(
                location=[centroide.y, centroide.x],
                icon=DivIcon(
                    icon_size=(150, 36),
                    icon_anchor=(0, 0),
                    html=f'<div style="font-size: 10pt; font-weight: bold; color: white; background-color: rgba(0,0,0,0.5); padding: 2px; border-radius: 4px;">{nome}</div>'
                )
            ).add_to(m)
        
        # Marker personalizzati per partenza e arrivo
        folium.Marker(
            location=[fermata_o["lat"], fermata_o["lon"]],
            tooltip=f"Fermata Partenza: {fermata_o['stop_name']}",
            icon=folium.Icon(color="green", icon="play", prefix="fa")
        ).add_to(m)
        folium.Marker(
            location=[fermata_d["lat"], fermata_d["lon"]],
            tooltip=f"Fermata Arrivo: {fermata_d['stop_name']}",
            icon=folium.Icon(color="red", icon="flag", prefix="fa")
        ).add_to(m)
        
        st.markdown("### :world_map: Mappa fermate e quartieri")
        st_folium(m, height=600, use_container_width=True)
        
        # ---------------------- Salvataggio Risposta in CSV ----------------------
        if st.button("Conferma e vai al sondaggio"):
            ip = socket.gethostbyname(socket.gethostname())
            # Uso pathlib per gestire il file in maniera più robusta
            file_path = Path("risposte_grezze.csv")

            # Controllo se il file esiste e se è scrivibile
            if not file_path.exists():
                st.warning(f"Il file {file_path} non esiste. Verrà creato.")
            elif not os.access(file_path, os.W_OK):
                st.error(f"Il file {file_path} non è scrivibile. Controlla i permessi!")
                st.stop()
            else:
                st.write("Il file è scrivibile, procedo con il salvataggio.")

            # Preparazione del record da salvare
            record = {
                "timestamp": datetime.now().isoformat(),
                "codice": ip,
                "nome_luogo_partenza": luogo_partenza['display_name'],
                "coord_partenza": f"({lat1}, {lon1})",
                "quartiere_partenza": quartiere_p if quartiere_p is not None else "N/D",
                "id_fermata_partenza": fermata_o['stop_id'],
                "fermata_partenza": fermata_o['stop_name'],
                "nome_luogo_arrivo": luogo_arrivo['display_name'],
                "coord_arrivo": f"({lat2}, {lon2})",
                "quartiere_arrivo": quartiere_a if quartiere_a is not None else "N/D",
                "id_fermata_arrivo": fermata_d['stop_id'],
                "fermata_arrivo": fermata_d['stop_name']
            }
            nuova = pd.DataFrame.from_records([record])

            # Salvataggio: se il file esiste e ha contenuto, appendo senza header, altrimenti creo un nuovo file con header
            try:
                if file_path.exists() and file_path.stat().st_size > 0:
                    nuova.to_csv(file_path, mode="a", index=False, header=False)
                else:
                    nuova.to_csv(file_path, index=False)
                st.success(":white_check_mark: Coordinate e fermate salvate correttamente!")
                st.session_state.step = 4
            except Exception as e:
                st.error("Errore nel salvataggio dei dati: " + str(e))

# ---------------------- Step 4: Prossimo modulo ----------------------
elif step == 4:
    st.header("Hai completato la prima parte del sondaggio!")
    st.markdown("Prosegui con la sezione successiva... (in fase di sviluppo)")
