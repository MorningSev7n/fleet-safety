
import io
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_events


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Fleet Safety Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CUSTOM STYLING
# ============================================================

st.markdown(
    """
    <style>
        .stApp {
            background-color: #11151C;
        }

        [data-testid="stMetric"] {
            background-color: #202733;
            border: 1px solid #303B49;
            padding: 18px;
            border-radius: 12px;
        }

        [data-testid="stMetricLabel"] {
            color: #A6B0BE;
        }

        [data-testid="stMetricValue"] {
            color: #FFFFFF;
        }

        h1, h2, h3 {
            color: #FFFFFF;
        }

        div[data-testid="stDownloadButton"] button {
            width: 100%;
            border-radius: 8px;
        }

        .dashboard-caption {
            color: #A6B0BE;
            font-size: 14px;
        }

        .section-title {
            color: #FFFFFF;
            font-size: 19px;
            font-weight: 600;
            margin-bottom: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATABASE
# ============================================================

@st.cache_data(ttl=5)
def load_events():
    """Load events from the existing SQLite database."""

    df = get_events()

    if df is None:
        return pd.DataFrame()

    df = df.copy()

    required_columns = [
        "id",
        "timestamp",
        "driver_id",
        "vehicle_id",
        "event_type",
        "duration_s",
        "severity",
    ]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(
                f"Database is missing required column: {column}"
            )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    df["duration_s"] = pd.to_numeric(
        df["duration_s"],
        errors="coerce",
    )

    return df


try:
    events_df = load_events()

except Exception as error:
    st.error(f"Could not load database events: {error}")
    st.info(
        "Check that events.db exists and src/db.py "
        "can connect to it."
    )
    st.stop()


# ============================================================
# HEADER
# ============================================================

st.title("🚗 Fleet Safety")
st.markdown(
    '<p class="dashboard-caption">'
    'DRIVER MONITORING AND EVENT ANALYTICS'
    '</p>',
    unsafe_allow_html=True,
)

st.divider()


# ============================================================
# CHECK DATABASE
# ============================================================

if events_df.empty:

    st.warning("No events found in the database.")

    st.info(
        "Run python seed.py from your project root "
        "to generate synthetic dashboard data."
    )

    st.stop()


# ============================================================
# GLOBAL FILTERS
# ============================================================

st.markdown("### 🔎 Dashboard Filters")

filter_col1, filter_col2, filter_col3 = st.columns(
    [1, 1, 2]
)

# Driver filter

drivers = sorted(
    events_df["driver_id"]
    .dropna()
    .unique()
    .tolist()
)

with filter_col1:

    selected_driver = st.selectbox(
        "Driver",
        options=["All Drivers"] + drivers,
    )


# Event type filter

event_types = sorted(
    events_df["event_type"]
    .dropna()
    .unique()
    .tolist()
)

with filter_col2:

    selected_event = st.selectbox(
        "Event Type",
        options=["All Events"] + event_types,
    )


# Date filter

valid_timestamps = events_df["timestamp"].dropna()

if valid_timestamps.empty:

    st.error("No valid timestamps found in the database.")
    st.stop()

min_date = valid_timestamps.min().date()
max_date = valid_timestamps.max().date()

with filter_col3:

    selected_dates = st.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )


# ============================================================
# APPLY ALL FILTERS
# ============================================================

filtered_df = events_df.copy()

if selected_driver != "All Drivers":

    filtered_df = filtered_df[
        filtered_df["driver_id"] == selected_driver
    ]


if selected_event != "All Events":

    filtered_df = filtered_df[
        filtered_df["event_type"] == selected_event
    ]


if isinstance(selected_dates, (tuple, list)):

    if len(selected_dates) == 2:

        start_date, end_date = selected_dates

        filtered_df = filtered_df[
            filtered_df["timestamp"].notna()
            & (
                filtered_df["timestamp"].dt.date >= start_date
            )
            & (
                filtered_df["timestamp"].dt.date <= end_date
            )
        ]

    elif len(selected_dates) == 1:

        selected_date = selected_dates[0]

        filtered_df = filtered_df[
            filtered_df["timestamp"].dt.date == selected_date
        ]

else:

    filtered_df = filtered_df[
        filtered_df["timestamp"].dt.date == selected_dates
    ]


# ============================================================
# KPI METRICS
# ============================================================

st.markdown("### 📊 Fleet Overview")

total_events = len(filtered_df)

total_drivers = filtered_df["driver_id"].nunique()

high_severity = (
    filtered_df["severity"]
    .astype(str)
    .str.upper()
    .eq("HIGH")
    .sum()
)

if total_events > 0:

    most_common_event = (
        filtered_df["event_type"]
        .value_counts()
        .idxmax()
    )

else:

    most_common_event = "N/A"


metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric(
    "Total Events",
    f"{total_events:,}",
)

metric2.metric(
    "Drivers",
    total_drivers,
)

metric3.metric(
    "High Severity",
    f"{high_severity:,}",
)

metric4.metric(
    "Most Common Event",
    most_common_event,
)

st.divider()


# ============================================================
# CHART CONFIGURATION
# ============================================================

chart_template = "plotly_dark"

chart_layout = {
    "template": chart_template,
    "paper_bgcolor": "#202733",
    "plot_bgcolor": "#202733",
    "font": {"color": "#E5EAF0"},
    "margin": {"l": 25, "r": 25, "t": 45, "b": 35},
    "legend": {"orientation": "h"},
}


# ============================================================
# CHART 1: EVENT DISTRIBUTION
# ============================================================

st.markdown("### 📌 Event Distribution")

if not filtered_df.empty:

    event_counts = (
        filtered_df["event_type"]
        .value_counts()
        .reset_index()
    )

    event_counts.columns = [
        "Event Type",
        "Count",
    ]

    fig_events = px.pie(
        event_counts,
        names="Event Type",
        values="Count",
        hole=0.55,
        title="Events by Type",
        color="Event Type",
        color_discrete_map={
            "EYES_CLOSED": "#E35D5B",
            "YAWN": "#E7A947",
            "LOOK_AWAY": "#F08A4B",
            "PHONE": "#A875D8",
        },
    )

    fig_events.update_layout(**chart_layout)

    st.plotly_chart(
        fig_events,
        use_container_width=True,
    )

else:

    st.info("No events available for this selection.")


st.divider()


# ============================================================
# CHART 2: EVENTS OVER TIME
# ============================================================

st.markdown("### 📈 Events Over Time")

if not filtered_df.empty:

    time_data = filtered_df.dropna(
        subset=["timestamp"]
    ).copy()

    if not time_data.empty:

        time_data["Date"] = (
            time_data["timestamp"].dt.date
        )

        daily_events = (
            time_data.groupby("Date")
            .size()
            .reset_index(name="Event Count")
        )

        fig_time = px.line(
            daily_events,
            x="Date",
            y="Event Count",
            markers=True,
            title="Daily Recorded Events",
        )

        fig_time.update_traces(
            line=dict(color="#4DA3FF", width=3),
            marker=dict(size=8),
        )

        fig_time.update_layout(**chart_layout)

        st.plotly_chart(
            fig_time,
            use_container_width=True,
        )

    else:

        st.info("No valid timestamps for this selection.")

else:

    st.info("No events available for this selection.")


st.divider()


# ============================================================
# CHART 3: DRIVER COMPARISON
# ============================================================

st.markdown("### 👤 Driver Comparison")

if not filtered_df.empty:

    driver_data = (
        filtered_df.groupby("driver_id")
        .size()
        .reset_index(name="Event Count")
        .sort_values("Event Count", ascending=False)
    )

    fig_drivers = px.bar(
        driver_data,
        x="driver_id",
        y="Event Count",
        color="Event Count",
        title="Events Recorded per Driver",
        color_continuous_scale=[
            "#305B8C",
            "#4DA3FF",
        ],
        text="Event Count",
    )

    fig_drivers.update_traces(
        textposition="outside"
    )

    fig_drivers.update_layout(**chart_layout)

    st.plotly_chart(
        fig_drivers,
        use_container_width=True,
    )

else:

    st.info("No events available for this selection.")


st.divider()


# ============================================================
# CHART 4: SEVERITY BREAKDOWN
# ============================================================

st.markdown("### ⚠️ Severity Breakdown")

if not filtered_df.empty:

    severity_data = (
        filtered_df["severity"]
        .fillna("UNKNOWN")
        .astype(str)
        .str.upper()
        .value_counts()
        .reset_index()
    )

    severity_data.columns = [
        "Severity",
        "Count",
    ]

    fig_severity = px.bar(
        severity_data,
        x="Severity",
        y="Count",
        color="Severity",
        title="Events by Severity Level",
        color_discrete_map={
            "HIGH": "#E35D5B",
            "MEDIUM": "#E7A947",
            "LOW": "#42B883",
            "UNKNOWN": "#8993A1",
        },
        text="Count",
    )

    fig_severity.update_traces(
        textposition="outside"
    )

    fig_severity.update_layout(**chart_layout)

    st.plotly_chart(
        fig_severity,
        use_container_width=True,
    )

else:

    st.info("No events available for this selection.")


st.divider()


# ============================================================
# FILTERED EVENT TABLE
# ============================================================

st.markdown("### 📋 Recorded Events")

st.caption(
    f"Showing {len(filtered_df):,} filtered records."
)

display_columns = [
    "id",
    "timestamp",
    "driver_id",
    "vehicle_id",
    "event_type",
    "duration_s",
    "severity",
]

st.dataframe(
    filtered_df[display_columns].sort_values(
        "timestamp",
        ascending=False,
        na_position="last",
    ),
    use_container_width=True,
    hide_index=True,
)


st.divider()


# ============================================================
# EXPORT FUNCTIONS
# ============================================================

st.markdown("### 📥 Export Filtered Data")

st.caption(
    "Download only the records matching your current filters."
)

export_df = filtered_df[display_columns].copy()


# CSV export

csv_data = export_df.to_csv(
    index=False
).encode("utf-8")


# TSV export

tsv_data = export_df.to_csv(
    index=False,
    sep="\t",
).encode("utf-8")


# XLSX export

xlsx_buffer = io.BytesIO()

with pd.ExcelWriter(
    xlsx_buffer,
    engine="openpyxl",
) as writer:

    export_df.to_excel(
        writer,
        index=False,
        sheet_name="Fleet Events",
    )

xlsx_data = xlsx_buffer.getvalue()


# XML export

def export_xml(df):

    root = ET.Element("fleet_events")

    root.set("total_records", str(len(df)))

    for _, row in df.iterrows():

        event = ET.SubElement(
            root,
            "event",
        )

        for column in display_columns:

            element = ET.SubElement(
                event,
                column,
            )

            value = row[column]

            if pd.isna(value):
                element.text = ""
            elif isinstance(value, pd.Timestamp):
                element.text = value.isoformat()
            else:
                element.text = str(value)

    ET.indent(
        root,
        space="    ",
    )

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )


xml_data = export_xml(export_df)


# ============================================================
# DOWNLOAD BUTTONS
# ============================================================

download1, download2, download3, download4 = st.columns(4)

with download1:

    st.download_button(
        label="📄 CSV",
        data=csv_data,
        file_name="fleet_events.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=export_df.empty,
    )


with download2:

    st.download_button(
        label="📑 TSV",
        data=tsv_data,
        file_name="fleet_events.tsv",
        mime="text/tab-separated-values",
        use_container_width=True,
        disabled=export_df.empty,
    )


with download3:

    st.download_button(
        label="📊 XLSX",
        data=xlsx_data,
        file_name="fleet_events.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        disabled=export_df.empty,
    )


with download4:

    st.download_button(
        label="🗂️ XML",
        data=xml_data,
        file_name="fleet_events.xml",
        mime="application/xml",
        use_container_width=True,
        disabled=export_df.empty,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center; color:#8993A1;">
        Fleet Safety | Driver Monitoring System<br>
        Powered by Python, Streamlit, SQLite and Plotly
    </div>
    """,
    unsafe_allow_html=True,
)
