
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
from folium.features import CustomIcon

st.set_page_config(layout="wide")

# ----------------------------
# Logo e titolo
# ----------------------------
st.image("Logo_Conerobus.png", width=250)
st.title("Servizio Urbano Jesi – Conerobus")
st.markdown("""
Questa applicazione consente di esplorare le linee del trasporto pubblico urbano di Jesi fornite da **Conerobus**.

- Seleziona una o più linee cliccando sui riquadri colorati.
- Le fermate evidenziate in **arancione** rappresentano punti di interscambio tra diverse linee.
""")
# ----------------------------
# Funzioni
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
# Dati
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
    return stops, trips, stop_times, shapes, routes

stops, trips, stop_times, shapes, routes = load_data()

# ----------------------------
# Color setup
# ----------------------------
color_list = [
    "red", "blue", "green", "orange", "purple", "pink",
    "cadetblue", "darkred", "gray", "beige", "darkgreen", "lightblue"
]
color_cycle = iter(color_list)
route_colors = {}
for rid in sorted(trips["route_id"].unique()):
    route_colors[rid] = next(color_cycle, "black")

# ----------------------------
# Selezione linee via click
# ----------------------------
if "active_routes" not in st.session_state:
    st.session_state.active_routes = []

st.markdown("### Legenda linee")

legend_cols = st.columns(len(route_colors))

for i, (rid, color) in enumerate(route_colors.items()):
    r_name = routes[routes["route_id"] == rid]["route_long_name"]
    name = r_name.values[0] if not r_name.empty else ""

    active = rid in st.session_state.active_routes
    button_color = color if active else "#ccc"
    font_color = "white" if active else "black"

    if legend_cols[i].button(rid, key=f"btn_{rid}"):
        if active:
            st.session_state.active_routes.remove(rid)
        else:
            st.session_state.active_routes.append(rid)

    legend_cols[i].markdown(
        f"<span style='font-size: 0.8rem; color: {font_color}; background-color: {button_color}; "
        f"padding: 0.4rem 0.6rem; border-radius: 5px; font-weight: bold;'>{rid}</span><br>"
        f"<span style='font-size: 0.7rem;'>{name}</span>",
        unsafe_allow_html=True
    )

selected_routes = st.session_state.active_routes

# ----------------------------
# Mappa
# ----------------------------
m = folium.Map(location=[stops["stop_lat"].mean(), stops["stop_lon"].mean()], zoom_start=13)

stop_info = {}
for route_id in selected_routes:
    trips_of_route = trips[trips["route_id"] == route_id]
    shape_ids = trips_of_route["shape_id"].unique()
    color = route_colors.get(route_id, "black")

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
# Marker
# ----------------------------
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

    if is_interchange:
        marker_icon = folium.Icon(color="orange", icon="exchange-alt", prefix="fa")
    else:
        marker_icon = CustomIcon(logo_path, icon_size=(30, 30))

    folium.Marker(
        location=[info["lat"], info["lon"]],
        popup=folium.Popup(popup_text, max_width=300),
        icon=marker_icon
    ).add_to(m)
    plotted_stops.add(sid)

# ----------------------------
# Mostra mappa
# ----------------------------
st.markdown("### Mappa del servizio")
st_folium(m, use_container_width=True, height=1000)
