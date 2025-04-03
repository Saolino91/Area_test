import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
from folium.features import CustomIcon

# Configura la pagina
st.set_page_config(layout="wide")

# Logo e intestazione
col1, col2 = st.columns([1, 5])
with col1:
    st.image("Logo_Conerobus.png", width=100)
with col2:
    st.title("Servizio Urbano Jesi – Conerobus")
    st.markdown("""
    Questa applicazione consente di esplorare le linee del trasporto pubblico urbano di Jesi fornite da **Conerobus**.
    - Seleziona una o più linee cliccando sui riquadri colorati.
    - Le fermate evidenziate in **arancione** rappresentano punti di interscambio tra diverse linee.
    """)

# ----------------------------
# Funzioni di utilità
# ----------------------------
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
    routes = pd.read_csv("routes.txt")
    shapes["sequence"] = shapes["sequence"].astype(int)
    return stops, trips, stop_times, shapes, routes

stops, trips, stop_times, shapes, routes = load_data()

# ----------------------------
# Costruzione dei colori
# ----------------------------
color_list = ["red", "blue", "green", "orange", "purple", "pink", "cadetblue", "darkred", "gray", "beige"]
color_cycle = iter(color_list)
route_colors = {}

# UI: selezione da legenda
st.markdown("### Legenda linee")
if "active_routes" not in st.session_state:
    st.session_state.active_routes = []

legend_cols = st.columns(6)
unique_route_ids = trips["route_id"].unique()

for idx, route_id in enumerate(unique_route_ids):
    route_info = routes[routes["route_id"] == route_id]
    long_name = route_info["route_long_name"].values[0] if not route_info.empty else ""

    if route_id not in route_colors:
        route_colors[route_id] = next(color_cycle, "black")
    color = route_colors[route_id]

    is_active = route_id in st.session_state.active_routes
    btn_color = color if is_active else "#ccc"
    text_color = "white" if is_active else "black"

    if legend_cols[idx % 6].button(route_id, key=route_id,
                                   help=long_name,
                                   use_container_width=True):
        if route_id in st.session_state.active_routes:
            st.session_state.active_routes.remove(route_id)
        else:
            st.session_state.active_routes.append(route_id)

# ----------------------------
# Inizializza mappa
# ----------------------------
center_lat = stops["stop_lat"].mean()
center_lon = stops["stop_lon"].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

# ----------------------------
# Percorsi e fermate
# ----------------------------
stop_info = {}
logo_path = "01-CONEROBUS1-removebg-preview.png"

for route_id in st.session_state.active_routes:
    color = route_colors.get(route_id, "black")
    trips_of_route = trips[trips["route_id"] == route_id]
    shape_ids = trips_of_route["shape_id"].unique()

    for shape_id in shape_ids:
        shape_pts = shapes[shapes["shape_id"] == shape_id].sort_values("sequence")
        coords = list(zip(shape_pts["lat"], shape_pts["lon"]))
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

# ----------------------------
# Marker fermate
# ----------------------------
plotted_stops = set()

for sid, info in stop_info.items():
    if sid in plotted_stops:
        continue

    active_routes = [r for r in info["routes"] if r in st.session_state.active_routes]
    if not active_routes:
        continue

    times_by_route = {r: [time_to_seconds(t) for t in info["routes"][r]] for r in active_routes}
    popup_lines = [f"<b>{info['stop_name']}</b><br><br>"]
    is_interchange = False

    for r in active_routes:
        display_times = []
        for t in sorted(info["routes"][r]):
            sec = time_to_seconds(t)
            has_match = any(
                abs(sec - sec2) <= 300
                for r2 in active_routes if r2 != r
                for sec2 in times_by_route[r2]
            )
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
    icon = folium.Icon(color="orange", icon="exchange-alt", prefix="fa") if is_interchange else CustomIcon(logo_path, icon_size=(30, 30))

    folium.Marker(
        location=[info["lat"], info["lon"]],
        popup=folium.Popup(popup_text, max_width=300),
        icon=icon
    ).add_to(m)

    plotted_stops.add(sid)

# ----------------------------
# Mostra la mappa
# ----------------------------
st.markdown("### Mappa del servizio")
st_folium(m, use_container_width=True, height=1000)
