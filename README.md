# VISTA — Visual Intelligent Smart Traffic Advisor

VISTA is a proof-of-concept operator dashboard that combines annotated traffic
video, incident evidence, traffic-flow forecasting, and advisory signal timing.
The default frontend mode uses recorded video and synthetic SCATS-format data so
the complete presentation can run without external services.

## Frontend architecture

| File | Responsibility |
|---|---|
| `frontend/App.py` | Streamlit page composition and operator interactions |
| `frontend/config.py` | Environment variables, filesystem paths, and assets |
| `frontend/data_service.py` | Mock/live API adapters and data normalization |
| `frontend/styles.py` | Safe loading of the dashboard stylesheet |
| `frontend/styles.css` | Visual design system and responsive styling |

This separation keeps the UI independent from the M1 Vision and M2 Forecasting
transport details while preserving one consistent data shape in mock and live
modes.

## Run the demo

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r frontend\requirements.txt
streamlit run frontend\App.py
```

Open `http://localhost:8501`. Set `MOCK_MODE=false` only when the live services
configured in `frontend/config.py` are running.
