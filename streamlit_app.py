import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.features import CustomIcon
from datetime import datetime

st.set_page_config(layout="wide")

st.image("Logo_Conerobus.png", width=250)
st.title("Servizio Urbano Jesi – Conerobus")

st.markdown("""
Questa applicazione consente di esplorare le linee del trasporto pubblico urbano di Jesi fornite da **Conerobus**.

- Clicca sulle caselle colorate per attivare/disattivare una linea.
- Le fermate evidenziate in **arancione** rappresentano punti di interscambio tra diverse linee.
- Passa il cursore sopra un pulsante per vedere la descrizione della linea.
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
# UI - Selezione linee via HTML+CSS
# ----------------------------
st.markdown("### Legenda linee")
all_route_ids = sorted(trips["route_id"].unique())
route_colors_raw = routes.set_index("route_id")["route_color"].to_dict()
route_names = routes.set_index("route_id")["route_long_name"].to_dict()

if "active_routes" not in st.session_state:
    st.session_state.active_routes = set()

def toggle_route(route_id):
    if route_id in st.session_state.active_routes:
        st.session_state.active_routes.remove(route_id)
    else:
        st.session_state.active_routes.add(route_id)

col_count = 5
cols = st.columns(col_count)

for idx, route_id in enumerate(all_route_ids):
    col = cols[idx % col_count]
    color = "#" + route_colors_raw.get(route_id, "777777")
    active = route_id in st.session_state.active_routes
    bg_color = color if active else "#e0e0e0"
    text_color = "white" if active else "black"
    tooltip = route_names.get(route_id, "")

    button_html = f"""
    <div title='{tooltip}'>
        <form action='' method='post'>
            <button name='route' value='{route_id}' style='
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                margin: 4px;
                cursor: pointer;
                font-weight: bold;
                width: 100%;
            '>{route_id}</button>
        </form>
    </div>
    """
    col.markdown(button_html, unsafe_allow_html=True)

if "route" in st.query_params:
    toggle_route(st.query_params["route"])

# ----------------------------
# Inizializza mappa
# ----------------------------
center_lat = stops["stop_lat"].mean()
center_lon = stops["stop_lon"].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

# ----------------------------
# Colori & fermate
# ----------------------------
route_colors = {r: "#" + route_colors_raw.get(r, "000000") for r in all_route_ids}
stop_info = {}
logo_path = "01-CONEROBUS1-removebg-preview.png"

for route_id in st.session_state.active_routes:
    color = route_colors.get(route_id, "#000000")
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
        if route_id not in stop_info[sid]["routes"]:
            stop_info[sid]["routes"][route_id] = []
        stop_info[sid]["routes"][route_id].append(row["arrival_time"])

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
    marker_icon = folium.Icon(color="orange", icon="exchange-alt", prefix="fa") if is_interchange else CustomIcon(logo_path, icon_size=(30, 30))

    folium.Marker(
        location=[info["lat"], info["lon"]],
        popup=folium.Popup(popup_text, max_width=300),
        icon=marker_icon
    ).add_to(m)

    plotted_stops.add(sid)

# ----------------------------
# Visualizzazione mappa
# ----------------------------
st.markdown("### Mappa del servizio")
st_folium(m, use_container_width=True, height=1000)
