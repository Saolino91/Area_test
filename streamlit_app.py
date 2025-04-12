import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import st_folium
from datetime import datetime
from folium.features import CustomIcon

# ----------------- CONFIGURAZIONE PAGINA -----------------
st.set_page_config(layout="wide")

col1, col2 = st.columns([3, 2])
with col1:
    st.title("Servizio Urbano Jesi")
    st.markdown("""
        Questa applicazione consente di esplorare le linee del trasporto pubblico urbano di Jesi fornite da **Conerobus**.

        - Seleziona una o più linee cliccando sui rettangoli colorati.
        - Le fermate evidenziate in **arancione** rappresentano punti di interscambio tra diverse linee.
        - Puoi anche visualizzare i **quartieri della città** sulla mappa.
    """)
with col2:
    st.image("Logo_Conerobus.png", width=400)

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

@st.cache_data
def load_data():
    stops = pd.read_csv("stops.txt")
    trips = pd.read_csv("trips.txt")
    stop_times = pd.read_csv("stop_times.txt")
    shapes = pd.read_csv("shapes.txt", header=None, skiprows=1,
                         names=["shape_id", "lat", "lon", "sequence", "shape_dist_traveled"])
    shapes["sequence"] = shapes["sequence"].astype(int)
    routes = pd.read_csv("routes.txt")
    return stops, trips, stop_times, shapes, routes

stops, trips, stop_times, shapes, routes = load_data()

# ----------------- QUARTIERI -----------------
with open("quartieri_jesi.geojson", "r", encoding="utf-8") as f:
    quartieri_geojson = json.load(f)

quartieri_nomi = sorted(set(
    feature["properties"].get("layer", "Sconosciuto")
    for feature in quartieri_geojson["features"]
))

quartieri_selezionati = st.multiselect(
    "Seleziona i quartieri da visualizzare sulla mappa:",
    options=quartieri_nomi,
    default=quartieri_nomi
)

colori_quartieri = {
    "Smia - Zona Industriale": "orange",
    "Coppi - Giardini": "green",
    "Prato": "red",
    "Minonna": "blue",
    "Paradiso": "yellow",
    "San Francesco": "magenta",
    "Erbarella - San Pietro Martire": "teal",
    "San Giuseppe": "brown",
    "Centro Storico": "black",
    "Via Roma": "darkblue"
}

# ----------------- GESTIONE LINEE -----------------
route_ids = sorted(trips["route_id"].unique())

if "route_colors" not in st.session_state:
    st.session_state.route_colors = {}
    color_list = ["red", "blue", "green", "orange", "purple", "pink", "cadetblue", "darkred", "gray", "beige"]
    color_cycle = iter(color_list)
    for rid in route_ids:
        st.session_state.route_colors[rid] = next(color_cycle, "black")
route_colors = st.session_state.route_colors

if "selected_routes" not in st.session_state:
    st.session_state["selected_routes"] = []

st.markdown("### Seleziona le linee da visualizzare:")
cols = st.columns(6)
for idx, route_id in enumerate(route_ids):
    color = route_colors.get(route_id, "#888888")
    is_selected = route_id in st.session_state["selected_routes"]
    if cols[idx % 6].button(route_id, key=route_id):
        if is_selected:
            st.session_state["selected_routes"].remove(route_id)
        else:
            st.session_state["selected_routes"].append(route_id)
selected_routes = st.session_state["selected_routes"]

# ----------------- MAPPA -----------------
if selected_routes:
    coords_all = []
    center_lat = stops["stop_lat"].mean()
    center_lon = stops["stop_lon"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
    stop_info = {}

    # Aggiungi i poligoni dei quartieri
    for feature in quartieri_geojson["features"]:
        nome_q = feature["properties"].get("layer", "Sconosciuto")
        if nome_q in quartieri_selezionati:
            colore = colori_quartieri.get(nome_q, "#CCCCCC")
            folium.GeoJson(
                feature,
                name=nome_q,
                tooltip=folium.GeoJsonTooltip(fields=["layer"], aliases=["Quartiere"]),
                style_function=lambda f, colore=colore: {
                    "fillColor": colore,
                    "color": colore,
                    "weight": 2,
                    "fillOpacity": 0.2
                }
            ).add_to(m)

    for route_id in selected_routes:
        color = route_colors[route_id]
        trips_of_route = trips[trips["route_id"] == route_id]
        shape_ids = trips_of_route["shape_id"].unique()
        for shape_id in shape_ids:
            shape_pts = shapes[shapes["shape_id"] == shape_id].sort_values("sequence")
            coords = list(zip(shape_pts["lat"], shape_pts["lon"]))
            coords_all += coords
            folium.PolyLine(coords, color=color, weight=5, opacity=0.7).add_to(m)

        trip_ids = trips_of_route["trip_id"].unique()
        stops_line = stop_times[stop_times["trip_id"].isin(trip_ids)].merge(stops, on="stop_id", how="left")
        for _, row in stops_line.iterrows():
            sid = row["stop_id"]
            if sid not in stop_info:
                stop_info[sid] = {
                    "stop_name": row["stop_name"],
                    "lat": row["stop_lat"],
                    "lon": row["stop_lon"],
                    "routes": {}
                }
            stop_info[sid]["routes"].setdefault(route_id, []).append(row["arrival_time"])

    # Legenda
    st.markdown("### Legenda linee")
    legend_html = "<div style='display: flex; flex-wrap: wrap; gap: 1rem;'>"
    for route_id in selected_routes:
        color = route_colors.get(route_id, "#000000")
        route_info = routes[routes["route_id"] == route_id]
        route_name = route_info["route_long_name"].values[0] if not route_info.empty else ""
        legend_html += (
            f"<div style='display: flex; align-items: center; gap: 0.5rem;'>"
            f"<div style='background-color:{color}; padding: 0.4rem 0.7rem; color: white; border-radius: 5px; font-weight: bold;'>"
            f"{route_id}</div><span style='font-size: 0.9rem;'>{route_name}</span></div>"
        )
    legend_html += "</div>"
    st.markdown(legend_html, unsafe_allow_html=True)

    # Marker fermate
    logo_path = "01-CONEROBUS1-removebg-preview.png"
    plotted_stops = set()
    for sid, info in stop_info.items():
        if sid in plotted_stops:
            continue
        active_routes = [r for r in info["routes"] if r in selected_routes]
        if not active_routes:
            continue
        times_by_route = {r: [time_to_seconds(t) for t in info["routes"][r]] for r in active_routes}
        popup_lines = [f"<b>{info['stop_name']}</b><br><br>"]
        is_interchange = False
        for r in active_routes:
            display_times = []
            for t in sorted(info["routes"][r]):
                sec = time_to_seconds(t)
                has_match = any(abs(sec - sec2) <= 300 for r2 in active_routes if r2 != r for sec2 in times_by_route[r2])
                ft = format_time_str(t)
                if has_match:
                    display_times.append(f"<u>{ft}</u>")
                    is_interchange = True
                else:
                    display_times.append(ft)
            color = route_colors.get(r, "black")
            popup_lines.append(f"<b style='color:{color};'>{r}</b>: {' '.join(display_times)}<br><br>")
        if is_interchange:
            popup_lines.insert(1, "<i style='color:grey;'>Fermata di interscambio</i><br><br>")
        popup_text = "".join(popup_lines)
        icon = folium.Icon(color="orange", icon="exchange-alt", prefix="fa") if is_interchange else CustomIcon(logo_path, icon_size=(20, 20))
        folium.Marker(
            location=[info["lat"], info["lon"]],
            popup=folium.Popup(popup_text, max_width=300),
            icon=icon
        ).add_to(m)
        plotted_stops.add(sid)

    folium.LayerControl(collapsed=False).add_to(m)

    st.markdown("### Mappa del servizio")
    st_folium(m, use_container_width=True, height=1000)
