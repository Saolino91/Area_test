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
        Esplora il trasporto pubblico urbano di Jesi:
        - Scegli le linee nella **sidebar**.
        - Attiva/disattiva quartieri e linee con il **Layer Control** (in alto a destra).
        - Apri la **Legenda linee** quando serve.
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

# ----------------- SELEZIONE LINEE (SIDEBAR) -----------------
route_ids = sorted(trips["route_id"].unique())
selected_routes = st.sidebar.multiselect(
    "Seleziona linee 🚍",
    options=route_ids,
    default=[],
    format_func=lambda x: f"Linea {x}"
)

# ----------------- COSTRUZIONE MAPPA -----------------
if selected_routes:
    # Centro mappa
    center = [stops["stop_lat"].mean(), stops["stop_lon"].mean()]
    m = folium.Map(location=center, zoom_start=13)

    # Quartieri come layer GeoJSON
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

    # Prepara colori per le route
    if "route_colors" not in st.session_state:
        palette = ["red","blue","green","orange","purple","pink",
                   "cadetblue","darkred","darkgreen","black"]
        st.session_state.route_colors = {
            rid: palette[i % len(palette)]
            for i, rid in enumerate(route_ids)
        }
    route_colors = st.session_state.route_colors

    # Raccogli dati per fermate
    stop_info = {}
    for rid in selected_routes:
        color = route_colors[rid]
        tr = trips[trips["route_id"] == rid]
        # Disegna polilinee
        for sid in tr["shape_id"].unique():
            pts = shapes[shapes["shape_id"] == sid].sort_values("sequence")
            folium.PolyLine(
                list(zip(pts["lat"], pts["lon"])),
                color=color, weight=4, opacity=0.8,
                name=f"Linea {rid}"
            ).add_to(m)
        # Raccogli fermate
        tids = tr["trip_id"].unique()
        stops_on = stop_times[stop_times["trip_id"].isin(tids)].merge(stops, on="stop_id")
        for _, r in stops_on.iterrows():
            sid = r["stop_id"]
            info = stop_info.setdefault(sid, {
                "name": r["stop_name"],
                "lat": r["stop_lat"],
                "lon": r["stop_lon"],
                "routes": set()
            })
            info["routes"].add(r["route_id"])

    # Aggiungi marker fermate
    for sid, info in stop_info.items():
        routes_here = info["routes"] & set(selected_routes)
        if not routes_here:
            continue
        popup = f"<b>{info['name']}</b><br>Linee: {', '.join(map(str, sorted(routes_here)))}"
        folium.Marker(
            [info["lat"], info["lon"]],
            popup=popup,
            icon=folium.Icon(color="gray", icon="bus", prefix="fa")
        ).add_to(m)

    # Layer control (collapsed per mobile)
    folium.LayerControl(collapsed=True).add_to(m)

    # Mostra mappa
    st.markdown("### Mappa del servizio")
    st_folium(m, height=700, use_container_width=True)

    # Legenda linee in expander
    with st.expander("👉 Legenda linee", expanded=False):
        for rid in selected_routes:
            name = routes.loc[routes["route_id"] == rid, "route_long_name"].iloc[0]
            col = route_colors[rid]
            st.markdown(
                f"- <span style='background:{col};padding:0.2em 0.5em;"
                f"border-radius:3px;color:white'>Linea {rid}</span>  {name}",
                unsafe_allow_html=True
            )

else:
    st.info("Seleziona linee dalla sidebar per visualizzare il percorso.")
