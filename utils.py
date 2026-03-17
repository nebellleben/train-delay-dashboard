import pandas as pd
import numpy as np
import re

STATION_SEQUENCE_DOWN = [
    "UTR",
    "TSW",
    "TWH",
    "KWH",
    "KWF",
    "LAK",
    "MEF",
    "LCK",
    "CSW",
    "SSP",
    "PRE",
    "MOK",
    "YMT",
    "JOR",
    "TST",
    "ADM",
    "CEN",
]
STATION_SEQUENCE_UP = [
    "CEN",
    "ADM",
    "TST",
    "JOR",
    "YMT",
    "MOK",
    "PRE",
    "SSP",
    "CSW",
    "LCK",
    "MEF",
    "LAK",
    "KWF",
    "KWH",
    "TWH",
    "TSW",
    "UTR",
]


def time_to_seconds(time_str):
    if pd.isna(time_str) or time_str == "" or time_str is None:
        return None
    parts = str(time_str).split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return None


def seconds_to_time(seconds):
    if seconds is None or pd.isna(seconds):
        return "--:--"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def seconds_to_hms(seconds):
    if seconds is None or pd.isna(seconds):
        return "--:--:--"
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}"


def extract_base_station(platform):
    if pd.isna(platform):
        return None
    platform = str(platform)
    match = re.match(r"^([A-Z]+)", platform)
    if match:
        return match.group(1)
    return platform


def load_data():
    df = pd.read_csv("data/sample.csv")
    stations_df = pd.read_csv("data/stations.csv", header=None, names=["station"])
    station_order = stations_df["station"].tolist()
    return df, station_order


def get_direction(destination):
    if destination == "CEN":
        return "down"
    elif destination == "TSW":
        return "up"
    return "unknown"


def get_station_sequence_for_direction(direction):
    if direction == "down":
        return STATION_SEQUENCE_DOWN
    elif direction == "up":
        return STATION_SEQUENCE_UP
    return STATION_SEQUENCE_DOWN


def process_data(df, station_order):
    df = df.copy()
    df["base_station"] = df["Platform"].apply(extract_base_station)
    df["variance_seconds"] = df["Variance"].apply(time_to_seconds)
    df["sched_arr_seconds"] = df["Sched. Arr."].apply(time_to_seconds)
    df["sched_dep_seconds"] = df["Sched. Dep."].apply(time_to_seconds)
    df["actual_arr_seconds"] = df["Actual Arr."].apply(time_to_seconds)
    df["actual_dep_seconds"] = df["Actual Dep."].apply(time_to_seconds)
    df["sched_dwell"] = df.apply(
        lambda x: x["sched_dep_seconds"] - x["sched_arr_seconds"]
        if pd.notna(x["sched_dep_seconds"]) and pd.notna(x["sched_arr_seconds"])
        else None,
        axis=1,
    )
    df["actual_dwell"] = df.apply(
        lambda x: x["actual_dep_seconds"] - x["actual_arr_seconds"]
        if pd.notna(x["actual_dep_seconds"]) and pd.notna(x["actual_arr_seconds"])
        else None,
        axis=1,
    )
    df["dwell_variance"] = df.apply(
        lambda x: x["actual_dwell"] - x["sched_dwell"]
        if pd.notna(x["actual_dwell"]) and pd.notna(x["sched_dwell"])
        else None,
        axis=1,
    )
    df["direction"] = df["Destination"].apply(get_direction)
    df["station_order"] = df.apply(
        lambda row: get_station_sequence_for_direction(row["direction"]).index(
            row["base_station"]
        )
        if row["base_station"] in get_station_sequence_for_direction(row["direction"])
        else -1,
        axis=1,
    )
    df["stop_number"] = df.groupby("Trip").cumcount() + 1
    return df


def calculate_delay_deltas(df):
    deltas = []
    for trip in df["Trip"].unique():
        trip_df = (
            df[df["Trip"] == trip].sort_values("station_order").reset_index(drop=True)
        )
        for i in range(1, len(trip_df)):
            prev_variance = trip_df.iloc[i - 1]["variance_seconds"]
            curr_variance = trip_df.iloc[i]["variance_seconds"]
            if pd.notna(prev_variance) and pd.notna(curr_variance):
                delta = curr_variance - prev_variance
                deltas.append(
                    {
                        "Trip": trip,
                        "Direction": trip_df.iloc[i]["direction"],
                        "From_Station": trip_df.iloc[i - 1]["base_station"],
                        "To_Station": trip_df.iloc[i]["base_station"],
                        "segment": f"{trip_df.iloc[i - 1]['base_station']} → {trip_df.iloc[i]['base_station']}",
                        "delta_seconds": delta,
                        "delta_time": seconds_to_time(delta),
                        "prev_variance": prev_variance,
                        "curr_variance": curr_variance,
                    }
                )
    return pd.DataFrame(deltas)


def get_summary_stats(df):
    stats = {
        "total_trips": df["Trip"].nunique(),
        "avg_delay": df["variance_seconds"].mean(),
        "max_delay": df["variance_seconds"].max(),
        "min_delay": df["variance_seconds"].min(),
        "total_records": len(df),
    }

    station_avg = df.groupby("base_station")["variance_seconds"].mean().to_dict()
    if station_avg:
        stats["worst_station"] = max(station_avg, key=station_avg.get)
        stats["best_station"] = min(station_avg, key=station_avg.get)
        stats["worst_station_delay"] = station_avg[stats["worst_station"]]
        stats["best_station_delay"] = station_avg[stats["best_station"]]

    journey_delays = calculate_station_journey_delay(df)
    if journey_delays:
        stats["worst_journey_station"] = max(journey_delays, key=journey_delays.get)
        stats["best_journey_station"] = min(journey_delays, key=journey_delays.get)
        stats["worst_journey_delay"] = journey_delays[stats["worst_journey_station"]]
        stats["best_journey_delay"] = journey_delays[stats["best_journey_station"]]

    return stats


def calculate_station_journey_delay(df):
    station_delays = {}

    for trip in df["Trip"].unique():
        trip_df = (
            df[df["Trip"] == trip].sort_values("station_order").reset_index(drop=True)
        )

        for i in range(len(trip_df)):
            row = trip_df.iloc[i]
            station = row["base_station"]

            if pd.notna(row["dwell_variance"]):
                if station not in station_delays:
                    station_delays[station] = []
                station_delays[station].append(row["dwell_variance"])

    station_avg_delays = {}
    for station, delays in station_delays.items():
        if len(delays) >= 1:
            station_avg_delays[station] = np.mean(delays)

    return station_avg_delays


def get_top_culprits(deltas_df, n=5):
    if deltas_df.empty:
        return pd.DataFrame()
    culprits = deltas_df[deltas_df["delta_seconds"] > 30].copy()
    culprits = culprits.sort_values("delta_seconds", ascending=False).head(n)
    return culprits


def get_recovery_points(deltas_df, n=5):
    if deltas_df.empty:
        return pd.DataFrame()
    recovery = deltas_df[deltas_df["delta_seconds"] < 0].copy()
    recovery = recovery.sort_values("delta_seconds", ascending=True).head(n)
    return recovery
