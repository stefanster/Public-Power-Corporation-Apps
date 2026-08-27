"""Aegean Fuel Command v2.1 — single-file Streamlit application.

This build is designed to work in both environments:

* Local/PyCharm: run ``python main.py`` or press Run. If required packages are
  missing, they are installed into the active interpreter and this file is
  relaunched through Streamlit.
* Streamlit Community Cloud: choose ``main.py`` as the entrypoint. The script
  detects that it is already executing inside Streamlit and does not spawn a
  second server process.

All demonstration fleet, station, inventory, demand, availability-calendar,
and routing data are generated inside this file.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys


# ---------------------------------------------------------------------------
# Local launcher / cloud-safe runtime detection
# ---------------------------------------------------------------------------
_REQUIRED_PACKAGES = {
    "streamlit": "streamlit==1.62.0",
    "pandas": "pandas>=2.2,<3",
    "numpy": "numpy>=1.26,<3",
    "plotly": "plotly>=5.24,<7",
    "pydeck": "pydeck>=0.9,<1",
}


def _running_inside_streamlit() -> bool:
    """Return True only when Streamlit is currently executing this script."""
    if importlib.util.find_spec("streamlit") is None:
        return False
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        try:
            return get_script_run_ctx(suppress_warning=True) is not None
        except TypeError:
            # Compatibility fallback for older Streamlit versions.
            return get_script_run_ctx() is not None
    except Exception:
        return False


def _install_missing_packages() -> None:
    missing = [
        requirement
        for module, requirement in _REQUIRED_PACKAGES.items()
        if importlib.util.find_spec(module) is None
    ]
    if not missing:
        return
    print("Installing missing packages into the active Python interpreter:")
    print("  " + " ".join(missing))
    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])


def _launch_streamlit() -> int:
    this_file = str(Path(__file__).resolve())
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        this_file,
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
    ]
    print("Launching Aegean Fuel Command in your browser...")
    return subprocess.call(command)


# PyCharm executes the file as ordinary Python. Community Cloud and
# ``streamlit run main.py`` execute it with an active Streamlit script context.
if not _running_inside_streamlit():
    _install_missing_packages()
    raise SystemExit(_launch_streamlit())


# ---------------------------------------------------------------------------
# Actual Streamlit application starts here
# ---------------------------------------------------------------------------
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math
from typing import Dict, List, Tuple

APP_VERSION = "2.1"

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

# -----------------------------
# App configuration
# -----------------------------
st.set_page_config(
    page_title="Aegean Fuel Command v2.1",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .stApp {
        background:
          radial-gradient(circle at 15% 0%, rgba(29, 78, 216, 0.10), transparent 28%),
          radial-gradient(circle at 100% 20%, rgba(14, 165, 233, 0.08), transparent 25%),
          #07111f;
        color: #e7eef8;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1627 0%, #0c1d31 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.16);
    }
    [data-testid="stHeader"] { background: rgba(7,17,31,0.80); }
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
    h1, h2, h3 { color: #f8fbff; letter-spacing: -0.02em; }
    p, label, .stMarkdown { color: #cad6e4; }
    .hero {
        padding: 1.25rem 1.35rem;
        border: 1px solid rgba(125, 211, 252, 0.15);
        border-radius: 22px;
        background: linear-gradient(135deg, rgba(15, 42, 73, 0.96), rgba(9, 27, 47, 0.92));
        box-shadow: 0 20px 60px rgba(0,0,0,0.20);
        margin-bottom: 1rem;
    }
    .eyebrow { color:#7dd3fc; font-size:0.78rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }
    .hero-title { font-size:2rem; font-weight:800; color:#ffffff; margin:.18rem 0 .3rem 0; }
    .hero-sub { color:#a8bad0; max-width:920px; line-height:1.55; }
    .card {
        border: 1px solid rgba(148, 163, 184, 0.15);
        background: linear-gradient(180deg, rgba(15, 31, 52, 0.95), rgba(10, 24, 42, 0.95));
        border-radius: 18px;
        padding: 1rem 1rem .9rem 1rem;
        min-height: 122px;
        box-shadow: 0 12px 30px rgba(0,0,0,.13);
    }
    .card-label { color:#8ea4bd; font-size:.78rem; font-weight:650; text-transform:uppercase; letter-spacing:.08em; }
    .card-value { color:#ffffff; font-size:1.72rem; font-weight:800; margin-top:.18rem; }
    .card-foot { color:#88a1bb; font-size:.82rem; margin-top:.22rem; }
    .pill-good, .pill-warn, .pill-bad, .pill-info {
        display:inline-block; padding:.22rem .52rem; border-radius:999px; font-size:.75rem; font-weight:700;
    }
    .pill-good { background:rgba(34,197,94,.14); color:#86efac; border:1px solid rgba(34,197,94,.25); }
    .pill-warn { background:rgba(245,158,11,.14); color:#fcd34d; border:1px solid rgba(245,158,11,.25); }
    .pill-bad { background:rgba(239,68,68,.14); color:#fca5a5; border:1px solid rgba(239,68,68,.25); }
    .pill-info { background:rgba(56,189,248,.14); color:#7dd3fc; border:1px solid rgba(56,189,248,.25); }
    div[data-testid="stDataFrame"] { border:1px solid rgba(148,163,184,.12); border-radius:16px; overflow:hidden; }
    div[data-testid="stMetric"] {
        background: rgba(12, 29, 49, .86); border:1px solid rgba(148,163,184,.14); padding: .75rem;
        border-radius: 16px;
    }
    .section-note { color:#8198b3; font-size:.88rem; margin-top:-.35rem; margin-bottom:.7rem; }
    .small { color:#8297b0; font-size:.78rem; }
    .risk-row { padding:.72rem .85rem; border-radius:14px; background:rgba(14,29,49,.75); border:1px solid rgba(148,163,184,.10); margin-bottom:.5rem; }
    .stTabs [data-baseweb="tab-list"] { gap:.25rem; }
    .stTabs [data-baseweb="tab"] { height:46px; border-radius:12px; padding:0 16px; background:#0c1c30; }
    .stTabs [aria-selected="true"] { background:#153355; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# -----------------------------
# Data model and synthetic data
# -----------------------------
HUB = {"name": "Lavrio Hub", "lat": 37.7149, "lon": 24.0565}

STATIONS = pd.DataFrame(
    [
        ["Sifnos", 36.9740, 24.7020, 3400, 1220, 92],
        ["Milos", 36.7226, 24.4443, 4300, 1510, 118],
        ["Paros", 37.0856, 25.1482, 5100, 1920, 142],
        ["Santorini", 36.3932, 25.4615, 6300, 2360, 176],
        ["Limnos", 39.9239, 25.2370, 4700, 1160, 108],
    ],
    columns=["station", "lat", "lon", "tank_capacity_t", "current_stock_t", "base_daily_t"],
)

FLEET = pd.DataFrame(
    [
        ["PPC Star Delos", 1800, 13.5, 150, 100],
        ["PPC Star Naxos", 2500, 12.8, 210, 100],
        ["PPC Star Chios", 3200, 14.2, 250, 100],
    ],
    columns=["ship", "capacity_t", "speed_kn", "bunker_reserve_t", "availability"],
)


@st.cache_data(show_spinner=False)
def generate_consumption_history(days: int = 180, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end = pd.Timestamp(date.today()) - pd.Timedelta(days=1)
    dates = pd.date_range(end=end, periods=days, freq="D")
    rows: List[Dict] = []

    for _, s in STATIONS.iterrows():
        for d in dates:
            doy = d.dayofyear
            # Summer tourism peak + weekly operations pattern + random noise.
            seasonal = 1.0 + 0.26 * math.sin(2 * math.pi * (doy - 170) / 365.25)
            summer_boost = 1.15 if d.month in (6, 7, 8) else 1.0
            weekly = 1.04 if d.dayofweek in (4, 5, 6) else 0.98
            noise = rng.normal(1.0, 0.075)
            value = max(20, s.base_daily_t * seasonal * summer_boost * weekly * noise)
            rows.append({"date": d, "station": s.station, "consumption_t": round(value, 1)})
    return pd.DataFrame(rows)


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_km = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    km = 2 * r_km * math.asin(math.sqrt(a))
    return km / 1.852


def build_station_snapshot(history: pd.DataFrame, target_days: int, safety_days: int) -> pd.DataFrame:
    recent = (
        history.sort_values("date")
        .groupby("station")
        .tail(21)
        .copy()
    )
    stats = (
        recent.groupby("station")["consumption_t"]
        .agg(forecast_daily_t="mean", demand_std_t="std")
        .reset_index()
    )
    df = STATIONS.merge(stats, on="station", how="left")
    df["forecast_daily_t"] = df["forecast_daily_t"].round(1)
    df["days_cover"] = (df["current_stock_t"] / df["forecast_daily_t"]).round(1)
    df["safety_stock_t"] = (df["forecast_daily_t"] * safety_days).round(0)
    df["target_stock_t"] = np.minimum(df["tank_capacity_t"], df["forecast_daily_t"] * target_days).round(0)
    df["delivery_need_t"] = np.maximum(0, df["target_stock_t"] - df["current_stock_t"]).round(0)
    df["distance_nm"] = df.apply(lambda r: haversine_nm(HUB["lat"], HUB["lon"], r.lat, r.lon), axis=1).round(1)
    df["risk"] = pd.cut(
        df["days_cover"],
        bins=[-np.inf, safety_days, safety_days + 4, np.inf],
        labels=["Critical", "Watch", "Healthy"],
        right=False,
    )
    return df


def _ship_key(ship: str) -> str:
    return ship.lower().replace(" ", "_")


def init_ship_availability() -> None:
    """Create persistent calendar state for each vessel."""
    today = date.today()
    default_end = today + timedelta(days=30)
    for ship in FLEET["ship"]:
        key = _ship_key(ship)
        st.session_state.setdefault(f"active_{key}", True)
        st.session_state.setdefault(f"availability_{key}", (today, default_end))


def get_ship_availability() -> Dict[str, Dict]:
    """Read the vessel calendar controls from Streamlit session state."""
    result: Dict[str, Dict] = {}
    today = date.today()
    for ship in FLEET["ship"]:
        key = _ship_key(ship)
        active = bool(st.session_state.get(f"active_{key}", True))
        value = st.session_state.get(f"availability_{key}", (today, today + timedelta(days=30)))
        if isinstance(value, (tuple, list)):
            if len(value) >= 2:
                start_d, end_d = value[0], value[1]
            elif len(value) == 1:
                start_d = end_d = value[0]
            else:
                start_d, end_d = today, today + timedelta(days=30)
        else:
            start_d = end_d = value
        if pd.Timestamp(end_d) < pd.Timestamp(start_d):
            start_d, end_d = end_d, start_d
        result[ship] = {"active": active, "start": pd.Timestamp(start_d), "end": pd.Timestamp(end_d)}
    return result


def _distance_between(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    return haversine_nm(a_lat, a_lon, b_lat, b_lon)


def plan_voyages(
    snapshot: pd.DataFrame,
    planning_days: int,
    target_days: int,
    safety_days: int,
    port_hours: float,
    weather_delay_pct: float,
    availability: Dict[str, Dict],
    max_stops: int = 3,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Build multi-island voyages using inventory urgency and geographic proximity.

    Each voyage starts and ends in Lavrio. A vessel may call at multiple islands
    before returning, subject to cargo capacity, planning horizon, and its
    user-selected availability calendar.
    """
    needs = snapshot.set_index("station")["delivery_need_t"].astype(float).to_dict()
    covers = snapshot.set_index("station")["days_cover"].astype(float).to_dict()
    forecast = snapshot.set_index("station")["forecast_daily_t"].astype(float).to_dict()
    current_stock = snapshot.set_index("station")["current_stock_t"].astype(float).to_dict()
    station_lookup = snapshot.set_index("station")[["lat", "lon"]].to_dict("index")
    delivered_before = {s: 0.0 for s in needs}

    today_ts = pd.Timestamp(date.today())
    horizon = today_ts + pd.Timedelta(days=planning_days, hours=23)
    ship_state: Dict[str, Dict] = {}
    for i, row in FLEET.iterrows():
        cal = availability[row.ship]
        start_ts = max(today_ts + pd.Timedelta(hours=6 + i * 2), cal["start"] + pd.Timedelta(hours=6))
        end_ts = cal["end"] + pd.Timedelta(hours=23, minutes=59)
        ship_state[row.ship] = {
            "available": start_ts,
            "available_until": end_ts,
            "capacity": float(row.capacity_t),
            "speed": float(row.speed_kn),
            "active": bool(cal["active"]),
        }

    voyage_rows: List[Dict] = []
    stop_rows: List[Dict] = []
    trip_id = 1

    def urgency_score(station: str) -> float:
        urgency = max(0.0, safety_days + 5 - covers[station])
        normalized_need = needs[station] / max(float(FLEET.capacity_t.max()), 1.0)
        return urgency * 2.5 + normalized_need

    for _ in range(60):
        remaining = [s for s, n in needs.items() if n > 50]
        if not remaining:
            break

        eligible_ships = [
            ship for ship, state in ship_state.items()
            if state["active"] and state["available"] <= min(horizon, state["available_until"])
        ]
        if not eligible_ships:
            break

        ship = min(eligible_ships, key=lambda x: ship_state[x]["available"])
        state = ship_state[ship]
        dispatch = state["available"]
        cargo_remaining = state["capacity"]
        route_stations: List[str] = []
        route_deliveries: List[float] = []

        current_lat, current_lon = HUB["lat"], HUB["lon"]
        candidates = remaining.copy()
        while candidates and cargo_remaining > 50 and len(route_stations) < max_stops:
            if not route_stations:
                station = max(candidates, key=urgency_score)
            else:
                def multi_stop_score(station_name: str) -> float:
                    loc = station_lookup[station_name]
                    leg = _distance_between(current_lat, current_lon, loc["lat"], loc["lon"])
                    return urgency_score(station_name) - 0.020 * leg
                station = max(candidates, key=multi_stop_score)

            cargo = min(cargo_remaining, needs[station])
            if cargo <= 50:
                candidates.remove(station)
                continue
            route_stations.append(station)
            route_deliveries.append(cargo)
            cargo_remaining -= cargo
            loc = station_lookup[station]
            current_lat, current_lon = loc["lat"], loc["lon"]
            candidates = [s for s in candidates if s != station and needs[s] > 50]

        if not route_stations:
            state["available"] = state["available_until"] + pd.Timedelta(days=1)
            continue

        voyage = f"V{trip_id:02d}"
        cursor = dispatch
        previous_lat, previous_lon = HUB["lat"], HUB["lon"]
        cumulative_nm = 0.0
        temp_stop_rows: List[Dict] = []

        for stop_no, (station, cargo) in enumerate(zip(route_stations, route_deliveries), start=1):
            loc = station_lookup[station]
            leg_nm = _distance_between(previous_lat, previous_lon, loc["lat"], loc["lon"])
            travel_h = leg_nm / state["speed"] * (1 + weather_delay_pct / 100)
            eta = cursor + pd.Timedelta(hours=travel_h)
            depart_stop = eta + pd.Timedelta(hours=port_hours)
            cumulative_nm += leg_nm

            days_to_eta = max(0.0, (eta - today_ts).total_seconds() / 86400)
            projected_stock = max(
                0.0,
                current_stock[station] + delivered_before[station] - forecast[station] * days_to_eta,
            )
            projected_cover = projected_stock / forecast[station] if forecast[station] else 0.0

            temp_stop_rows.append({
                "voyage": voyage,
                "ship": ship,
                "stop": stop_no,
                "station": station,
                "cargo_t": round(cargo),
                "eta": eta,
                "depart": depart_stop,
                "leg_nm": round(leg_nm, 1),
                "cumulative_nm": round(cumulative_nm, 1),
                "arrival_cover_days": round(projected_cover, 1),
            })
            cursor = depart_stop
            previous_lat, previous_lon = loc["lat"], loc["lon"]

        return_leg_nm = _distance_between(previous_lat, previous_lon, HUB["lat"], HUB["lon"])
        cumulative_nm += return_leg_nm
        return_h = return_leg_nm / state["speed"] * (1 + weather_delay_pct / 100)
        ret = cursor + pd.Timedelta(hours=return_h)

        # Reject any voyage that would finish after the vessel's selected window.
        if ret > state["available_until"]:
            state["available"] = state["available_until"] + pd.Timedelta(days=1)
            continue

        total_cargo = float(sum(route_deliveries))
        route_text = "Lavrio → " + " → ".join(route_stations) + " → Lavrio"
        voyage_rows.append({
            "voyage": voyage,
            "ship": ship,
            "route": route_text,
            "stops": len(route_stations),
            "cargo_t": round(total_cargo),
            "capacity_t": round(state["capacity"]),
            "utilization_pct": round(total_cargo / state["capacity"] * 100, 1),
            "dispatch": dispatch,
            "return": ret,
            "distance_nm": round(cumulative_nm, 1),
            "duration_h": round((ret - dispatch).total_seconds() / 3600, 1),
            "priority": "Urgent" if any(covers[s] < safety_days for s in route_stations) else "Planned",
        })
        stop_rows.extend(temp_stop_rows)

        for station, cargo in zip(route_stations, route_deliveries):
            needs[station] -= cargo
            delivered_before[station] += cargo
        state["available"] = ret + pd.Timedelta(hours=3)
        trip_id += 1

    return pd.DataFrame(voyage_rows), pd.DataFrame(stop_rows)


SHIP_COLORS = {
    "PPC Star Delos": [56, 189, 248, 225],
    "PPC Star Naxos": [34, 197, 94, 225],
    "PPC Star Chios": [245, 158, 11, 225],
}


def render_voyage_map(
    voyages: pd.DataFrame,
    stops: pd.DataFrame,
    selected_voyages: List[str] | None = None,
    height: int = 500,
) -> None:
    """Draw complete Lavrio-islands-Lavrio paths with vessel labels."""
    point_rows = [{"name": HUB["name"], "lat": HUB["lat"], "lon": HUB["lon"], "kind": "Hub", "size": 1000}]
    for _, r in snapshot.iterrows():
        point_rows.append({"name": r.station, "lat": r.lat, "lon": r.lon, "kind": "Station", "size": 650})
    points = pd.DataFrame(point_rows)

    path_rows: List[Dict] = []
    label_rows: List[Dict] = []
    if not voyages.empty and not stops.empty:
        subset = voyages if not selected_voyages else voyages[voyages["voyage"].isin(selected_voyages)]
        lookup = snapshot.set_index("station")[["lat", "lon"]].to_dict("index")
        for _, v in subset.iterrows():
            v_stops = stops[stops["voyage"] == v.voyage].sort_values("stop")
            coords = [[HUB["lon"], HUB["lat"]]]
            for _, s in v_stops.iterrows():
                loc = lookup[s.station]
                coords.append([loc["lon"], loc["lat"]])
            coords.append([HUB["lon"], HUB["lat"]])
            color = SHIP_COLORS.get(v.ship, [125, 211, 252, 225])
            path_rows.append({"path": coords, "color": color, "label": f"{v.voyage} · {v.ship}", "route": v.route})

            # Place the label roughly halfway through the outward/multi-stop route.
            mid = coords[max(1, min(len(coords) - 2, len(coords) // 2))]
            label_rows.append({"lon": mid[0], "lat": mid[1], "label": f"{v.voyage} · {v.ship}", "color": color})

    layers = [
        pdk.Layer(
            "ScatterplotLayer", points, get_position="[lon, lat]", get_radius="size",
            radius_min_pixels=6, radius_max_pixels=13,
            get_fill_color="[56, 189, 248, 220]", get_line_color="[255,255,255,160]",
            line_width_min_pixels=1, stroked=True, pickable=True,
        ),
        pdk.Layer(
            "TextLayer", points, get_position="[lon, lat]", get_text="name",
            get_size=13, get_color="[232,240,248,235]", get_pixel_offset="[0, -18]",
            get_text_anchor="'middle'", pickable=False,
        ),
    ]
    if path_rows:
        layers.insert(0, pdk.Layer(
            "PathLayer", pd.DataFrame(path_rows), get_path="path", get_color="color",
            width_min_pixels=3, get_width=4, pickable=True,
        ))
        layers.append(pdk.Layer(
            "TextLayer", pd.DataFrame(label_rows), get_position="[lon, lat]", get_text="label",
            get_size=14, get_color="color", get_pixel_offset="[0, 18]",
            get_text_anchor="'middle'", pickable=True,
        ))

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=37.65, longitude=24.65, zoom=5.5, pitch=18),
        tooltip={"text": "{name}{label}\n{route}"},
        map_style=None,
    )
    st.pydeck_chart(deck, width="stretch", height=height)

def status_pill(risk: str) -> str:
    cls = {"Healthy": "pill-good", "Watch": "pill-warn", "Critical": "pill-bad"}.get(risk, "pill-info")
    return f'<span class="{cls}">{risk}</span>'


def kpi_card(label: str, value: str, foot: str) -> None:
    st.markdown(
        f"<div class='card'><div class='card-label'>{label}</div><div class='card-value'>{value}</div><div class='card-foot'>{foot}</div></div>",
        unsafe_allow_html=True,
    )


# -----------------------------
# Sidebar controls
# -----------------------------
history = generate_consumption_history()

with st.sidebar:
    st.markdown(f"### ⚓ Aegean Fuel Command · v{APP_VERSION}")
    st.caption("Fleet dispatch & island inventory control")
    st.divider()
    st.markdown("**Planning controls**")
    planning_days = st.slider("Planning horizon", 5, 30, 14, 1, format="%d days")
    safety_days = st.slider("Safety-stock threshold", 3, 12, 7, 1, format="%d days")
    target_days = st.slider("Target stock cover", 10, 30, 18, 1, format="%d days")
    port_hours = st.slider("Port + handling time", 2.0, 14.0, 7.0, 0.5, format="%.1f h")
    weather_delay_pct = st.slider("Weather delay factor", 0, 35, 10, 5, format="%d%%")
    max_stops = st.slider("Maximum island stops / voyage", 1, 5, 3, 1)
    st.divider()
    st.markdown("**Scenario**")
    demand_surge = st.slider("Demand multiplier", 0.80, 1.35, 1.00, 0.05)
    st.caption("Use this to stress-test tourism peaks or outages.")

# Apply scenario multiplier to the history rather than to source assumptions.
scenario_history = history.copy()
scenario_history["consumption_t"] *= demand_surge
snapshot = build_station_snapshot(scenario_history, target_days, safety_days)
init_ship_availability()
ship_availability = get_ship_availability()
voyages, voyage_stops = plan_voyages(
    snapshot, planning_days, target_days, safety_days, port_hours, weather_delay_pct,
    ship_availability, max_stops=max_stops,
)

# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Supply chain control tower · Greece · v2.0</div>
      <div class="hero-title">Fuel delivery orchestration for island power stations</div>
      <div class="hero-sub">A decision-support prototype for monitoring fuel reserves, forecasting consumption, prioritizing island replenishment, and dispatching a three-vessel PPC fleet from Lavrio, including multi-island voyages and vessel availability calendars.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

critical_count = int((snapshot["risk"] == "Critical").sum())
total_need = float(snapshot["delivery_need_t"].sum())
fleet_capacity = int(FLEET["capacity_t"].sum())
planned_t = int(voyages["cargo_t"].sum()) if not voyages.empty else 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Stations at risk", str(critical_count), "Below the configured safety-stock threshold")
with c2:
    kpi_card("Replenishment need", f"{total_need:,.0f} t", f"Target: {target_days} days of stock cover")
with c3:
    kpi_card("Fleet capacity", f"{fleet_capacity:,} t", "PPC Star Delos · Naxos · Chios")
with c4:
    kpi_card("Planned cargo", f"{planned_t:,} t", f"Within the next {planning_days} days")

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Command Center", "Inventory & Demand", "Data & Availability", "Dispatch Planner", "Scenario Lab"]
)

with tab1:
    left, right = st.columns([1.45, 1])
    with left:
        st.subheader("Voyage network")
        st.markdown('<div class="section-note">Every planned voyage is drawn as Lavrio → one or more islands → Lavrio. Route labels identify the assigned PPC vessel.</div>', unsafe_allow_html=True)
        render_voyage_map(voyages, voyage_stops, height=500)
        if not voyages.empty:
            legend_cols = st.columns(3)
            for col, ship in zip(legend_cols, FLEET["ship"]):
                with col:
                    active = ship_availability[ship]["active"]
                    st.caption(f"{'●' if active else '○'} {ship}")

    with right:
        st.subheader("Risk queue")
        st.markdown('<div class="section-note">Stations sorted by projected days of cover.</div>', unsafe_allow_html=True)
        for _, r in snapshot.sort_values("days_cover").iterrows():
            st.markdown(
                f"""
                <div class="risk-row">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:.75rem;">
                      <div><b style="color:#f8fbff">{r.station}</b><div class="small">{r.current_stock_t:,.0f} t on hand · {r.forecast_daily_t:,.0f} t/day forecast</div></div>
                      <div style="text-align:right"><b style="color:#fff">{r.days_cover:.1f} days</b><br>{status_pill(str(r.risk))}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.subheader("Next recommended voyages")
    st.markdown('<div class="section-note">Multi-stop dispatch recommendation based on inventory urgency, geographic proximity, vessel capacity, vessel calendar, speed, and handling time.</div>', unsafe_allow_html=True)
    if voyages.empty:
        st.warning("No feasible voyage is available under the current demand, inventory, and ship-calendar settings.")
    else:
        shown = voyages.head(8).copy()
        shown["dispatch"] = shown["dispatch"].dt.strftime("%d %b · %H:%M")
        shown["return"] = shown["return"].dt.strftime("%d %b · %H:%M")
        st.dataframe(
            shown[["voyage", "ship", "route", "stops", "cargo_t", "utilization_pct", "dispatch", "return", "priority"]],
            width="stretch", hide_index=True,
            column_config={
                "cargo_t": st.column_config.NumberColumn("Cargo", format="%d t"),
                "utilization_pct": st.column_config.ProgressColumn("Capacity used", min_value=0, max_value=100, format="%.0f%%"),
            },
        )

with tab2:
    st.subheader("Inventory position")
    st.markdown('<div class="section-note">Current stock, target stock, and safety stock by island.</div>', unsafe_allow_html=True)
    inv = snapshot.melt(
        id_vars=["station"],
        value_vars=["current_stock_t", "safety_stock_t", "target_stock_t"],
        var_name="measure",
        value_name="tonnes",
    )
    inv["measure"] = inv["measure"].map(
        {"current_stock_t": "Current", "safety_stock_t": "Safety stock", "target_stock_t": "Target"}
    )
    fig = px.bar(inv, x="station", y="tonnes", color="measure", barmode="group", height=390)
    fig.update_layout(
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#cbd5e1",
        legend_title_text="",
        xaxis_title="",
        yaxis_title="Tonnes",
    )
    st.plotly_chart(fig, width='stretch')

    st.subheader("Historical daily consumption")
    selected = st.multiselect("Stations", STATIONS.station.tolist(), default=STATIONS.station.tolist())
    hist_filter = scenario_history[scenario_history.station.isin(selected)]
    fig2 = px.line(hist_filter, x="date", y="consumption_t", color="station", height=420)
    fig2.update_layout(
        margin=dict(l=10, r=10, t=15, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#cbd5e1",
        legend_title_text="",
        xaxis_title="",
        yaxis_title="Daily consumption (t)",
    )
    st.plotly_chart(fig2, width='stretch')

    table = snapshot[["station", "current_stock_t", "forecast_daily_t", "days_cover", "delivery_need_t", "distance_nm", "risk"]].copy()
    st.dataframe(
        table,
        width='stretch',
        hide_index=True,
        column_config={
            "station": "Station",
            "current_stock_t": st.column_config.NumberColumn("Current stock", format="%d t"),
            "forecast_daily_t": st.column_config.NumberColumn("Forecast/day", format="%.1f t"),
            "days_cover": st.column_config.ProgressColumn("Days cover", min_value=0, max_value=max(30, float(table.days_cover.max())), format="%.1f d"),
            "delivery_need_t": st.column_config.NumberColumn("Need", format="%d t"),
            "distance_nm": st.column_config.NumberColumn("From Lavrio", format="%.1f nm"),
            "risk": "Risk",
        },
    )

with tab3:
    st.subheader("Station master data")
    st.markdown('<div class="section-note">Hypothetical power-station and storage assumptions used by the planning model.</div>', unsafe_allow_html=True)
    station_view = STATIONS.copy()
    station_view["distance_from_lavrio_nm"] = station_view.apply(
        lambda r: haversine_nm(HUB["lat"], HUB["lon"], r.lat, r.lon), axis=1
    ).round(1)
    st.dataframe(
        station_view, width="stretch", hide_index=True,
        column_config={
            "station": "Station",
            "lat": st.column_config.NumberColumn("Latitude", format="%.4f"),
            "lon": st.column_config.NumberColumn("Longitude", format="%.4f"),
            "tank_capacity_t": st.column_config.NumberColumn("Tank capacity", format="%d t"),
            "current_stock_t": st.column_config.NumberColumn("Current stock", format="%d t"),
            "base_daily_t": st.column_config.NumberColumn("Base demand/day", format="%d t"),
            "distance_from_lavrio_nm": st.column_config.NumberColumn("From Lavrio", format="%.1f nm"),
        },
    )

    st.divider()
    st.subheader("Fleet master data")
    fleet_view = FLEET.copy()
    fleet_view["nominal_range_nm"] = ((fleet_view["bunker_reserve_t"] / 5.5) * fleet_view["speed_kn"]).round(0)
    st.dataframe(
        fleet_view, width="stretch", hide_index=True,
        column_config={
            "ship": "Vessel",
            "capacity_t": st.column_config.NumberColumn("Cargo capacity", format="%d t"),
            "speed_kn": st.column_config.NumberColumn("Service speed", format="%.1f kn"),
            "bunker_reserve_t": st.column_config.NumberColumn("Ship fuel reserve", format="%d t"),
            "availability": st.column_config.ProgressColumn("Nominal availability", min_value=0, max_value=100, format="%.0f%%"),
            "nominal_range_nm": st.column_config.NumberColumn("Illustrative range", format="%d nm"),
        },
    )

    st.divider()
    st.subheader("Ship availability calendar")
    st.markdown('<div class="section-note">Select whether each vessel is available and the exact date range in which the planner may dispatch it. Changes recalculate the voyage plan on the next Streamlit rerun.</div>', unsafe_allow_html=True)

    cal_cols = st.columns(3)
    for col, ship in zip(cal_cols, FLEET["ship"]):
        key = _ship_key(ship)
        with col:
            st.markdown(f"**{ship}**")
            st.toggle("Available for planning", key=f"active_{key}")
            st.date_input(
                "Available date range",
                key=f"availability_{key}",
                min_value=date.today() - timedelta(days=7),
                max_value=date.today() + timedelta(days=120),
                format="DD/MM/YYYY",
            )
            cal = get_ship_availability()[ship]
            if cal["active"]:
                st.caption(f"Planner window: {cal['start'].strftime('%d %b %Y')} → {cal['end'].strftime('%d %b %Y')}")
            else:
                st.caption("Excluded from dispatch planning")

    avail_rows = []
    for ship, cal in get_ship_availability().items():
        if cal["active"]:
            avail_rows.append({"ship": ship, "start": cal["start"], "end": cal["end"] + pd.Timedelta(days=1)})
    if avail_rows:
        avail_df = pd.DataFrame(avail_rows)
        avfig = px.timeline(avail_df, x_start="start", x_end="end", y="ship", color="ship", height=300)
        avfig.update_yaxes(autorange="reversed")
        avfig.add_vline(x=pd.Timestamp(date.today()), line_dash="dot", opacity=.5)
        avfig.update_layout(
            margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", font_color="#cbd5e1", legend_title_text="",
            xaxis_title="Dispatchable calendar", yaxis_title="", showlegend=False,
        )
        st.plotly_chart(avfig, width="stretch")
    else:
        st.warning("All vessels are currently excluded from planning.")

with tab4:
    st.subheader("Multi-island dispatch planner")
    st.markdown('<div class="section-note">Each voyage starts at Lavrio, may call at several islands, and returns to Lavrio. The first stop is selected mainly by stock urgency; later stops balance urgency with geographic proximity.</div>', unsafe_allow_html=True)
    if voyages.empty:
        st.info("Nothing feasible to dispatch under the current planning assumptions and ship calendars.")
    else:
        plan_table = voyages.copy()
        for col in ["dispatch", "return"]:
            plan_table[col] = plan_table[col].dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(plan_table, width="stretch", hide_index=True)

        st.subheader("Voyage map")
        selected_voyage = st.selectbox(
            "Inspect a voyage",
            voyages["voyage"].tolist(),
            format_func=lambda v: f"{v} · {voyages.loc[voyages.voyage == v, 'ship'].iloc[0]} · {voyages.loc[voyages.voyage == v, 'route'].iloc[0]}",
        )
        render_voyage_map(voyages, voyage_stops, selected_voyages=[selected_voyage], height=520)

        vrow = voyages[voyages.voyage == selected_voyage].iloc[0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Vessel", vrow.ship)
        m2.metric("Cargo", f"{vrow.cargo_t:,.0f} t")
        m3.metric("Route distance", f"{vrow.distance_nm:,.0f} nm")
        m4.metric("Voyage duration", f"{vrow.duration_h:.1f} h")

        st.markdown("**Island calls and delivery quantities**")
        detail = voyage_stops[voyage_stops.voyage == selected_voyage].copy()
        detail["eta"] = detail["eta"].dt.strftime("%d %b %Y · %H:%M")
        detail["depart"] = detail["depart"].dt.strftime("%d %b %Y · %H:%M")
        st.dataframe(
            detail[["stop", "station", "cargo_t", "eta", "depart", "leg_nm", "arrival_cover_days"]],
            width="stretch", hide_index=True,
            column_config={"cargo_t": st.column_config.NumberColumn("Delivery", format="%d t")},
        )

        gantt = voyages.copy()
        fig3 = px.timeline(gantt, x_start="dispatch", x_end="return", y="ship", color="ship", hover_data=["route", "cargo_t", "voyage"], height=390)
        fig3.update_yaxes(autorange="reversed")
        fig3.update_layout(
            margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", font_color="#cbd5e1", legend_title_text="",
            xaxis_title="Vessel schedule", yaxis_title="", showlegend=False,
        )
        st.plotly_chart(fig3, width="stretch")

        by_dest = voyage_stops.groupby("station", as_index=False)["cargo_t"].sum()
        fig4 = px.bar(by_dest, x="station", y="cargo_t", text="cargo_t", height=340)
        fig4.update_traces(texttemplate="%{text:,.0f} t", textposition="outside")
        fig4.update_layout(
            margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", font_color="#cbd5e1", xaxis_title="",
            yaxis_title="Planned cargo (t)",
        )
        st.plotly_chart(fig4, width="stretch")

with tab5:
    st.subheader("Scenario lab")
    st.markdown('<div class="section-note">Stress-test the network by changing demand, safety stock, handling time, weather delay, maximum island calls, and planning horizon in the sidebar.</div>', unsafe_allow_html=True)

    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("Demand scenario", f"{demand_surge:.0%}", delta=f"{(demand_surge-1):+.0%} vs baseline")
    with s2:
        st.metric("Lowest stock cover", f"{snapshot.days_cover.min():.1f} days")
    with s3:
        utilization = planned_t / max(fleet_capacity, 1)
        st.metric("Cargo / one fleet lift", f"{utilization:.1f}×")

    # Stock-cover projection with no further deliveries: useful to visualize urgency.
    projection_days = min(planning_days, 30)
    proj_rows = []
    for _, r in snapshot.iterrows():
        for d in range(projection_days + 1):
            stock = max(0, r.current_stock_t - r.forecast_daily_t * d)
            proj_rows.append({"day": d, "station": r.station, "stock_t": stock, "safety_t": r.safety_stock_t})
    proj = pd.DataFrame(proj_rows)
    fig5 = px.line(proj, x="day", y="stock_t", color="station", height=430)
    for _, r in snapshot.iterrows():
        fig5.add_trace(
            go.Scatter(
                x=[0, projection_days], y=[r.safety_stock_t, r.safety_stock_t],
                mode="lines", line=dict(width=1, dash="dot"),
                showlegend=False, hoverinfo="skip", opacity=.35,
            )
        )
    fig5.update_layout(
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#cbd5e1",
        xaxis_title="Days from today", yaxis_title="Projected stock without deliveries (t)", legend_title_text="",
    )
    st.plotly_chart(fig5, width='stretch')

st.divider()
st.caption(
    f"Aegean Fuel Command v{APP_VERSION} · Prototype note: all vessel, inventory, capacity, consumption, travel-time, and handling data are hypothetical. Straight-line nautical distance is used for demonstration; production use should incorporate navigational routing, port windows, weather, berth constraints, ship compatibility, costs, and regulatory requirements."
)
