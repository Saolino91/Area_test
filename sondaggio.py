import streamlit as st
import json
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
import pandas as pd
import os
import socket
from datetime import datetime
from shapely.geometry import shape

st.set_page_config(page_title="Sondaggio TPL Jesi", layout="wide")
st.title("\U0001F4CB Sondaggio sul Trasporto Pubblico Urbano di Jesi")

st.markdown("""
Aiutaci a migliorare il servizio!\n
Clicca sulla mappa per indicare **da dove parti** e **dove vuoi arrivare**.\n
Poi rispondi a poche domande per capire meglio come usi l'autobus.\n
Le risposte sono **anonime** e servono solo per fini statistici.
""")

# ---------------------- Load quartieri ----------------------
with open("quartieri_jesi.geojson", "r", encoding="utf-8") as f:
    quartieri_geojson = json.load(f)

# Colori ufficiali per i quartieri (presi dal progetto principale)
quartiere_colori = {
    "Smia - Zona Industriale": "orange",
    "Coppi - Giardini": "lightgreen",
    "Prato": "red",
    "Minonna": "blue",
    "Paradiso": "yellow",
    "San Francesco": "pink",
    "Erbarella - San Pietro Martire": "violet",
    "San Giuseppe": "brown",
    "Centro Storico": "gray",
    "Via Roma": "lightgray"
}

# Mappa dei quartieri con poligoni e interazione clic
quartieri = {}
for feature in quartieri_geojson["features"]:
    nome = feature["properties"].get("layer", "Sconosciuto")
    geom = shape(feature["geometry"])
    lon, lat = geom.centroid.xy
    quartieri[nome] = {
        "centroide": (lat[0], lon[0]),
        "geometry": feature["geometry"],
        "properties": feature["properties"]
    }

# Recupero selezione e stato step
if "selected" not in st.session_state:
    st.session_state.selected = {"origine": None, "destinazione": None}
if "step" not in st.session_state:
    st.session_state.step = 1

selected = st.session_state.selected
step = st.session_state.step

# Messaggio guida step-by-step
if step == 1:
    st.info("👣 Step 1: clicca su un quartiere per selezionare la tua zona di partenza")
elif step == 2:
    st.info(f"✅ Partenza: {selected['origine']}\n👣 Step 2: seleziona la destinazione")

# Costruzione mappa
m = folium.Map(location=[43.518, 13.243], zoom_start=13)

for nome, info in quartieri.items():
    colore = "gray"
    if selected["origine"] == nome:
        colore = quartiere_colori.get(nome, "green")
    elif selected["destinazione"] == nome:
        colore = quartiere_colori.get(nome, "red")

    # Disegna poligono colorato
 gj = folium.GeoJson(
    data=info["geometry"],
    name=nome,
    style_function=lambda feat, colore=colore: {
        "fillColor": colore,
        "color": "black",
        "weight": 1.5,
        "fillOpacity": 0.5
    },
    tooltip=folium.Tooltip(nome),
    popup=folium.Popup(f"Clicca qui per selezionare {nome}", max_width=300)
)
gj.add_to(m)


    # Nome del quartiere visibile al centro
    folium.map.Marker(
        location=info["centroide"],
        icon=DivIcon(
            icon_size=(150, 36),
            icon_anchor=(0, 0),
            html=f'<div style="font-size: 10pt; font-weight: bold; color: black; background-color: transparent; padding: 2px; border-radius: 4px;">{nome}</div>'
        )
    ).add_to(m)

# Visualizza mappa
click_data = st_folium(m, height=500)

# Gestione clic
if click_data and "last_object_clicked_tooltip" in click_data:
    nome_q = click_data["last_object_clicked_tooltip"]
    if step == 1:
        selected["origine"] = nome_q
        st.session_state.step = 2
    elif step == 2 and nome_q != selected["origine"]:
        selected["destinazione"] = nome_q
        st.session_state.step = 3
    st.session_state.selected = selected


# Pulsante reset
if selected["origine"] or selected["destinazione"]:
    if st.button("🔄 Reset selezione"):
        st.session_state.selected = {"origine": None, "destinazione": None}
        st.session_state.step = 1

# ---------------------- FORM ----------------------
if step == 3:
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

            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                if ip in df["ip"].values:
                    st.warning("Hai già compilato il sondaggio da questo dispositivo. Grazie!")
                else:
                    nuova.to_csv(file_path, mode="a", index=False, header=False)
                    st.success("Grazie per aver partecipato al sondaggio!")
                    st.session_state.selected = {"origine": None, "destinazione": None}
                    st.session_state.step = 1
            else:
                nuova.to_csv(file_path, index=False)
                st.success("Grazie per aver partecipato al sondaggio!")
                st.session_state.selected = {"origine": None, "destinazione": None}
                st.session_state.step = 1
