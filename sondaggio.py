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
with open("quartieri_jesi.geojson", "r", encoding="utf-8") as f:
    quartieri_geojson = json.load(f)

# Estrai nome e centroide di ciascun quartiere
quartieri = {}

from shapely.geometry import shape

for feature in quartieri_geojson["features"]:
    nome = feature["properties"].get("layer", "Sconosciuto")
    geom = shape(feature["geometry"])
    lon, lat = geom.centroid.xy
    quartieri[nome] = (lat[0], lon[0])


# ---------------------- MAPPA cliccabile ----------------------
from shapely.geometry import shape

st.markdown("#### 1. Clicca sulla mappa per selezionare origine e destinazione")

# Costruzione struttura quartieri
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

# Recupero selezione da sessione
selected = st.session_state.get("selected", {"origine": None, "destinazione": None})

# Costruzione mappa
m = folium.Map(location=[43.518, 13.243], zoom_start=13)

# Aggiunta poligoni interattivi e marker
for nome, info in quartieri.items():
    colore = "gray"
    if selected["origine"] == nome:
        colore = "green"
    elif selected["destinazione"] == nome:
        colore = "red"

    # Poligono cliccabile
    geojson = folium.GeoJson(
        info["geometry"],
        name=nome,
        tooltip=folium.Tooltip(f"{nome} - clicca per selezionare"),
        style_function=lambda feat, colore=colore: {
            "fillColor": colore,
            "color": "black",
            "weight": 1.5,
            "fillOpacity": 0.4
        }
    )
    geojson.add_to(m)

    # Marker al centroide per supporto visivo
    folium.Marker(
        location=info["centroide"],
        tooltip=f"{nome}",
        popup=f"Clicca per selezionare: {nome}",
        icon=folium.Icon(
            color="green" if selected["origine"] == nome else
                  "red" if selected["destinazione"] == nome else
                  "blue"
        )
    ).add_to(m)

# Visualizza mappa
click_data = st_folium(m, height=500)

# Gestione del clic sul poligono
if click_data and "last_object_clicked" in click_data:
    clicked_obj = click_data["last_object_clicked"]
    props = clicked_obj.get("properties") if isinstance(clicked_obj, dict) else None

    nome_q = None
    if props:
        nome_q = props.get("layer") or props.get("name") or props.get("tooltip")

    if nome_q:
        if selected["origine"] is None:
            selected["origine"] = nome_q
        elif selected["destinazione"] is None and nome_q != selected["origine"]:
            selected["destinazione"] = nome_q
        elif nome_q == selected["origine"] or nome_q == selected["destinazione"]:
            st.toast(f"Quartiere {nome_q} già selezionato.")
        st.session_state.selected = selected

# Bottone per resettare la selezione
if selected["origine"] or selected["destinazione"]:
    st.button("🔄 Reset selezione", on_click=lambda: st.session_state.update({"selected": {"origine": None, "destinazione": None}}))



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
