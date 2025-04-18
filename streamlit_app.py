import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import st_folium
from datetime import datetime
from folium.features import CustomIcon
from geopy.distance import geodesic
from shapely.geometry import shape, Point

# ----------------- CONFIGURAZIONE PAGINA -----------------
st.set_page_config(layout="wide")
col1, col2 = st.columns([3, 2])
with col1:
    st.title("Servizio Urbano Jesi")
    st.markdown("""
        Esplora le linee del trasporto pubblico urbano di Jesi:
        - Seleziona le linee nella **sidebar** (botttoni colorati).
        - La **legenda** si accende quando clicchi una linea.
        - Attiva/disattiva quartieri e linee con il **Layer Control** (in alto a destra).
    """)
with col2:
    st.image("Logo_Conerobus.png", width=200)

# ----------------- FUNZIONI UTILI -----------------
def time_to_seconds(t):
    try:
        h, m, s = map(int, t.split(":"))
        return h * 3600 + m * 60 + s
    except:
        return None

def format_time_str(time_str):
    try:
        dt = datetime.strptime(time_str, "%H:%M:%S")
        return dt.strftime("%H:%M")
    except:
        return time_str

# ----------------- CARICAMENTO DATI -----------------
@st.cache_data
def load_data():
    stops = pd.read_csv("stops.txt")
    trips = pd.read_csv("trips.txt")
    stop_times = pd.read_csv("stop_times.txt")
    shapes = pd.read_csv("shapes.txt", header=None, skiprows=1,
                         names=["shape_id", "lat", "lon", "sequence", "shape_dist_traveled"])
    shapes["sequence"] = shapes["sequence"].astype(int)
    routes = pd.read_csv("routes.txt")
    with open("quartieri_jesi.geojson", "r", encoding="utf-8") as f:
        quartieri = json.load(f)
    return stops, trips, stop_times, shapes, routes, quartieri

stops, trips, stop_times, shapes, routes, quartieri_geojson = load_data()

# ----------------- SIDEBAR: BOTTONI + LEGGENDA -----------------
route_ids = sorted(trips["route_id"].unique())

if "route_colors" not in st.session_state:
    palette = ["red","blue","green","orange","purple","pink","cadetblue","darkred","darkgreen","black"]
    st.session_state.route_colors = {rid: palette[i % len(palette)] for i, rid in enumerate(route_ids)}
route_colors = st.session_state.route_colors

if "selected_routes" not in st.session_state:
    st.session_state.selected_routes = []

with st.sidebar:
    st.markdown("### Seleziona le linee da visualizzare:")
    btn_cols = st.columns(6)
    for idx, rid in enumerate(route_ids):
        col = btn_cols[idx % 6]
        color = route_colors[rid]
        selected = rid in st.session_state.selected_routes
        if col.button(
            rid,
            key=f"btn_{rid}",
            help="Clicca per attivare/disattivare",
            args=(),
            kwargs={}
        ):
            if selected:
                st.session_state.selected_routes.remove(rid)
            else:
                st.session_state.selected_routes.append(rid)

    # legenda attiva solo se ho almeno una linea selezionata
    if st.session_state.selected_routes:
        st.markdown("### Legenda linee")
        for rid in st.session_state.selected_routes:
            name = routes.loc[routes["route_id"] == rid, "route_long_name"].iloc[0]
            col = route_colors[rid]
            st.markdown(
                f"<span style='background:{col};padding:0.3em 0.6em;"
                f"border-radius:4px;color:white;font-weight:bold'>Linea {rid}</span>  {name}",
                unsafe_allow_html=True
            )

selected_routes = st.session_state.selected_routes

# ----------------- COSTRUZIONE MAPPA -----------------
if selected_routes:
    # centro mappa
    center = [stops["stop_lat"].mean(), stops["stop_lon"].mean()]
    m = folium.Map(location=center, zoom_start=13)

    # quartieri come layer toggle
    for feat in quartieri_geojson["features"]:
        nome = feat["properties"].get("layer", "Sconosciuto")
        folium.GeoJson(
            feat,
            name=f"Quartiere: {nome}",
            tooltip=nome,
            style_function=lambda f: {
                "fillColor": "#cccccc",
                "color": "#666666",
                "weight": 1,
                "fillOpacity": 0.1
            }
        ).add_to(m)

    # raccogli info fermate
    stop_info = {}
    for rid in selected_routes:
        color = route_colors[rid]
        tr = trips[trips["route_id"] == rid]

        # disegna percorso
        for sid in tr["shape_id"].unique():
            pts = shapes[shapes["shape_id"] == sid].sort_values("sequence")
            folium.PolyLine(
                list(zip(pts["lat"], pts["lon"])),
                color=color, weight=5, opacity=0.8,
                name=f"Linea {rid}"
            ).add_to(m)

    # raccogli fermate
    tids = tr["trip_id"].unique()
    stops_on = (stop_times[stop_times["trip_id"].isin(tids)]
                .merge(stops, on="stop_id", how="left"))
    for _, r in stops_on.iterrows():
        sid2 = r["stop_id"]
        info = stop_info.setdefault(sid2, {
            "name":   r["stop_name"],
            "lat":    r["stop_lat"],
            "lon":    r["stop_lon"],
            "routes": set()
        })
        # invece di r["route_id"], uso direttamente rid
        info["routes"].add(rid)

    # aggiungi marker fermate
    for sid2, info in stop_info.items():
        routes_here = info["routes"] & set(selected_routes)
        if not routes_here:
            continue
        popup = f"<b>{info['name']}</b><br>Linee: {', '.join(map(str, sorted(routes_here)))}"
        folium.Marker(
            [info["lat"], info["lon"]],
            popup=popup,
            icon=folium.Icon(color="gray", icon="bus", prefix="fa")
        ).add_to(m)

    # layer e line control
    folium.LayerControl(collapsed=True).add_to(m)

    # render mappa
    st.markdown("### Mappa del servizio")
    st_folium(m, height=800, use_container_width=True)

else:
    st.info("Seleziona almeno una linea dalla sidebar per visualizzare il percorso.")
