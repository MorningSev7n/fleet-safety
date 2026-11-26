
import base64
import io
import xml.etree.ElementTree as ET

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from db import ROOT, get_events, get_driving_events
from scoring import calculate_driver_scores, SEVERITY_DEDUCTIONS


# ============================================================
# 1. SETTINGS
# ============================================================

ATTENTION_SCORE = 75

SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH"]

SEVERITY_COLORS = {
    "LOW": "#42B883",
    "MEDIUM": "#E7A947",
    "HIGH": "#E35D5B",
}

WEBCAM_EVENT_COLORS = {
    "EYES_CLOSED": "#E35D5B",
    "YAWN": "#E7A947",
    "LOOK_AWAY": "#F08A4B",
    "PHONE": "#A875D8",
}

DRIVING_EVENT_COLORS = {
    "HARSH_BRAKING": "#E7A947",
    "HARSH_CORNERING": "#4DA3FF",
    "SPEEDING": "#E35D5B",
}

SCORE_COLORS = {
    "Excellent": "#42B883",
    "Good": "#4DA3FF",
    "Needs Improvement": "#E7A947",
    "Poor": "#E35D5B",
}

# measured_value means something different for each driving event.
DRIVING_UNITS = {
    "HARSH_BRAKING": "m/s²",
    "HARSH_CORNERING": "m/s²",
    "SPEEDING": "km/h",
}

WEBCAM_COLUMNS = [
    "id",
    "timestamp",
    "driver_id",
    "vehicle_id",
    "event_type",
    "duration_s",
    "severity",
    "snapshot",
]

DRIVING_COLUMNS = [
    "id",
    "timestamp",
    "driver_id",
    "vehicle_id",
    "event_type",
    "measured_value",
    "threshold_value",
    "unit",
    "severity",
]

# Friendly table headings. Exports keep the original column names.
COLUMN_LABELS = {
    "id": "ID",
    "timestamp": "Time",
    "driver_id": "Driver",
    "vehicle_id": "Vehicle",
    "event_type": "Event",
    "duration_s": "Duration (s)",
    "measured_value": "Measured",
    "threshold_value": "Limit",
    "unit": "Unit",
    "severity": "Severity",
    "snapshot": "Snapshot",
}

CHART_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "#1A202A",
    "plot_bgcolor": "#1A202A",
    "font": {"color": "#E5EAF0"},
    "title": {"font": {"size": 15}},
    "margin": {"l": 10, "r": 10, "t": 45, "b": 10},
    "height": 320,
}


# ============================================================
# 2. PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="Fleet Safety Dashboard",
    page_icon="🚗",
    layout="wide",
)

st.markdown(
    """
    <style>
        [data-testid="stMetric"] {
            background-color: #1A202A;
            border: 1px solid #2B3441;
            padding: 16px;
            border-radius: 12px;
        }

        [data-testid="stMetricLabel"] {
            color: #A6B0BE;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. LOAD DATA
# ============================================================

# No cache: the live sections reload this every 2 seconds.
def load_webcam_events():
    """Load webcam events and fix column types."""

    df = get_events()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    df["duration_s"] = pd.to_numeric(
        df["duration_s"],
        errors="coerce",
    )

    return df.dropna(subset=["timestamp"])


@st.cache_data(ttl=5)
def load_driving_events():
    """Load driving events, fix column types, and add units."""

    df = get_driving_events()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    df["measured_value"] = pd.to_numeric(
        df["measured_value"],
        errors="coerce",
    )

    df["threshold_value"] = pd.to_numeric(
        df["threshold_value"],
        errors="coerce",
    )

    df["unit"] = df["event_type"].map(DRIVING_UNITS)

    return df.dropna(subset=["timestamp"])


# ============================================================
# 4. FILTERS
# ============================================================

def show_filters(df, key):
    """
    Show driver, event type, and date filters.

    Returns the selected driver, event type,
    and the selected start and end dates.
    """

    drivers = sorted(df["driver_id"].unique().tolist())
    event_types = sorted(df["event_type"].unique().tolist())

    min_date = df["timestamp"].min().date()

    # Reach today, so new live events fit in the default range.
    max_date = max(df["timestamp"].max().date(), date.today())

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:

        driver = st.selectbox(
            "Driver",
            ["All drivers"] + drivers,
            key=f"{key}_driver",
        )

    with col2:

        event_type = st.selectbox(
            "Event type",
            ["All events"] + event_types,
            key=f"{key}_event",
        )

    with col3:

        dates = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key=f"{key}_dates",
        )

    # While a range is being picked, Streamlit
    # briefly returns only the start date.
    start_date = min_date
    end_date = max_date

    if len(dates) == 2:
        start_date, end_date = dates

    elif len(dates) == 1:
        start_date = dates[0]
        end_date = dates[0]

    return driver, event_type, start_date, end_date


def apply_filters(df, driver, event_type, start_date, end_date):
    """Keep only the rows that match the selected filters."""

    event_dates = df["timestamp"].dt.date

    filtered = df[
        (event_dates >= start_date)
        & (event_dates <= end_date)
    ]

    if driver != "All drivers":

        filtered = filtered[
            filtered["driver_id"] == driver
        ]

    if event_type != "All events":

        filtered = filtered[
            filtered["event_type"] == event_type
        ]

    return filtered


# ============================================================
# 5. CHART HELPERS
# ============================================================

def show_chart(fig, key):
    """Apply the shared dark style and display a chart."""

    fig.update_layout(**CHART_LAYOUT)

    st.plotly_chart(
        fig,
        width="stretch",
        key=key,
    )


def show_type_chart(df, colors, key):
    """Horizontal bar chart of events per event type."""

    counts = (
        df["event_type"]
        .value_counts()
        .rename_axis("Event")
        .reset_index(name="Events")
    )

    fig = px.bar(
        counts,
        x="Events",
        y="Event",
        orientation="h",
        color="Event",
        color_discrete_map=colors,
        text="Events",
        title="Events by type",
    )

    fig.update_layout(
        showlegend=False,
        yaxis={"categoryorder": "total ascending", "title": ""},
    )

    show_chart(fig, key)


def show_severity_chart(df, key):
    """Bar chart of events per severity, always LOW → HIGH."""

    counts = (
        df["severity"]
        .value_counts()
        .reindex(SEVERITY_ORDER, fill_value=0)
        .rename_axis("Severity")
        .reset_index(name="Events")
    )

    fig = px.bar(
        counts,
        x="Severity",
        y="Events",
        color="Severity",
        color_discrete_map=SEVERITY_COLORS,
        text="Events",
        title="Events by severity",
    )

    fig.update_layout(
        showlegend=False,
        xaxis={"title": ""},
    )

    show_chart(fig, key)


def show_daily_chart(df, key):
    """Bar chart of events per day."""

    counts = (
        df["timestamp"].dt.date
        .value_counts()
        .sort_index()
        .rename_axis("Date")
        .reset_index(name="Events")
    )

    fig = px.bar(
        counts,
        x="Date",
        y="Events",
        title="Events per day",
    )

    fig.update_traces(
        marker_color="#4DA3FF"
    )

    fig.update_layout(
        xaxis={"title": ""},
    )

    show_chart(fig, key)


# ============================================================
# 6. RECORDS AND EXPORT
# ============================================================

def to_xml(df):
    """Convert a table to XML, one <event> per row."""

    root = ET.Element("fleet_events")

    root.set("total_records", str(len(df)))

    for _, row in df.iterrows():

        event = ET.SubElement(root, "event")

        for column, value in row.items():

            element = ET.SubElement(event, column)

            if pd.isna(value):
                element.text = ""
            elif isinstance(value, pd.Timestamp):
                element.text = value.isoformat()
            else:
                element.text = str(value)

    ET.indent(root, space="    ")

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )


def to_xlsx(df):
    """Convert a table to an Excel file in memory."""

    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Events",
        )

    return buffer.getvalue()


def show_records(df, columns, file_name, key):
    """Show the filtered records and the four export buttons."""

    records = df[columns]

    st.markdown("#### 📋 Records")

    with st.expander(f"View {len(records):,} filtered records"):

        st.dataframe(
            records.rename(columns=COLUMN_LABELS),
            width="stretch",
            hide_index=True,
        )

    st.caption("Exports include only the records that match your filters.")

    exports = [
        ("📄 CSV", records.to_csv(index=False), "csv", "text/csv"),
        ("📑 TSV", records.to_csv(index=False, sep="\t"), "tsv", "text/tab-separated-values"),
        ("📊 XLSX", to_xlsx(records), "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("🗂️ XML", to_xml(records), "xml", "application/xml"),
    ]

    for column, (label, data, extension, mime) in zip(st.columns(4), exports):

        with column:

            st.download_button(
                label,
                data=data,
                file_name=f"{file_name}.{extension}",
                mime=mime,
                key=f"{key}_{extension}",
                width="stretch",
            )


# ============================================================
# 7. TAB: DRIVER MONITORING (WEBCAM)
# ============================================================

def format_time_since(seconds):
    """Turn seconds into short text like '45 s ago' or '3 h 12 min ago'."""

    seconds = max(int(seconds), 0)

    if seconds < 60:
        return f"{seconds} s ago"

    if seconds < 3600:
        return f"{seconds // 60} min ago"

    return f"{seconds // 3600} h {seconds % 3600 // 60} min ago"


@st.fragment(run_every=2)
def show_live_now():
    """Newest webcam events, refreshed every 2 seconds."""

    st.markdown("#### 🔴 Live now")

    df = load_webcam_events()

    if df.empty:

        st.caption("Waiting for the first event from the detector…")
        return

    df = df.sort_values("timestamp", ascending=False)
    latest = df.iloc[0]

    today_count = (df["timestamp"].dt.date == date.today()).sum()
    seconds_since = (pd.Timestamp.now() - latest["timestamp"]).total_seconds()

    left, right = st.columns([2, 1])

    with left:

        metric1, metric2 = st.columns(2)

        metric1.metric("Events today", f"{today_count:,}")
        metric2.metric("Last event", format_time_since(seconds_since), latest["event_type"], delta_color="off")

        st.dataframe(
            df.head(5)[["timestamp", "driver_id", "event_type", "duration_s", "severity"]]
            .rename(columns=COLUMN_LABELS),
            width="stretch",
            hide_index=True,
        )

    with right:

        # Seeded events have no picture, so look for the newest one that has.
        with_pictures = df[df["snapshot"].notna()]

        if not with_pictures.empty:

            newest = with_pictures.iloc[0]
            picture = ROOT / newest["snapshot"]

            if picture.exists():

                # Inline picture instead of st.image: st.image's /media link
                # returns an error with this Streamlit + Starlette pair.
                encoded = base64.b64encode(picture.read_bytes()).decode()

                st.markdown(
                    f'<img src="data:image/jpeg;base64,{encoded}" '
                    'style="width: 100%; border-radius: 12px;">',
                    unsafe_allow_html=True,
                )

                st.caption(f"{newest['event_type']} · {newest['timestamp']:%H:%M:%S}")


def show_monitoring_tab(df):

    show_live_now()

    if df.empty:

        st.info("No webcam events yet. Run `python scripts/seed.py` or start the detector.")
        return

    # The filters stay outside the fragment, so they never reset.
    # Changing one reruns the page, which passes the new values in.
    driver, event_type, start_date, end_date = show_filters(df, "webcam")

    show_webcam_results(driver, event_type, start_date, end_date)


@st.fragment(run_every=2)
def show_webcam_results(driver, event_type, start_date, end_date):
    """KPIs, charts and records, reloaded every 2 seconds."""

    filtered = apply_filters(
        load_webcam_events(),
        driver,
        event_type,
        start_date,
        end_date,
    )

    if filtered.empty:

        st.info("No events match these filters.")
        return

    # ----------------------------------
    # KPI METRICS
    # ----------------------------------

    high_events = (filtered["severity"] == "HIGH").sum()

    most_common = filtered["event_type"].value_counts().idxmax()

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric("Total events", f"{len(filtered):,}")
    metric2.metric("High severity", f"{high_events:,}")
    metric3.metric("Average duration", f"{filtered['duration_s'].mean():.1f} s")
    metric4.metric("Most common", most_common)

    # ----------------------------------
    # CHARTS (2 × 2)
    # ----------------------------------

    left, right = st.columns(2)

    with left:
        show_type_chart(filtered, WEBCAM_EVENT_COLORS, "webcam_types")

    with right:
        show_severity_chart(filtered, "webcam_severity")

    left, right = st.columns(2)

    with left:
        show_daily_chart(filtered, "webcam_daily")

    with right:

        driver_counts = (
            filtered.groupby(["driver_id", "severity"])
            .size()
            .reset_index(name="Events")
        )

        fig = px.bar(
            driver_counts,
            x="driver_id",
            y="Events",
            color="severity",
            color_discrete_map=SEVERITY_COLORS,
            category_orders={"severity": SEVERITY_ORDER},
            title="Events per driver",
        )

        fig.update_layout(
            xaxis={"title": ""},
            legend={"title": "", "orientation": "h", "y": -0.15},
        )

        show_chart(fig, "webcam_drivers")

    # ----------------------------------
    # RECORDS AND EXPORT
    # ----------------------------------

    show_records(
        filtered,
        WEBCAM_COLUMNS,
        "webcam_events",
        "webcam",
    )


# ============================================================
# 8. TAB: DRIVING BEHAVIOUR
# ============================================================

def show_driving_tab(df):

    if df.empty:

        st.info("No driving events yet. Run `python scripts/seed_behavior.py`.")
        return

    driver, event_type, start_date, end_date = show_filters(df, "driving")

    filtered = apply_filters(df, driver, event_type, start_date, end_date)

    # ----------------------------------
    # DRIVER SCORES
    # ----------------------------------

    if driver == "All drivers":
        score_drivers = df["driver_id"].unique().tolist()
    else:
        score_drivers = [driver]

    # Drivers with no events in the selection keep a score of 100.
    scores = calculate_driver_scores(
        filtered,
        drivers=score_drivers,
        start_date=start_date,
        end_date=end_date,
    ).sort_values(
        ["score", "driver_id"],
        ascending=[False, True],
    )

    need_attention = scores[scores["score"] < ATTENTION_SCORE]

    high_events = (filtered["severity"] == "HIGH").sum()

    # ----------------------------------
    # KPI METRICS
    # ----------------------------------

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric("Average score", f"{scores['score'].mean():.0f} / 100")
    metric2.metric("Driving events", f"{len(filtered):,}")
    metric3.metric("High severity", f"{high_events:,}")
    metric4.metric("Need attention", f"{len(need_attention):,}")

    # One summary message instead of one warning per driver.
    if need_attention.empty:

        st.success(f"All drivers are at or above {ATTENTION_SCORE}/100.")

    else:

        names = ", ".join(
            f"{row.driver_id} ({row.score})"
            for row in need_attention.itertuples()
        )

        st.warning(f"Below {ATTENTION_SCORE}/100: {names}")

    # ----------------------------------
    # SCORES: CHART + LEADERBOARD
    # ----------------------------------

    left, right = st.columns(2)

    with left:

        fig = px.bar(
            scores.sort_values("score"),
            x="score",
            y="driver_id",
            orientation="h",
            color="classification",
            color_discrete_map=SCORE_COLORS,
            text="score",
            title="Driver scores",
        )

        fig.update_layout(
            xaxis={"range": [0, 110], "title": "Score out of 100"},
            yaxis={"title": ""},
            legend={"title": "", "orientation": "h", "y": -0.25},
        )

        show_chart(fig, "driving_scores")

    with right:

        st.markdown("##### 🏆 Leaderboard")

        leaderboard = scores[[
            "driver_id",
            "score",
            "classification",
            "low_events",
            "medium_events",
            "high_events",
        ]].rename(columns={
            "driver_id": "Driver",
            "score": "Score",
            "classification": "Rating",
            "low_events": "Low",
            "medium_events": "Medium",
            "high_events": "High",
        })

        st.dataframe(
            leaderboard,
            width="stretch",
            hide_index=True,
        )

        deductions = ", ".join(
            f"{severity} −{points}"
            for severity, points in SEVERITY_DEDUCTIONS.items()
        )

        st.caption(
            f"Each driver starts at 100. Deductions: {deductions}. "
            "Synthetic demo rules, not a certified safety rating."
        )

    if filtered.empty:

        st.info("No driving events match these filters.")
        return

    # ----------------------------------
    # EVENT CHARTS
    # ----------------------------------

    left, middle, right = st.columns(3)

    with left:
        show_type_chart(filtered, DRIVING_EVENT_COLORS, "driving_types")

    with middle:
        show_severity_chart(filtered, "driving_severity")

    with right:
        show_daily_chart(filtered, "driving_daily")

    # ----------------------------------
    # RECORDS AND EXPORT
    # ----------------------------------

    show_records(
        filtered,
        DRIVING_COLUMNS,
        "driving_events",
        "driving",
    )


# ============================================================
# 9. PAGE LAYOUT
# ============================================================

st.title("🚗 Fleet Safety Dashboard")

st.caption("Driver monitoring and driving behaviour analytics · synthetic demo data")

try:

    webcam_df = load_webcam_events()
    driving_df = load_driving_events()

except Exception as error:

    st.error(f"Could not load the database: {error}")
    st.stop()

monitoring_tab, driving_tab = st.tabs([
    "👁️ Driver Monitoring",
    "🚦 Driving Behaviour",
])

with monitoring_tab:
    show_monitoring_tab(webcam_df)

with driving_tab:
    show_driving_tab(driving_df)