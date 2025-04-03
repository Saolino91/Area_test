
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime

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
    shapes = pd.read_csv("shapes.txt", header=None, skiprows=1,
                         names=["shape_id", "lat", "lon", "sequence", "shape_dist_traveled"])
    shapes["sequence"] = shapes["sequence"].astype(int)
    return stops, trips, stop_times, shapes

stops, trips, stop_times, shapes = load_data()

# ----------------------------
# UI - Selezione linee
# ----------------------------
route_ids = sorted(trips["route_id"].unique())
selected_routes = st.multiselect("Seleziona le linee da visualizzare", route_ids)

# ----------------------------
# Inizializza mappa
# ----------------------------
center_lat = stops["stop_lat"].mean()
center_lon = stops["stop_lon"].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

# ----------------------------
# Raccolta info fermate
# ----------------------------
stop_info = {}
route_colors = {}
color_list = ["red", "blue", "green", "orange", "purple", "pink", "cadetblue", "darkred", "gray", "beige"]
color_cycle = iter(color_list)

for route_id in selected_routes:
    if route_id not in route_colors:
        route_colors[route_id] = next(color_cycle, "black")

    color = route_colors[route_id]
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
# Inserimento fermate sulla mappa
# ----------------------------
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

    icon = folium.Icon(color="orange" if is_interchange else "blue", icon="bus", prefix="fa")
    folium.Marker(
        location=[info["lat"], info["lon"]],
        popup=folium.Popup(popup_text, max_width=300),
        icon=icon
    ).add_to(m)
    plotted_stops.add(sid)

# ----------------------------
# Visualizzazione mappa
# ----------------------------
st.markdown("### Mappa del servizio")
st_data = st_folium(m, width=1000, height=700)
