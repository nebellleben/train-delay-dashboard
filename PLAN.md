# Train Delay Dashboard Implementation Plan

## Overview

An interactive Streamlit dashboard to analyze train delay patterns, identify delay culprits, and visualize delay accumulation across the West Rail Line (TSW ↔ CEN).

## Data Structure

### sample.csv
| Column | Description |
|--------|-------------|
| un | Unique identifier (59 for all records) |
| Trip | Trip number (979, 1044, 1043, 1288, 1287, 1536) |
| Destination | End station (TSW or CEN) |
| Platform | Platform code with suffix |
| Sched. Arr. | Scheduled arrival time |
| Sched. Dep. | Scheduled departure time |
| Actual Arr. | Actual arrival time |
| Actual Dep. | Actual departure time |
| Variance | Accumulated delay (MM:SS format) |

### stations.csv
Ordered list of stations from TSW (1) to CEN (16):
```
TSW → TWH → KWH → KWF → LAK → MEF → LCK → CSW → SSP → PRE → MOK → YMT → JOR → TST → ADM → CEN
```

## Key Metrics

### 1. Delay Accumulation
- **Definition**: Cumulative delay at each station (Variance column)
- **Purpose**: Track how delay builds up along the journey

### 2. Delay Delta (Culprit Detection)
- **Definition**: `Variance[i] - Variance[i-1]` between consecutive stations
- **Purpose**: Identify which station segments cause delay spikes
- **Threshold**: Delta > 30 seconds = potential culprit

### 3. Dwell Time
- **Definition**: `Actual Dep - Actual Arr` at each station
- **Purpose**: Measure time spent at station (vs scheduled dwell)
- **Scheduled Dwell**: `Sched. Dep - Sched. Arr`

### 4. Travel Time
- **Definition**: `Next Station Arr - Current Station Dep`
- **Purpose**: Measure inter-station travel performance

### 5. Recovery Score
- **Definition**: Stations where Delay Delta < 0
- **Purpose**: Identify where train recovers time

## Visualizations

### 1. Delay Accumulation Chart (Cumulative Inter-Station Delay)
- **Type**: Two separate line charts (one for DOWN, one for UP direction)
- **X-axis**: Stations (in travel order for each direction)
- **Y-axis**: Cumulative delay delta (seconds), starting from 0 at first recorded station
- **Color**: By Trip number, with distinct colors for each direction
- **Features**: 
  - Hover to see exact cumulative delta values
  - Shows how delay accumulates from inter-station segments
  - 5-minute and 10-minute threshold lines
  - Separate charts for DOWN (UTR→CEN) and UP (CEN→UTR) directions

### 2. Delay Delta Bar Chart (Culprit Finder)
- **Type**: Bar chart
- **X-axis**: Station segments (e.g., "TST → JOR")
- **Y-axis**: Delay delta (seconds)
- **Color**: Red for positive (delay), green for negative (recovery)
- **Features**: Sort by delta, highlight top culprits

### 3. Station Performance Heatmap
- **Type**: Heatmap
- **X-axis**: Trips
- **Y-axis**: Stations
- **Color**: Variance intensity
- **Purpose**: Quick identification of problem stations

### 4. Timeline Comparison (Gantt-style)
- **Type**: Horizontal bar chart
- **Shows**: Scheduled vs Actual timeline for selected trip
- **Purpose**: Visual comparison of timing deviations

### 5. Summary Statistics Panel
- Total trips analyzed
- Average delay per trip
- Worst performing station
- Best performing station
- Total delay minutes

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Train Delay Analysis Dashboard                              │
├─────────────────────────────────────────────────────────────┤
│  [Trip Selector] [Direction Filter] [Time Range]             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────────────┐   │
│  │  Summary Stats      │  │  Top Culprits               │   │
│  │  - Avg Delay: 6:23  │  │  1. SSP → PRE (+3:49)       │   │
│  │  - Worst: SSP       │  │  2. CSW → SSP (+2:15)       │   │
│  │  - Best: TWH        │  │  3. MEF → LAK (+1:58)       │   │
│  └─────────────────────┘  └─────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Delay Accumulation Chart (Line)                       │  │
│  │  [Interactive: hover, zoom, toggle trips]              │  │
│  └───────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────────────┐  ┌────────────────────────────┐ │
│  │  Delay Delta (Bar)     │  │  Station Heatmap           │ │
│  │  [Identify culprits]   │  │  [Overview all trips]      │ │
│  └────────────────────────┘  └────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Timeline Comparison (Gantt)                           │  │
│  │  [Selected trip: scheduled vs actual]                  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Phase 1: Setup
1. Create project directory structure
2. Install dependencies (streamlit, pandas, plotly, numpy)
3. Copy data files

### Phase 2: Data Processing (utils.py)
1. Load and parse CSV files
2. Convert time strings to seconds
3. Calculate delay deltas
4. Map platforms to base station codes
5. Sort stations by sequence

### Phase 3: Core Dashboard (app.py)
1. Set up Streamlit layout
2. Create sidebar filters
3. Implement summary statistics
4. Build delay accumulation chart
5. Build delay delta chart
6. Build heatmap
7. Build timeline comparison

### Phase 4: Interactivity
1. Trip selection dropdown
2. Direction filter
3. Time range slider
4. Chart hover interactions
5. Download data option

### Phase 5: Polish
1. Color scheme and styling
2. Responsive layout
3. Performance optimization
4. Error handling
5. Documentation

## Technical Details

### Time Conversion
```python
def time_to_seconds(time_str):
    if pd.isna(time_str) or time_str == '':
        return None
    parts = time_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])

def seconds_to_time(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"
```

### Station Mapping
Extract base station code from platform:
- `TST1` → `TST`
- `KWH_44` → `KWH`
- `CEN_24` → `CEN`

### Direction Detection
- Destination = `TSW` → Direction: CEN to TSW (reverse order)
- Destination = `CEN` → Direction: TSW to CEN (normal order)

## Dependencies

```
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.18.0
numpy>=1.24.0
```

## Running the Dashboard

```bash
cd train_delay_dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Future Enhancements

1. **Historical Analysis**: Compare multiple days/weeks
2. **Incident Integration**: Overlay incident reports
3. **Predictive Model**: Predict delays based on patterns
4. **Alert System**: Real-time delay notifications
5. **Export Reports**: PDF/Excel report generation
6. **Weather Correlation**: Include weather data
7. **Passenger Load**: Integrate ridership data
