
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
from folium.features import CustomIcon

st.set_page_config(layout="wide")

st.image("Logo_Conerobus.png", width=250)
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

# ----------------------------
# Caricamento dati
# ----------------------------
@st.cache_data
def load_data():
    stops = pd.read_csv("stops.txt")
    trips = pd.read_csv("trips.txt")
    stop_times = pd.read_csv("stop_times.txt")
    routes = pd.read_csv("routes.txt")
    shapes = pd.read_csv("shapes.txt", header=None, skiprows=1,
                         names=["shape_id", "lat", "lon", "sequence", "shape_dist_traveled"])
    shapes["sequence"] = shapes["sequence"].astype(int)
    return stops, trips, stop_times, routes, shapes

stops, trips, stop_times, routes, shapes = load_data()

# ----------------------------
# Generazione colori per route_id
# ----------------------------
color_list = ["red", "blue", "green", "orange", "purple", "pink", "cadetblue", "darkred", "gray", "beige", "black", "navy"]
route_ids = sorted(trips["route_id"].unique())
route_colors = {rid: color_list[i % len(color_list)] for i, rid in enumerate(route_ids)}

# ----------------------------
# Stato sessione per toggle
# ----------------------------
for rid in route_ids:
    if f"toggle_{rid}" not in st.session_state:
        st.session_state[f"toggle_{rid}"] = False

# ----------------------------
# Creazione UI legenda linee
# ----------------------------
st.markdown("### Legenda linee")
legend_cols = st.columns(len(route_ids))

for i, rid in enumerate(route_ids):
    route_name = routes[routes["route_id"] == rid]["route_long_name"].values[0]
    active = st.session_state[f"toggle_{rid}"]
    btn_color = route_colors[rid] if active else "#ccc"
    btn_text_color = "white" if active else "black"

    with legend_cols[i]:
        if st.button(rid, key=f"btn_{rid}"):
            st.session_state[f"toggle_{rid}"] = not st.session_state[f"toggle_{rid}"]

        st.markdown(
            f"<div style='background-color:{btn_color};color:{btn_text_color};"
            f"padding:0.4rem 0.7rem;border-radius:5px;font-weight:bold;text-align:center;'>"
            f"{route_name}</div>",
            unsafe_allow_html=True
        )

# ----------------------------
# Linee attive
# ----------------------------
active_routes = [rid for rid in route_ids if st.session_state[f"toggle_{rid}"]]

# ----------------------------
# Creazione mappa
# ----------------------------
center_lat = stops["stop_lat"].mean()
center_lon = stops["stop_lon"].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

stop_info = {}

for route_id in active_routes:
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
logo_path = "01-CONEROBUS1-removebg-preview.png"
for sid, info in stop_info.items():
    active_rts = [r for r in info["routes"] if r in active_routes]
    if not active_rts:
        continue

    times_by_route = {r: [time_to_seconds(t) for t in info["routes"][r]] for r in active_rts}
    popup_lines = [f"<b>{info['stop_name']}</b><br><br>"]
    is_interchange = False

    for r in active_rts:
        display_times = []
        for t in sorted(info["routes"][r]):
            sec = time_to_seconds(t)
            has_match = any(abs(sec - sec2) <= 300 for r2 in active_rts if r2 != r for sec2 in times_by_route[r2])
            ft = format_time_str(t)
            if has_match:
                display_times.append(f"<u>{ft}</u>")
                is_interchange = True
            else:
                display_times.append(ft)
        popup_lines.append(f"<b style='color:{route_colors.get(r)};'>{r}</b>: {' '.join(display_times)}<br><br>")

    if is_interchange:
        popup_lines.insert(1, "<i style='color:grey;'>Fermata di interscambio</i><br><br>")

    popup_text = "".join(popup_lines)
    marker_icon = folium.Icon(color="orange", icon="exchange-alt", prefix="fa") if is_interchange else CustomIcon(logo_path, icon_size=(30, 30))
    folium.Marker([info["lat"], info["lon"]], popup=folium.Popup(popup_text, max_width=300), icon=marker_icon).add_to(m)

# ----------------------------
# Visualizzazione mappa
# ----------------------------
st.markdown("### Mappa del servizio")
st_folium(m, use_container_width=True, height=1000)
