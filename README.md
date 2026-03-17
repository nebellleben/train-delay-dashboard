# Train Delay Analysis Dashboard

Interactive Streamlit dashboard for analyzing train delay patterns and identifying delay culprits on the West Rail Line (TSW ↔ CEN).

## Features

- **Delay Accumulation Charts**: Separate visualizations for UP/DOWN directions
- **Station Delay Heatmaps**: By direction with stations in travel order
- **Dwell Time Variance Analysis**: Identify stations with longer-than-scheduled stops
- **Journey Time Breakdown**: Stacked bar charts showing time per station segment
- **Delay Culprit Detection**: Identifies segments causing significant delays
- **Recovery Point Analysis**: Shows where trains recover time
- **Timeline Comparison**: Scheduled vs actual timeline for selected trips
- **Interactive Filters**: Filter by trip, direction, time range, and culprit threshold

## Line Configuration

- **DOWN** (UTR → CEN): UTR → TSW → TWH → KWH → KWF → LAK → MEF → LCK → CSW → SSP → PRE → MOK → YMT → JOR → TST → ADM → CEN
- **UP** (CEN → UTR): CEN → ADM → TST → JOR → YMT → MOK → PRE → SSP → CSW → LCK → MEF → LAK → KWF → KWH → TWH → TSW → UTR

## Local Development

```bash
# Clone the repository
git clone https://github.com/nebellleben/train-delay-dashboard.git
cd train-delay-dashboard

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run app.py
```

Dashboard will be available at http://localhost:8501

## Data Format

### sample.csv
| Column | Description |
|--------|-------------|
| un | Unique identifier |
| Trip | Trip number |
| Destination | End station (TSW or CEN) |
| Platform | Platform code with suffix |
| Sched. Arr. | Scheduled arrival time (HH:MM:SS) |
| Sched. Dep. | Scheduled departure time (HH:MM:SS) |
| Actual Arr. | Actual arrival time (HH:MM:SS) |
| Actual Dep. | Actual departure time (HH:MM:SS) |
| Variance | Accumulated delay (MM:SS) |

### stations.csv
Ordered list of stations from TSW to CEN (one per line).

## Deployment

This dashboard is configured for deployment to Streamlit Cloud via GitHub Actions.

### Automatic Deployment

The dashboard automatically deploys to Streamlit Cloud when:
- Changes are pushed to the `main` branch
- GitHub Actions workflow is triggered

### Manual Deployment

1. Go to [Streamlit Cloud](https://share.streamlit.io/)
2. Create a new app
3. Connect your GitHub repository
4. Select the repository and branch
5. Deploy

## CI/CD Pipeline

The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that automatically deploys to Streamlit Cloud on every push to the main branch.

### Required Secrets

Add these secrets to your GitHub repository:
1. Go to Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `STREAMLIT_SHARING_BASE_URL`: Your Streamlit Cloud sharing URL
   - `STREAMLIT_SHARING_API_KEY`: Your Streamlit Cloud API key

To get these values:
1. Deploy manually once on Streamlit Cloud
2. Check the deployment settings for the sharing URL
3. Generate an API key from your Streamlit Cloud settings

## Key Findings from Sample Data

| Metric | Value |
|--------|-------|
| Top Delay Culprit | PRE → SSP (+3:59 on Trip 979) |
| Worst Station (Journey Delay) | UTR (+27.0s avg) |
| Best Station (Journey Delay) | ADM (-48.6s avg) |
| Total Trips Analyzed | 6 |

## Technology Stack

- **Frontend**: Streamlit (Python)
- **Visualization**: Plotly
- **Data Processing**: Pandas, NumPy
- **Deployment**: Streamlit Cloud
- **CI/CD**: GitHub Actions
