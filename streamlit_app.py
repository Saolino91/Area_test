import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import st_folium
from datetime import datetime
from folium.features import CustomIcon
from folium.plugins import PolyLineTextPath


# ----------------- CONFIGURAZIONE PAGINA -----------------
st.set_page_config(layout="wide")
col1, col2 = st.columns([3, 2])
with col1:
    st.title("Servizio Urbano Jesi")
    st.markdown("""
        Questa applicazione consente di esplorare le linee del trasporto pubblico urbano di Jesi fornite da **Conerobus**.

        - Seleziona una o più linee cliccando sui rettangoli colorati nella **sidebar**.
        - La legenda si attiva automaticamente quando selezioni le linee.
        - I quartieri sono già presenti in OpenStreetMap, non serve un filtro aggiuntivo qui.
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

# ----------------- COLORI QUARTIERI -----------------
colori_quartieri = {
    "Smia - Zona Industriale": "orange",
    "Coppi - Giardini": "green",
    "Prato": "red",
    "Minonna": "blue",
    "Paradiso": "yellow",
    "San Francesco": "magenta",
    "Erbarella - San Pierto Martire": "purple",
    "San Giuseppe": "brown",
    "Centro Storico": "black",
    "Via Roma": "darkblue"
}

# ----------------- GESTIONE LINEE IN SIDEBAR -----------------
route_ids = sorted(trips["route_id"].unique())

if "route_colors" not in st.session_state:
    color_list = [
        "red", "blue", "green", "orange", "purple", "pink",
        "cadetblue", "darkred", "darkgreen", "black"
    ]
    st.session_state.route_colors = {
        rid: color_list[i % len(color_list)]
        for i, rid in enumerate(route_ids)
    }
route_colors = st.session_state.route_colors

if "selected_routes" not in st.session_state:
    st.session_state.selected_routes = []

with st.sidebar:
    st.markdown("### Seleziona le linee da visualizzare:")
    btn_cols = st.columns(6)
    for idx, rid in enumerate(route_ids):
        col = btn_cols[idx % 6]
        selected = rid in st.session_state.selected_routes

        # se selezionata, aggiungo il checkmark
        label = f"{'✅ ' if selected else ''}{rid}"

        if col.button(
            label,
            key=f"btn_{rid}",
            help="Clicca per attivare/disattivare"
        ):
            if selected:
                st.session_state.selected_routes.remove(rid)
            else:
                st.session_state.selected_routes.append(rid)


    # Legenda attiva solo se ho almeno una linea selezionata
    if st.session_state.selected_routes:
        st.markdown("### Legenda linee")
        for rid in st.session_state.selected_routes:
            route_name = routes.loc[routes["route_id"] == rid, "route_long_name"].iloc[0]
            col = route_colors[rid]
            st.markdown(
                f"<span style='background:{col};"
                f"padding:0.3em 0.6em;border-radius:4px;"
                f"color:white;font-weight:bold'>Linea {rid}</span>  {route_name}",
                unsafe_allow_html=True
            )

selected_routes = st.session_state.selected_routes

# ----------------- MAPPA -----------------
if selected_routes:
    center_lat = stops["stop_lat"].mean()
    center_lon = stops["stop_lon"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
    stop_info = {}

    # Aggiungi tutti i quartieri (toggle via LayerControl in mappa)
    for feat in quartieri_geojson["features"]:
        nome_q = feat["properties"].get("layer", "Sconosciuto")
        colore = colori_quartieri.get(nome_q, "#CCCCCC")
        folium.GeoJson(
            feat,
            name=f"Quartiere: {nome_q}",
            tooltip=nome_q,
            style_function=lambda f, colore=colore: {
                "fillColor": colore,
                "color": colore,
                "weight": 2,
                "fillOpacity": 0.2
            }
        ).add_to(m)

    # Disegna le linee e raccogli le fermate
    for rid in selected_routes:
        color = route_colors[rid]
        tr = trips[trips["route_id"] == rid]

        # polilinee + frecce
        for sid in tr["shape_id"].unique():
            pts = shapes[shapes["shape_id"] == sid].sort_values("sequence")

            # disegno la polilinea
            line = folium.PolyLine(
                list(zip(pts["lat"], pts["lon"])),
                color=color, weight=5, opacity=0.7,
                name=f"Linea {rid}"
            ).add_to(m)

            # aggiungo le freccine lungo la linea per indicare il verso
            PolyLineTextPath(
                line,
                '   ›   ',         # il simbolo da ripetere
                repeat=True,       # ripeti fino alla fine
                offset=10,         # spostamento dal centro linea
                attributes={       # stile (dimensione/colori)
                    'fill': color,
                    'font-weight': 'bold',
                    'font-size': '16px'
                }
            ).add_to(m)

        # fermate
        tids = tr["trip_id"].unique()
        stops_on = (
            stop_times[stop_times["trip_id"].isin(tids)]
            .merge(stops, on="stop_id", how="left")
        )
        for _, row in stops_on.iterrows():
            sid2 = row["stop_id"]
            info = stop_info.setdefault(sid2, {
                "stop_name": row["stop_name"],
                "lat": row["stop_lat"],
                "lon": row["stop_lon"],
                "routes": {}
            })
            info["routes"].setdefault(rid, []).append(row["arrival_time"])


    # Popup e marker
    for sid2, info in stop_info.items():
        active = [r for r in info["routes"] if r in selected_routes]
        if not active:
            continue
        # costruisco popup
        popup_lines = [f"<b>{info['stop_name']}</b><br><br>"]
        is_interchange = False
        times_by_route = {r: [time_to_seconds(t) for t in info["routes"][r]] for r in active}
        for r in active:
            display = []
            for t in sorted(info["routes"][r]):
                sec = time_to_seconds(t)
                match = any(abs(sec - sec2) <= 300 for r2 in active if r2 != r for sec2 in times_by_route[r2])
                ft = format_time_str(t)
                if match:
                    display.append(f"<u>{ft}</u>")
                    is_interchange = True
                else:
                    display.append(ft)
            clr = route_colors.get(r, "black")
            popup_lines.append(f"<b style='color:{clr};'>{r}</b>: {' '.join(display)}<br><br>")
        if is_interchange:
            popup_lines.insert(1, "<i style='color:grey;'>Fermata di interscambio</i><br><br>")
        popup_html = "".join(popup_lines)

        icon = folium.Icon(color="orange", icon="exchange-alt", prefix="fa") if is_interchange else CustomIcon(
            "01-CONEROBUS1-removebg-preview.png", icon_size=(20,20)
        )
        folium.Marker(
            [info["lat"], info["lon"]],
            popup=folium.Popup(popup_html, max_width=300),
            icon=icon
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    st.markdown("### Mappa del servizio")
    st_folium(m, use_container_width=True, height=1000)

else:
    st.info("Seleziona almeno una linea dalla sidebar per visualizzare il percorso.")
