import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from utils import (
    load_data,
    process_data,
    calculate_delay_deltas,
    get_summary_stats,
    get_top_culprits,
    get_recovery_points,
    seconds_to_time,
    seconds_to_hms,
    STATION_SEQUENCE_DOWN,
    STATION_SEQUENCE_UP,
)

st.set_page_config(
    page_title="Train Delay Analysis Dashboard",
    page_icon=":train:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 0.9em;
        color: #666;
    }
    .culprit-positive {
        color: #d32f2f;
        font-weight: bold;
    }
    .culprit-negative {
        color: #388e3c;
        font-weight: bold;
    }
    .direction-down {
        color: #1976d2;
    }
    .direction-up {
        color: #7b1fa2;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🚆 Train Delay Analysis Dashboard")
st.markdown("**West Rail Line (TSW ↔ CEN) Delay Pattern Analysis**")

with st.sidebar:
    st.header("📁 Data Source")

    data_source = st.radio(
        "Choose data source:",
        [
            "Sample Data 1 (sample.csv)",
            "Sample Data 2 (sample2.csv)",
            "Upload CSV File",
        ],
        index=0,
        key="data_source_radio",
    )

    uploaded_file = None
    if data_source == "Upload CSV File":
        uploaded_file = st.file_uploader(
            "Upload Trip Data CSV",
            type=["csv"],
            help="Upload your own trip data CSV file (columns: un, Trip, Destination, Platform, Sched. Arr., Sched. Dep., Actual Arr., Actual Dep., Variance)",
            accept_multiple_files=False,
            key="trip_data_uploader",
        )

    st.markdown("---")
    st.header("Filters")

if data_source == "Upload CSV File" and uploaded_file is not None:
    try:
        df_source = pd.read_csv(uploaded_file)
        st.info(f"📊 Analyzing uploaded data: {len(df_source)} records")
        sample_file = None
    except Exception as e:
        st.error(f"❌ Error loading file: {e}")
        df_source = None
        sample_file = "data/sample.csv"
elif data_source == "Sample Data 2 (sample2.csv)":
    df_source = None
    sample_file = "sample2.csv"
    st.info("📊 Using sample data 2 (sample2.csv)")
else:
    df_source = None
    sample_file = None
    st.info("📊 Using sample data 1 (sample.csv)")


@st.cache_data
def load_and_process_data(_df_source=None, _sample_file=None):
    if _df_source is not None:
        df = _df_source.copy()
        _, station_order = load_data()
    elif _sample_file is not None:
        df = pd.read_csv(_sample_file)
        _, station_order = load_data()
    else:
        df, station_order = load_data()
    df_processed = process_data(df, station_order)
    deltas_df = calculate_delay_deltas(df_processed)
    return df_processed, deltas_df, station_order


df, deltas_df, station_order = load_and_process_data(df_source, sample_file)

trips = sorted(df["Trip"].unique().tolist())
selected_trips = st.sidebar.multiselect("Select Trips", trips, default=trips)

directions = ["All", "down", "up"]
selected_direction = st.sidebar.selectbox(
    "Direction",
    directions,
    format_func=lambda x: "All Directions"
    if x == "All"
    else f"{'DOWN' if x == 'down' else 'UP'} ({'UTR→CEN' if x == 'down' else 'CEN→UTR'})",
)

min_time = df["sched_arr_seconds"].min()
max_time = df["sched_arr_seconds"].max()
if pd.notna(min_time) and pd.notna(max_time):
    time_range = st.sidebar.slider(
        "Scheduled Time Range",
        min_value=int(min_time),
        max_value=int(max_time),
        value=(int(min_time), int(max_time)),
    )
else:
    time_range = (0, 24 * 60)

variance_threshold = st.sidebar.slider(
    "Culprit Threshold (seconds)",
    min_value=0,
    max_value=120,
    value=30,
    help="Highlight segments where delay increases by more than this value",
)

filtered_df = df[df["Trip"].isin(selected_trips)]
if selected_direction != "All":
    filtered_df = filtered_df[filtered_df["direction"] == selected_direction]
if len(time_range) == 2:
    filtered_df = filtered_df[
        (filtered_df["sched_arr_seconds"] >= time_range[0])
        & (filtered_df["sched_arr_seconds"] <= time_range[1])
    ]

filtered_deltas = deltas_df[deltas_df["Trip"].isin(selected_trips)]
if selected_direction != "All":
    filtered_deltas = filtered_deltas[
        filtered_deltas["Direction"] == selected_direction
    ]

stats = get_summary_stats(filtered_df)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Trips", stats["total_trips"])
with col2:
    avg_delay_str = (
        seconds_to_time(stats["avg_delay"]) if stats["avg_delay"] else "--:--"
    )
    st.metric("Avg Delay", avg_delay_str)
with col3:
    max_delay_str = (
        seconds_to_time(stats["max_delay"]) if stats["max_delay"] else "--:--"
    )
    st.metric("Max Delay", max_delay_str)
with col4:
    if "worst_journey_station" in stats:
        st.metric(
            "Worst Station (Journey Delay)",
            stats["worst_journey_station"],
            delta=f"+{stats.get('worst_journey_delay', 0):.1f}s",
        )
    else:
        st.metric("Worst Station (Journey Delay)", "N/A")
with col5:
    if "best_journey_station" in stats:
        st.metric(
            "Best Station (Journey Delay)",
            stats["best_journey_station"],
            delta=f"{stats.get('best_journey_delay', 0):.1f}s",
        )
    else:
        st.metric("Best Station (Journey Delay)", "N/A")

st.markdown("---")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🔴 Top Delay Culprits")
    culprits = get_top_culprits(filtered_deltas, n=5)
    if not culprits.empty:
        for _, row in culprits.iterrows():
            dir_label = "DOWN" if row["Direction"] == "down" else "UP"
            st.markdown(f"**{row['segment']}** (Trip {row['Trip']}, {dir_label})")
            st.markdown(
                f"<span class='culprit-positive'>+{row['delta_time']}</span>",
                unsafe_allow_html=True,
            )
            st.progress(min(row["delta_seconds"] / 180, 1.0))
    else:
        st.info("No significant delay culprits found with current filters.")

with col_right:
    st.subheader("🟢 Top Recovery Points")
    recovery = get_recovery_points(filtered_deltas, n=5)
    if not recovery.empty:
        for _, row in recovery.iterrows():
            dir_label = "DOWN" if row["Direction"] == "down" else "UP"
            st.markdown(f"**{row['segment']}** (Trip {row['Trip']}, {dir_label})")
            st.markdown(
                f"<span class='culprit-negative'>{row['delta_time']}</span>",
                unsafe_allow_html=True,
            )
            st.progress(min(abs(row["delta_seconds"]) / 60, 1.0))
    else:
        st.info("No recovery points found with current filters.")

st.markdown("---")

st.subheader("📈 Delay Accumulation Analysis (Cumulative Inter-Station Delay)")
st.markdown(
    "*Starting from first recorded station (delta = 0), showing cumulative delay accumulation along the journey*"
)

down_trips = filtered_df[filtered_df["direction"] == "down"]["Trip"].unique()
up_trips = filtered_df[filtered_df["direction"] == "up"]["Trip"].unique()

col_down, col_up = st.columns(2)


def calculate_cumulative_delta(trip_df, trip_deltas):
    stations = trip_df["base_station"].tolist()
    variances = trip_df["variance_seconds"].tolist()

    delta_map = {}
    for _, row in trip_deltas.iterrows():
        delta_map[(row["From_Station"], row["To_Station"])] = row["delta_seconds"]

    cumulative_delta = [0]
    cumsum = 0
    for i in range(len(stations) - 1):
        from_st = stations[i]
        to_st = stations[i + 1]
        delta = delta_map.get((from_st, to_st), 0)
        cumsum += delta
        cumulative_delta.append(cumsum)

    return stations, cumulative_delta, variances


with col_down:
    st.markdown("### 🔵 DOWN Direction (UTR → CEN)")
    fig_down = go.Figure()

    down_colors = ["#1976d2", "#42a5f5", "#0d47a1", "#82b1ff", "#1565c0", "#2196f3"]

    down_stations_ordered = STATION_SEQUENCE_DOWN

    for idx, trip in enumerate(sorted(down_trips)):
        trip_df = (
            filtered_df[
                (filtered_df["Trip"] == trip) & (filtered_df["direction"] == "down")
            ]
            .sort_values("station_order")
            .reset_index(drop=True)
        )

        if not trip_df.empty:
            trip_deltas = filtered_deltas[
                (filtered_deltas["Trip"] == trip)
                & (filtered_deltas["Direction"] == "down")
            ]

            stations, cumulative_delta, variances = calculate_cumulative_delta(
                trip_df, trip_deltas
            )

            color = down_colors[idx % len(down_colors)]
            fig_down.add_trace(
                go.Scatter(
                    x=stations,
                    y=cumulative_delta,
                    mode="lines+markers",
                    name=f"Trip {trip}",
                    line=dict(color=color, width=2),
                    marker=dict(size=8),
                    hovertemplate="<b>Trip %{text}</b><br>Station: %{x}<br>Cumulative Delta: %{y:.0f}s<extra></extra>",
                    text=[str(trip)] * len(stations),
                )
            )

    fig_down.update_layout(
        xaxis_title="Station (UTR → CEN)",
        yaxis_title="Cumulative Delay Delta (seconds)",
        hovermode="x unified",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=30, b=100),
        xaxis_tickangle=-45,
        xaxis=dict(categoryorder="array", categoryarray=down_stations_ordered),
    )
    fig_down.add_hline(y=0, line_dash="solid", line_color="gray", line_width=1)
    fig_down.add_hline(
        y=300,
        line_dash="dash",
        line_color="red",
        annotation_text="5 min",
        annotation_position="right",
    )
    fig_down.add_hline(
        y=600,
        line_dash="dash",
        line_color="darkred",
        annotation_text="10 min",
        annotation_position="right",
    )
    st.plotly_chart(fig_down, width="stretch")

with col_up:
    st.markdown("### 🟣 UP Direction (CEN → UTR)")
    fig_up = go.Figure()

    up_colors = ["#7b1fa2", "#ab47bc", "#4a148c", "#ce93d8", "#6a1b9a", "#9c27b0"]

    up_stations_ordered = STATION_SEQUENCE_UP

    for idx, trip in enumerate(sorted(up_trips)):
        trip_df = (
            filtered_df[
                (filtered_df["Trip"] == trip) & (filtered_df["direction"] == "up")
            ]
            .sort_values("station_order")
            .reset_index(drop=True)
        )

        if not trip_df.empty:
            trip_deltas = filtered_deltas[
                (filtered_deltas["Trip"] == trip)
                & (filtered_deltas["Direction"] == "up")
            ]

            stations, cumulative_delta, variances = calculate_cumulative_delta(
                trip_df, trip_deltas
            )

            color = up_colors[idx % len(up_colors)]
            fig_up.add_trace(
                go.Scatter(
                    x=stations,
                    y=cumulative_delta,
                    mode="lines+markers",
                    name=f"Trip {trip}",
                    line=dict(color=color, width=2),
                    marker=dict(size=8),
                    hovertemplate="<b>Trip %{text}</b><br>Station: %{x}<br>Cumulative Delta: %{y:.0f}s<extra></extra>",
                    text=[str(trip)] * len(stations),
                )
            )

    fig_up.update_layout(
        xaxis_title="Station (CEN → UTR)",
        yaxis_title="Cumulative Delay Delta (seconds)",
        hovermode="x unified",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=30, b=100),
        xaxis_tickangle=-45,
        xaxis=dict(categoryorder="array", categoryarray=up_stations_ordered),
    )
    fig_up.add_hline(y=0, line_dash="solid", line_color="gray", line_width=1)
    fig_up.add_hline(
        y=300,
        line_dash="dash",
        line_color="red",
        annotation_text="5 min",
        annotation_position="right",
    )
    fig_up.add_hline(
        y=600,
        line_dash="dash",
        line_color="darkred",
        annotation_text="10 min",
        annotation_position="right",
    )
    st.plotly_chart(fig_up, width="stretch")

st.subheader("📊 Delay Delta by Station Segment")
if not filtered_deltas.empty:
    delta_sorted = filtered_deltas.sort_values("delta_seconds", ascending=False)
    colors = [
        "red" if x > variance_threshold else "green" if x < 0 else "gray"
        for x in delta_sorted["delta_seconds"]
    ]

    labels = [
        f"{row['segment']} ({row['Direction'].upper()})"
        for _, row in delta_sorted.iterrows()
    ]

    fig_delta = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=delta_sorted["delta_seconds"],
                marker_color=colors,
                hovertemplate="Segment: %{x}<br>Delta: %{y}s<extra></extra>",
            )
        ]
    )
    fig_delta.update_layout(
        xaxis_title="Station Segment (Direction)",
        yaxis_title="Delay Delta (seconds)",
        height=350,
        xaxis_tickangle=-45,
    )
    fig_delta.add_hline(
        y=variance_threshold,
        line_dash="dash",
        line_color="red",
        annotation_text="Culprit threshold",
    )
    st.plotly_chart(fig_delta, width="stretch")
else:
    st.info("No delay delta data available with current filters.")

st.markdown("---")
st.subheader("🗺️ Station Delay Heatmap by Direction")

col_heat_down, col_heat_up = st.columns(2)

with col_heat_down:
    st.markdown("### 🔵 DOWN Direction (UTR → CEN)")
    down_df = filtered_df[filtered_df["direction"] == "down"]
    if not down_df.empty:
        heatmap_down = down_df.pivot_table(
            values="variance_seconds",
            index="base_station",
            columns="Trip",
            aggfunc="mean",
        )
        if not heatmap_down.empty:
            heatmap_down = heatmap_down.reindex(
                [s for s in STATION_SEQUENCE_DOWN if s in heatmap_down.index]
            )
            fig_heatmap_down = go.Figure(
                data=go.Heatmap(
                    z=heatmap_down.values,
                    x=[str(c) for c in heatmap_down.columns],
                    y=heatmap_down.index,
                    colorscale="RdYlGn_r",
                    hovertemplate="Trip: %{x}<br>Station: %{y}<br>Delay: %{z:.0f}s<extra></extra>",
                )
            )
            fig_heatmap_down.update_layout(
                height=450, xaxis_title="Trip", yaxis_title="Station (UTR → CEN)"
            )
            st.plotly_chart(fig_heatmap_down, width="stretch")
        else:
            st.info("No data for DOWN direction heatmap.")
    else:
        st.info("No DOWN direction trips selected.")

with col_heat_up:
    st.markdown("### 🟣 UP Direction (CEN → UTR)")
    up_df = filtered_df[filtered_df["direction"] == "up"]
    if not up_df.empty:
        heatmap_up = up_df.pivot_table(
            values="variance_seconds",
            index="base_station",
            columns="Trip",
            aggfunc="mean",
        )
        if not heatmap_up.empty:
            heatmap_up = heatmap_up.reindex(
                [s for s in STATION_SEQUENCE_UP if s in heatmap_up.index]
            )
            fig_heatmap_up = go.Figure(
                data=go.Heatmap(
                    z=heatmap_up.values,
                    x=[str(c) for c in heatmap_up.columns],
                    y=heatmap_up.index,
                    colorscale="RdYlGn_r",
                    hovertemplate="Trip: %{x}<br>Station: %{y}<br>Delay: %{z:.0f}s<extra></extra>",
                )
            )
            fig_heatmap_up.update_layout(
                height=450, xaxis_title="Trip", yaxis_title="Station (CEN → UTR)"
            )
            st.plotly_chart(fig_heatmap_up, width="stretch")
        else:
            st.info("No data for UP direction heatmap.")
    else:
        st.info("No UP direction trips selected.")

st.markdown("---")
st.subheader("⏱️ Dwell Time Variance by Station & Direction")

col_dwell_down, col_dwell_up = st.columns(2)

with col_dwell_down:
    st.markdown("### 🔵 DOWN Direction (UTR → CEN)")
    dwell_down = filtered_df[
        (filtered_df["direction"] == "down") & (filtered_df["dwell_variance"].notna())
    ].copy()
    if not dwell_down.empty:
        avg_dwell_down = dwell_down.groupby("base_station")["dwell_variance"].mean()
        avg_dwell_down = avg_dwell_down.reindex(
            [s for s in STATION_SEQUENCE_DOWN if s in avg_dwell_down.index]
        )
        fig_dwell_down = go.Figure(
            data=[
                go.Bar(
                    x=avg_dwell_down.index,
                    y=avg_dwell_down.values,
                    marker_color=[
                        "#d32f2f" if x > 0 else "#388e3c" for x in avg_dwell_down.values
                    ],
                    hovertemplate="Station: %{x}<br>Dwell Variance: %{y:.1f}s<extra></extra>",
                )
            ]
        )
        fig_dwell_down.update_layout(
            xaxis_title="Station (UTR → CEN)",
            yaxis_title="Avg Dwell Time Variance (seconds)",
            height=400,
            xaxis_tickangle=-45,
        )
        fig_dwell_down.add_hline(y=0, line_color="black", line_width=1)
        st.plotly_chart(fig_dwell_down, width="stretch")
    else:
        st.info("No dwell time data for DOWN direction.")

with col_dwell_up:
    st.markdown("### 🟣 UP Direction (CEN → UTR)")
    dwell_up = filtered_df[
        (filtered_df["direction"] == "up") & (filtered_df["dwell_variance"].notna())
    ].copy()
    if not dwell_up.empty:
        avg_dwell_up = dwell_up.groupby("base_station")["dwell_variance"].mean()
        avg_dwell_up = avg_dwell_up.reindex(
            [s for s in STATION_SEQUENCE_UP if s in avg_dwell_up.index]
        )
        fig_dwell_up = go.Figure(
            data=[
                go.Bar(
                    x=avg_dwell_up.index,
                    y=avg_dwell_up.values,
                    marker_color=[
                        "#7b1fa2" if x > 0 else "#388e3c" for x in avg_dwell_up.values
                    ],
                    hovertemplate="Station: %{x}<br>Dwell Variance: %{y:.1f}s<extra></extra>",
                )
            ]
        )
        fig_dwell_up.update_layout(
            xaxis_title="Station (CEN → UTR)",
            yaxis_title="Avg Dwell Time Variance (seconds)",
            height=400,
            xaxis_tickangle=-45,
        )
        fig_dwell_up.add_hline(y=0, line_color="black", line_width=1)
        st.plotly_chart(fig_dwell_up, width="stretch")
    else:
        st.info("No dwell time data for UP direction.")

st.markdown("---")
st.subheader("🚆 Journey Time by Trip (Stacked by Station Segments)")
st.markdown(
    "*Each bar shows total journey time, colored by time spent between stations. Sorted by actual departure time.*"
)


def calculate_journey_segments(trip_df):
    segments = []
    trip_df = trip_df.sort_values("station_order").reset_index(drop=True)

    for i in range(len(trip_df)):
        row = trip_df.iloc[i]
        station = row["base_station"]

        dwell_time = 0
        if pd.notna(row["actual_arr_seconds"]) and pd.notna(row["actual_dep_seconds"]):
            dwell_time = row["actual_dep_seconds"] - row["actual_arr_seconds"]

        travel_time = 0
        if i < len(trip_df) - 1:
            next_row = trip_df.iloc[i + 1]
            if pd.notna(row["actual_dep_seconds"]) and pd.notna(
                next_row["actual_arr_seconds"]
            ):
                travel_time = next_row["actual_arr_seconds"] - row["actual_dep_seconds"]

        segments.append(
            {
                "station": station,
                "dwell_time": max(0, dwell_time),
                "travel_time": max(0, travel_time),
                "total_time": max(0, dwell_time) + max(0, travel_time),
            }
        )

    return segments


col_journey_down, col_journey_up = st.columns(2)

with col_journey_down:
    st.markdown("### 🔵 DOWN Direction (UTR → CEN)")

    down_trips_data = []
    for trip in sorted(down_trips):
        trip_df = filtered_df[
            (filtered_df["Trip"] == trip) & (filtered_df["direction"] == "down")
        ].sort_values("station_order")

        if not trip_df.empty:
            first_dep = trip_df.iloc[0]["actual_dep_seconds"]
            if pd.notna(first_dep):
                segments = calculate_journey_segments(trip_df)
                total_journey = sum(s["total_time"] for s in segments)
                down_trips_data.append(
                    {
                        "trip": trip,
                        "first_dep": first_dep,
                        "segments": segments,
                        "total_journey": total_journey,
                    }
                )

    if down_trips_data:
        down_trips_data.sort(key=lambda x: x["first_dep"])

        fig_journey_down = go.Figure()

        all_stations = set()
        for trip_data in down_trips_data:
            for seg in trip_data["segments"]:
                all_stations.add(seg["station"])

        station_colors = {}
        color_palette = [
            "#1565c0",
            "#1976d2",
            "#1e88e5",
            "#2196f3",
            "#42a5f5",
            "#64b5f6",
            "#90caf9",
            "#bbdefb",
            "#e3f2fd",
            "#82b1ff",
            "#448aff",
            "#2979ff",
            "#2962ff",
            "#0d47a1",
            "#1565c0",
            "#1a237e",
            "#283593",
        ]
        for i, station in enumerate(STATION_SEQUENCE_DOWN):
            if station in all_stations:
                station_colors[station] = color_palette[i % len(color_palette)]

        for station in all_stations:
            if station not in station_colors:
                station_colors[station] = color_palette[
                    len(station_colors) % len(color_palette)
                ]

        for trip_data in down_trips_data:
            trip = trip_data["trip"]
            segments = trip_data["segments"]

            for seg in segments:
                fig_journey_down.add_trace(
                    go.Bar(
                        name=seg["station"],
                        x=[f"Trip {trip}"],
                        y=[seg["total_time"]],
                        marker_color=station_colors.get(seg["station"], "#1976d2"),
                        hovertemplate=f"Trip {trip}<br>{seg['station']}<br>Time: {seg['total_time']:.0f}s<extra></extra>",
                        showlegend=False,
                    )
                )

        for station in STATION_SEQUENCE_DOWN:
            if station in all_stations:
                fig_journey_down.add_trace(
                    go.Bar(
                        name=station,
                        x=[None],
                        y=[None],
                        marker_color=station_colors[station],
                        showlegend=True,
                    )
                )

        fig_journey_down.update_layout(
            barmode="stack",
            xaxis_title="Trip (sorted by departure time)",
            yaxis_title="Journey Time (seconds)",
            height=400,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            legend_title="Station",
        )
        st.plotly_chart(fig_journey_down, width="stretch")

        for td in down_trips_data:
            st.caption(f"Trip {td['trip']}: {td['total_journey'] / 60:.1f} min total")
    else:
        st.info("No DOWN direction journey data available.")

with col_journey_up:
    st.markdown("### 🟣 UP Direction (CEN → UTR)")

    up_trips_data = []
    for trip in sorted(up_trips):
        trip_df = filtered_df[
            (filtered_df["Trip"] == trip) & (filtered_df["direction"] == "up")
        ].sort_values("station_order")

        if not trip_df.empty:
            first_dep = trip_df.iloc[0]["actual_dep_seconds"]
            if pd.notna(first_dep):
                segments = calculate_journey_segments(trip_df)
                total_journey = sum(s["total_time"] for s in segments)
                up_trips_data.append(
                    {
                        "trip": trip,
                        "first_dep": first_dep,
                        "segments": segments,
                        "total_journey": total_journey,
                    }
                )

    if up_trips_data:
        up_trips_data.sort(key=lambda x: x["first_dep"])

        fig_journey_up = go.Figure()

        all_stations = set()
        for trip_data in up_trips_data:
            for seg in trip_data["segments"]:
                all_stations.add(seg["station"])

        station_colors = {}
        color_palette = [
            "#6a1b9a",
            "#7b1fa2",
            "#8e24aa",
            "#9c27b0",
            "#ab47bc",
            "#ba68c8",
            "#ce93d8",
            "#e1bee7",
            "#f3e5f5",
            "#ea80fc",
            "#e040fb",
            "#d500f9",
            "#aa00ff",
            "#7c4dff",
            "#651fff",
            "#6200ea",
            "#4a148c",
        ]
        for i, station in enumerate(STATION_SEQUENCE_UP):
            if station in all_stations:
                station_colors[station] = color_palette[i % len(color_palette)]

        for station in all_stations:
            if station not in station_colors:
                station_colors[station] = color_palette[
                    len(station_colors) % len(color_palette)
                ]

        for trip_data in up_trips_data:
            trip = trip_data["trip"]
            segments = trip_data["segments"]

            for seg in segments:
                fig_journey_up.add_trace(
                    go.Bar(
                        name=seg["station"],
                        x=[f"Trip {trip}"],
                        y=[seg["total_time"]],
                        marker_color=station_colors.get(seg["station"], "#7b1fa2"),
                        hovertemplate=f"Trip {trip}<br>{seg['station']}<br>Time: {seg['total_time']:.0f}s<extra></extra>",
                        showlegend=False,
                    )
                )

        for station in STATION_SEQUENCE_UP:
            if station in all_stations:
                fig_journey_up.add_trace(
                    go.Bar(
                        name=station,
                        x=[None],
                        y=[None],
                        marker_color=station_colors[station],
                        showlegend=True,
                    )
                )

        fig_journey_up.update_layout(
            barmode="stack",
            xaxis_title="Trip (sorted by departure time)",
            yaxis_title="Journey Time (seconds)",
            height=400,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            legend_title="Station",
        )
        st.plotly_chart(fig_journey_up, width="stretch")

        for td in up_trips_data:
            st.caption(f"Trip {td['trip']}: {td['total_journey'] / 60:.1f} min total")
    else:
        st.info("No UP direction journey data available.")

st.markdown("---")
st.subheader("📅 Timeline Comparison (Scheduled vs Actual)")
selected_trip_timeline = st.selectbox(
    "Select Trip for Timeline View",
    sorted(filtered_df["Trip"].unique()) if not filtered_df.empty else [0],
)
if selected_trip_timeline and selected_trip_timeline != 0:
    trip_timeline = filtered_df[
        filtered_df["Trip"] == selected_trip_timeline
    ].sort_values("station_order")
    if not trip_timeline.empty:
        direction = trip_timeline["direction"].iloc[0]
        dir_label = "DOWN (UTR→CEN)" if direction == "down" else "UP (CEN→UTR)"
        st.markdown(f"**Direction:** {dir_label}")

        fig_timeline = go.Figure()

        for idx, (_, row) in enumerate(trip_timeline.iterrows()):
            station = row["base_station"]
            if pd.notna(row["sched_arr_seconds"]) and pd.notna(
                row["sched_dep_seconds"]
            ):
                fig_timeline.add_trace(
                    go.Bar(
                        name=f"{station} (Sched)" if idx == 0 else "",
                        x=[row["sched_dep_seconds"] - row["sched_arr_seconds"]],
                        y=[station],
                        base=[row["sched_arr_seconds"]],
                        orientation="h",
                        marker_color="lightblue",
                        showlegend=idx == 0,
                        hovertemplate=f"{station} Scheduled: {row.get('Sched. Arr.', '')} - {row.get('Sched. Dep.', '')}<extra></extra>",
                    )
                )
            if pd.notna(row["actual_arr_seconds"]) and pd.notna(
                row["actual_dep_seconds"]
            ):
                fig_timeline.add_trace(
                    go.Bar(
                        name=f"{station} (Actual)" if idx == 0 else "",
                        x=[row["actual_dep_seconds"] - row["actual_arr_seconds"]],
                        y=[station],
                        base=[row["actual_arr_seconds"]],
                        orientation="h",
                        marker_color="coral",
                        showlegend=idx == 0,
                        hovertemplate=f"{station} Actual: {row.get('Actual Arr.', '')} - {row.get('Actual Dep.', '')}<extra></extra>",
                    )
                )

        fig_timeline.update_layout(
            barmode="overlay",
            height=max(300, len(trip_timeline) * 30),
            xaxis_title="Time (seconds from midnight)",
            yaxis_title="Station",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )
        st.plotly_chart(fig_timeline, width="stretch")
    else:
        st.info("No timeline data for selected trip.")

st.markdown("---")
st.subheader("📋 Detailed Data View")
view_option = st.radio(
    "Select View",
    ["Trip Data", "Delay Deltas", "Statistics by Station", "Statistics by Direction"],
)
if view_option == "Trip Data":
    display_cols = [
        "Trip",
        "direction",
        "Destination",
        "Platform",
        "base_station",
        "Sched. Arr.",
        "Actual Arr.",
        "Variance",
        "variance_seconds",
    ]
    st.dataframe(
        filtered_df[[c for c in display_cols if c in filtered_df.columns]].head(50),
        width="stretch",
    )
elif view_option == "Delay Deltas":
    st.dataframe(filtered_deltas.head(50), width="stretch")
elif view_option == "Statistics by Station":
    station_stats = (
        filtered_df.groupby("base_station")
        .agg(
            {
                "variance_seconds": ["mean", "max", "min", "count"],
                "dwell_variance": "mean",
            }
        )
        .round(2)
    )
    station_stats.columns = [
        "Avg Delay (s)",
        "Max Delay (s)",
        "Min Delay (s)",
        "Count",
        "Avg Dwell Var (s)",
    ]
    all_stations = STATION_SEQUENCE_DOWN[1:]
    station_stats = station_stats.reindex(
        [s for s in all_stations if s in station_stats.index]
    )
    st.dataframe(station_stats, width="stretch")
else:
    direction_stats = (
        filtered_df.groupby("direction")
        .agg(
            {
                "variance_seconds": ["mean", "max", "min", "count"],
                "dwell_variance": "mean",
                "Trip": "nunique",
            }
        )
        .round(2)
    )
    direction_stats.columns = [
        "Avg Delay (s)",
        "Max Delay (s)",
        "Min Delay (s)",
        "Records",
        "Avg Dwell Var (s)",
        "Trips",
    ]
    st.dataframe(direction_stats, width="stretch")

st.markdown("---")
st.markdown("""
**Dashboard Guide:**
- **DOWN Direction (UTR→CEN)**: Trains traveling from depot/UTR towards Central
- **UP Direction (CEN→UTR)**: Trains traveling from Central towards depot/UTR
- **Delay Accumulation**: Shows how delay builds up along the journey for each trip
- **Delay Delta**: Positive values indicate delay increase (culprits), negative indicates recovery
- **Heatmap**: Quick overview of delay patterns across all trips and stations
- **Dwell Time**: Time spent at station vs scheduled - positive variance means longer stops
- **Culprits**: Segments where delay increases significantly (threshold configurable in sidebar)
""")
