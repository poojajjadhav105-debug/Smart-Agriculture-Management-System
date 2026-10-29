import sqlite3
from datetime import datetime, timedelta
import os

import pandas as pd
import plotly.express as px
import streamlit as st

# -------------------- App configuration --------------------
st.set_page_config(
    page_title="Smart Agriculture Management System",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = "agriculture_data.db"

# -------------------- Styling --------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

    /* Global light canvas: all default text is dark and readable */
    .stApp, [data-testid="stAppViewContainer"] { background: #F0F7FF !important; color: #111827 !important; }
    .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
    .stApp li, .stApp label, .stApp span, .stApp small,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li { color: #111827; }

    /* Dark sidebar: white text */
    [data-testid="stSidebar"] { background: #17324D !important; }
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }

    /* Dark hero/banner: white text */
    .hero { padding: 1.45rem 1.7rem; border-radius: 22px;
        background: linear-gradient(115deg, #17324D, #245B78);
        color: #FFFFFF !important; margin-bottom: 1.2rem; }
    .hero * { color: #FFFFFF !important; }
    .hero h1 { font-family: 'Manrope', sans-serif; font-size: 2rem; margin: 0 0 .35rem 0; }
    .hero p { color: #FFFFFF !important; margin: 0; }

    /* White cards: black/dark text */
    .metric-card { background: #FFFFFF !important; border: 1px solid #C9D9E8;
        border-radius: 18px; padding: 1rem 1.1rem;
        box-shadow: 0 4px 16px rgba(31, 65, 42, .05); min-height: 125px; }
    .metric-card * { color: #111827 !important; }
    .metric-label { color: #374151 !important; font-size: .88rem; font-weight: 600; }
    .metric-value { color: #111827 !important; font-family: 'Manrope', sans-serif;
        font-size: 1.8rem; font-weight: 800; margin: .3rem 0; }
    .metric-note { color: #4B5563 !important; font-size: .8rem; }
    .section-title { color: #17324D !important; font-family: 'Manrope', sans-serif;
        font-size: 1.25rem; font-weight: 800; margin: .6rem 0 .7rem 0; }
    .status-pill { padding: .24rem .6rem; border-radius: 999px; font-size: .8rem; font-weight: 700; }

    /* Streamlit metric boxes: force light background and dark labels/values,
       regardless of the user's browser theme. */
    div[data-testid="stMetric"], [data-testid="stMetric"] {
        background: #FFFFFF !important; border: 1px solid #C9D9E8 !important;
        border-radius: 16px; padding: 13px 16px;
    }
    [data-testid="stMetric"] * { color: #111827 !important; }
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { color: #374151 !important; }
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] * { color: #111827 !important; }

    /* Inputs and select boxes: white surface with dark text */
    .stTextInput input, .stNumberInput input, .stTextArea textarea,
    [data-baseweb="select"] > div, [data-baseweb="input"] > div {
        background: #FFFFFF !important; color: #111827 !important;
        border-color: #B8CADB !important;
    }
    [data-baseweb="select"] *, [data-baseweb="input"] * { color: #111827 !important; }
    .stButton button { color: #111827 !important; background: #DCEEFF !important; border: 1px solid #B8D4EE !important; }
    .stButton button p { color: #111827 !important; }
    .small-muted { color: #4B5563 !important; font-size: .86rem; }

    /* Alerts retain their own background but keep readable text */
    [data-testid="stAlert"] p, [data-testid="stAlert"] span { color: #111827 !important; }
    /* Tables */
    [data-testid="stDataFrame"], [data-testid="stTable"] { background: #FFFFFF !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- Database --------------------
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def initialize_database():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                soil_moisture REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                water_tank REAL NOT NULL,
                irrigation_on INTEGER NOT NULL,
                crop TEXT NOT NULL,
                field_name TEXT NOT NULL,
                mode TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS irrigation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT NOT NULL,
                soil_moisture REAL NOT NULL,
                mode TEXT NOT NULL
            )
            """
        )

def load_readings(limit=5000):
    with get_connection() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT ?",
            conn, params=(limit,)
        )
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp") if not df.empty else df

def save_reading(reading):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO sensor_readings
            (timestamp, soil_moisture, temperature, humidity, water_tank,
             irrigation_on, crop, field_name, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                reading["timestamp"].isoformat(sep=" ", timespec="seconds"),
                reading["soil_moisture"], reading["temperature"], reading["humidity"],
                reading["water_tank"], int(reading["irrigation_on"]), reading["crop"],
                reading["field_name"], reading["mode"]
            )
        )

def save_event(action, reason, moisture, mode):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO irrigation_events (timestamp, action, reason, soil_moisture, mode) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(sep=" ", timespec="seconds"), action, reason, moisture, mode)
        )

def load_events():
    with get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM irrigation_events ORDER BY timestamp DESC LIMIT 200", conn)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

initialize_database()

# -------------------- Demo data / session state --------------------
if "current_reading" not in st.session_state:
    st.session_state.current_reading = {
        "timestamp": datetime.now(),
        "soil_moisture": 34.0,
        "temperature": 29.0,
        "humidity": 62.0,
        "water_tank": 78.0,
        "irrigation_on": False,
        "crop": "Tomato",
        "field_name": "Field A",
        "mode": "Simulation",
    }
if "last_saved_minute" not in st.session_state:
    st.session_state.last_saved_minute = None
if "manual_override" not in st.session_state:
    st.session_state.manual_override = None

# -------------------- Sidebar controls --------------------
with st.sidebar:
    st.markdown("## 🌱 SmartAgri")
    st.caption("FARM INTELLIGENCE PLATFORM")
    page = st.radio(
        "NAVIGATION",
        ["Dashboard", "Live Monitoring", "Irrigation Control", "Crop Management",
         "Alerts & Notifications", "Data Analytics", "Historical Records", "Reports & Export", "Settings"],
        label_visibility="visible",
    )
    st.markdown("---")
    st.markdown("### ⚙️ Farm setup")
    field_name = st.text_input("Field name", value=st.session_state.current_reading["field_name"])
    crop = st.selectbox(
        "Crop type",
        ["Tomato", "Rice", "Wheat", "Maize", "Cotton", "Sugarcane", "Other"],
        index=["Tomato", "Rice", "Wheat", "Maize", "Cotton", "Sugarcane", "Other"].index(
            st.session_state.current_reading["crop"]
        ) if st.session_state.current_reading["crop"] in ["Tomato", "Rice", "Wheat", "Maize", "Cotton", "Sugarcane", "Other"] else 0,
    )
    st.markdown("---")
    st.markdown("**System status**")
    st.success("Dashboard online")
    st.caption("Demo mode · Sensor data is simulated")

# -------------------- Settings and thresholds --------------------
if "min_moisture" not in st.session_state:
    st.session_state.min_moisture = 30
if "target_moisture" not in st.session_state:
    st.session_state.target_moisture = 45
if "max_temperature" not in st.session_state:
    st.session_state.max_temperature = 38
if "min_temperature" not in st.session_state:
    st.session_state.min_temperature = 10
if "min_tank" not in st.session_state:
    st.session_state.min_tank = 15
if "auto_irrigation" not in st.session_state:
    st.session_state.auto_irrigation = True

# -------------------- Sensor simulation and irrigation logic --------------------
def simulate_new_reading():
    import random
    old = st.session_state.current_reading
    # Gentle realistic variation for demo purposes
    moisture = max(8.0, min(90.0, old["soil_moisture"] + random.uniform(-4.0, 2.0)))
    temperature = max(8.0, min(44.0, old["temperature"] + random.uniform(-1.2, 1.2)))
    humidity = max(20.0, min(98.0, old["humidity"] + random.uniform(-3.0, 3.0)))
    tank = max(0.0, min(100.0, old["water_tank"] - (1.0 if old["irrigation_on"] else 0.0)))
    pump = bool(old["irrigation_on"])

    if st.session_state.auto_irrigation:
        if moisture < st.session_state.min_moisture and tank >= st.session_state.min_tank:
            pump = True
        elif moisture >= st.session_state.target_moisture or tank < st.session_state.min_tank:
            pump = False

    if st.session_state.manual_override is not None:
        pump = st.session_state.manual_override

    if pump and tank >= st.session_state.min_tank:
        moisture = min(90.0, moisture + random.uniform(3.0, 6.0))
        tank = max(0.0, tank - random.uniform(1.0, 2.5))
    elif tank < st.session_state.min_tank:
        pump = False

    reading = {
        "timestamp": datetime.now(),
        "soil_moisture": round(moisture, 1),
        "temperature": round(temperature, 1),
        "humidity": round(humidity, 1),
        "water_tank": round(tank, 1),
        "irrigation_on": pump,
        "crop": crop,
        "field_name": field_name.strip() or "Field A",
        "mode": "Simulation",
    }
    previous_pump = old["irrigation_on"]
    if pump != previous_pump:
        action = "PUMP ON" if pump else "PUMP OFF"
        if pump:
            reason = "Soil moisture below threshold" if st.session_state.auto_irrigation else "Manual activation"
        else:
            reason = "Target moisture reached or water tank low" if st.session_state.auto_irrigation else "Manual deactivation"
        save_event(action, reason, reading["soil_moisture"], "Simulation")
    st.session_state.current_reading = reading
    st.session_state.manual_override = None
    save_reading(reading)
    st.session_state.last_saved_minute = datetime.now().strftime("%Y-%m-%d %H:%M")

def save_current_snapshot():
    reading = dict(st.session_state.current_reading)
    reading.update({"timestamp": datetime.now(), "crop": crop, "field_name": field_name.strip() or "Field A"})
    st.session_state.current_reading = reading
    save_reading(reading)
    st.session_state.last_saved_minute = datetime.now().strftime("%Y-%m-%d %H:%M")

# -------------------- Current readings --------------------
r = st.session_state.current_reading
r["crop"] = crop
r["field_name"] = field_name.strip() or "Field A"

# -------------------- Header --------------------
st.markdown(
    f"""
    <div class="hero">
      <h1>🌿 Smart Agriculture Management System</h1>
      <p>Welcome back! Monitor your farm, manage irrigation, and make data-driven decisions.</p>
      <p style="margin-top:12px;font-size:.82rem;">📍 {r['field_name']} &nbsp; • &nbsp; 🌾 {r['crop']} &nbsp; • &nbsp; 🕒 {datetime.now().strftime('%d %b %Y, %I:%M %p')}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------- Helper UI --------------------
def metric_card(label, value, note, icon):
    st.markdown(
        f"""<div class="metric-card">
        <div class="metric-label">{icon} &nbsp; {label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-note">{note}</div></div>""",
        unsafe_allow_html=True,
    )

def get_alerts(reading):
    alerts = []
    if reading["soil_moisture"] < st.session_state.min_moisture:
        alerts.append(("Critical" if reading["soil_moisture"] < st.session_state.min_moisture - 8 else "Warning",
                       "Low soil moisture", f"Soil moisture is {reading['soil_moisture']}%. Check irrigation and soil conditions."))
    if reading["soil_moisture"] > 75:
        alerts.append(("Warning", "High soil moisture", "Moisture is high. Check drainage and avoid overwatering."))
    if reading["temperature"] > st.session_state.max_temperature:
        alerts.append(("Warning", "High temperature", "Temperature is above your configured limit. Monitor crop stress."))
    if reading["temperature"] < st.session_state.min_temperature:
        alerts.append(("Warning", "Low temperature", "Temperature is below your configured limit. Check crop protection needs."))
    if reading["humidity"] > 90:
        alerts.append(("Warning", "High humidity", "High humidity can increase disease risk for some crops. Inspect plants."))
    if reading["water_tank"] < st.session_state.min_tank:
        alerts.append(("Critical", "Low water tank", "Water tank is low. Refill it before running irrigation."))
    return alerts

# -------------------- Page content --------------------
if page == "Dashboard":
    st.markdown('<div class="section-title">Farm overview</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]: metric_card("Soil Moisture", f"{r['soil_moisture']:.1f}%", "Current soil water level", "💧")
    with cols[1]: metric_card("Temperature", f"{r['temperature']:.1f}°C", "Ambient temperature", "🌡️")
    with cols[2]: metric_card("Humidity", f"{r['humidity']:.1f}%", "Relative air humidity", "☁️")
    with cols[3]: metric_card("Water Tank", f"{r['water_tank']:.1f}%", "Available water", "🚰")

    st.markdown("")
    left, right = st.columns([1.45, 1])
    with left:
        st.markdown('<div class="section-title">📈 Farm conditions</div>', unsafe_allow_html=True)
        history = load_readings()
        if history.empty:
            history = pd.DataFrame([{
                "timestamp": r["timestamp"], "soil_moisture": r["soil_moisture"],
                "temperature": r["temperature"], "humidity": r["humidity"], "water_tank": r["water_tank"]
            }])
        chart_df = history.tail(100).melt(
            id_vars="timestamp",
            value_vars=["soil_moisture", "temperature", "humidity"],
            var_name="Metric", value_name="Reading"
        )
        fig = px.line(chart_df, x="timestamp", y="Reading", color="Metric",
                      color_discrete_map={"soil_moisture": "#2f8f58", "temperature": "#e99b37", "humidity": "#4b8fce"})
        fig.update_layout(
            height=330, margin=dict(l=10, r=10, t=15, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
            legend_title_text="", font=dict(color="#405444"),
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="#edf1eb")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown('<div class="section-title">🚿 Irrigation status</div>', unsafe_allow_html=True)
        if r["irrigation_on"]:
            st.success("Pump is ON")
        else:
            st.info("Pump is OFF")
        st.progress(min(1.0, r["soil_moisture"] / 100))
        st.caption(f"Soil moisture: {r['soil_moisture']:.1f}%")
        st.caption(f"Automatic irrigation: {'Enabled' if st.session_state.auto_irrigation else 'Disabled'}")
        st.caption(f"Start threshold: {st.session_state.min_moisture}%")
        st.caption(f"Target moisture: {st.session_state.target_moisture}%")
        st.markdown('<div class="section-title">🔔 Latest alerts</div>', unsafe_allow_html=True)
        alerts = get_alerts(r)
        if alerts:
            for severity, title, message in alerts[:3]:
                if severity == "Critical":
                    st.error(f"**{title}** — {message}")
                else:
                    st.warning(f"**{title}** — {message}")
        else:
            st.success("All monitored conditions are within configured limits.")

    st.markdown('<div class="section-title">⚡ Quick actions</div>', unsafe_allow_html=True)
    q1, q2, q3 = st.columns(3)
    with q1:
        if st.button("🔄 Generate new sensor reading", use_container_width=True):
            simulate_new_reading()
            st.rerun()
    with q2:
        if st.button("💾 Save current snapshot", use_container_width=True):
            save_current_snapshot()
            st.success("Snapshot saved to local database.")
    with q3:
        if st.button("📊 View analytics", use_container_width=True):
            st.session_state["go_analytics"] = True
            st.info("Choose Data Analytics from the sidebar to explore trends.")

elif page == "Live Monitoring":
    st.markdown('<div class="section-title">📡 Live sensor monitoring</div>', unsafe_allow_html=True)
    st.info("Simulation mode: click the button to generate a new sample. Real-time hardware readings require an IoT connection.")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Soil moisture", f"{r['soil_moisture']:.1f}%", delta="Target " + str(st.session_state.target_moisture) + "%")
    with c2: st.metric("Temperature", f"{r['temperature']:.1f} °C")
    with c3: st.metric("Humidity", f"{r['humidity']:.1f}%")
    with c4: st.metric("Water tank", f"{r['water_tank']:.1f}%")
    st.markdown("#### Sensor status")
    status_cols = st.columns(3)
    for col, label, val, unit in [
        (status_cols[0], "Soil moisture sensor", r["soil_moisture"], "%"),
        (status_cols[1], "Temperature sensor", r["temperature"], "°C"),
        (status_cols[2], "Humidity sensor", r["humidity"], "%"),
    ]:
        with col:
            st.markdown(f"**{label}**")
            st.progress(max(0.0, min(1.0, val / (100 if unit == '%' else 50))))
            st.caption(f"Latest value: {val}{unit}")
    if st.button("🔄 Refresh simulated readings", type="primary"):
        simulate_new_reading()
        st.rerun()
    st.caption(f"Last reading: {r['timestamp'].strftime('%d %b %Y, %I:%M:%S %p')}")

elif page == "Irrigation Control":
    st.markdown('<div class="section-title">🚿 Irrigation control center</div>', unsafe_allow_html=True)
    st.warning("Safety note: these controls only simulate a pump. They do not operate physical hardware.")
    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### Current irrigation")
        st.metric("Pump status", "ON" if r["irrigation_on"] else "OFF")
        st.metric("Soil moisture", f"{r['soil_moisture']:.1f}%")
        st.metric("Water tank", f"{r['water_tank']:.1f}%")
        auto = st.toggle("Enable automatic irrigation", value=st.session_state.auto_irrigation)
        if auto != st.session_state.auto_irrigation:
            st.session_state.auto_irrigation = auto
            st.session_state.manual_override = None
            st.rerun()
        b1, b2 = st.columns(2)
        with b1:
            if st.button("▶ Turn pump ON", use_container_width=True, disabled=r["water_tank"] < st.session_state.min_tank):
                st.session_state.manual_override = True
                st.session_state.current_reading["irrigation_on"] = True
                save_event("PUMP ON", "Manual activation from control panel", r["soil_moisture"], "Simulation")
                st.success("Pump switched ON in simulation.")
                st.rerun()
        with b2:
            if st.button("■ Turn pump OFF", use_container_width=True):
                st.session_state.manual_override = False
                st.session_state.current_reading["irrigation_on"] = False
                save_event("PUMP OFF", "Manual deactivation from control panel", r["soil_moisture"], "Simulation")
                st.success("Pump switched OFF in simulation.")
                st.rerun()
    with right:
        st.markdown("#### Irrigation thresholds")
        min_m = st.slider("Start irrigation below soil moisture (%)", 5, 70, int(st.session_state.min_moisture))
        target_m = st.slider("Stop irrigation at soil moisture (%)", min_m + 1, 90, max(min_m + 1, int(st.session_state.target_moisture)))
        min_t = st.slider("Minimum safe water tank level (%)", 0, 50, int(st.session_state.min_tank))
        if st.button("Save irrigation settings", type="primary"):
            st.session_state.min_moisture = min_m
            st.session_state.target_moisture = target_m
            st.session_state.min_tank = min_t
            st.success("Irrigation thresholds updated.")
            st.rerun()
        st.caption("The simulated pump starts below the start threshold and stops at the target moisture or when the tank is too low.")
    events = load_events()
    st.markdown("#### Recent irrigation activity")
    if events.empty:
        st.caption("No irrigation events recorded yet.")
    else:
        st.dataframe(events.drop(columns=["id"]), use_container_width=True, hide_index=True)

elif page == "Crop Management":
    st.markdown('<div class="section-title">🌾 Crop management</div>', unsafe_allow_html=True)
    st.write("Manage the crop profile for the selected field. Thresholds are examples; adjust them to your crop variety, growth stage, soil type, and local agronomy advice.")
    a, b = st.columns(2)
    with a:
        st.markdown("#### Field profile")
        st.write(f"**Field:** {r['field_name']}")
        st.write(f"**Selected crop:** {r['crop']}")
        st.write(f"**Monitoring mode:** {r['mode']}")
        st.write(f"**Last update:** {r['timestamp'].strftime('%d %b %Y, %I:%M %p')}")
    with b:
        st.markdown("#### Current condition summary")
        if r["soil_moisture"] < st.session_state.min_moisture:
            st.warning("Soil moisture is below the configured irrigation threshold.")
        elif r["soil_moisture"] >= st.session_state.target_moisture:
            st.success("Soil moisture is at or above the target.")
        else:
            st.info("Soil moisture is between the start and target thresholds.")
        if r["temperature"] > st.session_state.max_temperature:
            st.warning("Temperature is above your configured limit.")
        else:
            st.success("Temperature is within the configured limit.")
    st.markdown("#### Crop monitoring notes")
    st.text_area("Notes for this field", placeholder="Record observations, growth stage, fertilizer applications, or field work...", key="crop_notes")
    st.caption("Crop-specific thresholds should be configured with local soil and crop requirements.")

elif page == "Alerts & Notifications":
    st.markdown('<div class="section-title">🔔 Alerts & notifications</div>', unsafe_allow_html=True)
    alerts = get_alerts(r)
    if not alerts:
        st.success("No active alerts. Current simulated readings are within configured limits.")
    else:
        st.write(f"{len(alerts)} active alert(s) based on the latest sensor readings.")
        for severity, title, message in alerts:
            if severity == "Critical":
                st.error(f"**{severity}: {title}**\n\n{message}")
            else:
                st.warning(f"**{severity}: {title}**\n\n{message}")
    st.markdown("#### Recent irrigation events")
    events = load_events()
    if events.empty:
        st.caption("No events have been recorded.")
    else:
        st.dataframe(events.drop(columns=["id"]), use_container_width=True, hide_index=True)
    if st.button("Refresh alerts"):
        st.rerun()

elif page == "Data Analytics":
    st.markdown('<div class="section-title">📊 Agricultural data analytics</div>', unsafe_allow_html=True)
    st.caption("Sensor readings chart")
    st.image(os.path.join(os.path.dirname(__file__), "assets", "sensor_readings_chart.png"), use_container_width=True)
    history = load_readings()
    if history.empty:
        st.info("No historical records yet. Generate a new reading from Dashboard or Live Monitoring.")
    else:
        date_col1, date_col2 = st.columns(2)
        min_date = history["timestamp"].min().date()
        max_date = history["timestamp"].max().date()
        with date_col1:
            start_date = st.date_input("From date", value=min_date, min_value=min_date, max_value=max_date)
        with date_col2:
            end_date = st.date_input("To date", value=max_date, min_value=min_date, max_value=max_date)
        filtered = history[
            (history["timestamp"].dt.date >= start_date) &
            (history["timestamp"].dt.date <= end_date)
        ]
        if filtered.empty:
            st.warning("No records in the selected date range.")
        else:
            k1, k2, k3 = st.columns(3)
            with k1: st.metric("Average soil moisture", f"{filtered['soil_moisture'].mean():.1f}%")
            with k2: st.metric("Average temperature", f"{filtered['temperature'].mean():.1f} °C")
            with k3: st.metric("Average humidity", f"{filtered['humidity'].mean():.1f}%")
            metrics = st.multiselect(
                "Choose metrics to chart",
                ["soil_moisture", "temperature", "humidity", "water_tank"],
                default=["soil_moisture", "temperature", "humidity"],
            )
            if metrics:
                long_df = filtered.melt(id_vars="timestamp", value_vars=metrics, var_name="Metric", value_name="Reading")
                fig = px.line(long_df, x="timestamp", y="Reading", color="Metric", markers=True)
                fig.update_layout(height=400, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
            st.markdown("#### Summary statistics")
            st.dataframe(filtered[["soil_moisture", "temperature", "humidity", "water_tank"]].describe().round(2),
                         use_container_width=True)

elif page == "Historical Records":
    st.markdown('<div class="section-title">🗂️ Historical sensor records</div>', unsafe_allow_html=True)
    history = load_readings()
    if history.empty:
        st.info("No records saved yet. Use “Generate new sensor reading” to start building your history.")
    else:
        st.caption(f"{len(history)} saved record(s) in the local SQLite database.")
        st.dataframe(history.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)
        if st.button("Generate and save a new reading"):
            simulate_new_reading()
            st.rerun()

elif page == "Reports & Export":
    st.markdown('<div class="section-title">📄 Reports & data export</div>', unsafe_allow_html=True)
    history = load_readings()
    if history.empty:
        st.info("No data available to export yet.")
    else:
        st.metric("Total saved readings", len(history))
        st.write("Download the stored sensor history as a CSV file for spreadsheets or further analysis.")
        export_df = history.drop(columns=["id"], errors="ignore")
        st.download_button(
            "⬇️ Download sensor history (CSV)",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name=f"smart_agriculture_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        events = load_events()
        if not events.empty:
            st.download_button(
                "⬇️ Download irrigation event history (CSV)",
                data=events.drop(columns=["id"], errors="ignore").to_csv(index=False).encode("utf-8"),
                file_name="irrigation_events.csv",
                mime="text/csv",
                use_container_width=True,
            )
        st.markdown("#### Latest readings")
        st.dataframe(history.sort_values("timestamp", ascending=False).head(20), use_container_width=True, hide_index=True)

elif page == "Settings":
    st.markdown('<div class="section-title">⚙️ System settings</div>', unsafe_allow_html=True)
    st.info("These settings apply to the demonstration dashboard. Hardware integration requires a separately configured IoT device and secure control interface.")
    with st.form("settings_form"):
        min_m = st.number_input("Low soil moisture alert / irrigation start (%)", 5, 70, int(st.session_state.min_moisture))
        target_m = st.number_input("Target soil moisture (%)", int(min_m) + 1, 90, max(int(min_m) + 1, int(st.session_state.target_moisture)))
        min_temp = st.number_input("Low temperature alert (°C)", -5.0, 25.0, float(st.session_state.min_temperature))
        max_temp = st.number_input("High temperature alert (°C)", 25.0, 55.0, float(st.session_state.max_temperature))
        min_tank = st.number_input("Low water tank alert (%)", 0, 50, int(st.session_state.min_tank))
        auto = st.checkbox("Enable automatic irrigation simulation", value=st.session_state.auto_irrigation)
        submitted = st.form_submit_button("Save settings", type="primary")
    if submitted:
        if target_m <= min_m:
            st.error("Target moisture must be greater than the irrigation start threshold.")
        elif max_temp <= min_temp:
            st.error("High temperature threshold must be greater than low temperature threshold.")
        else:
            st.session_state.min_moisture = int(min_m)
            st.session_state.target_moisture = int(target_m)
            st.session_state.min_temperature = float(min_temp)
            st.session_state.max_temperature = float(max_temp)
            st.session_state.min_tank = int(min_tank)
            st.session_state.auto_irrigation = auto
            st.success("Settings saved.")
            st.rerun()
    st.markdown("#### Database")
    st.write(f"Local database file: `{DB_PATH}`")
    st.caption("The database is created automatically in the folder from which Streamlit is launched.")

# -------------------- Footer --------------------
st.markdown("---")
st.markdown(
    '<p class="small-muted">🌱 Smart Agriculture Management System · Local demo edition · '
    'Simulated readings are for demonstration only and are not real sensor measurements.</p>',
    unsafe_allow_html=True,
)
