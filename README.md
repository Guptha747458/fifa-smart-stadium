# StadiumGenius AI

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![WebSockets](https://img.shields.io/badge/Real--time-WebSockets-2F80ED)
![Accessibility](https://img.shields.io/badge/Accessibility-WCAG%202.1%20AA-6A5ACD)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

AI-powered stadium operations and fan experience platform for large-scale events.

## Overview
StadiumGenius AI combines real-time operations, multilingual assistance, and accessibility-first navigation to support fans, staff, and organizers.

## Highlights
- Smart wayfinding and accessibility-first routing
- Predictive crowd monitoring and alerts
- Real-time multilingual support
- Organizer decision-support dashboard
- Live simulator-driven updates via WebSockets

## Stack
- Python, FastAPI, Uvicorn
- Pydantic, NumPy
- Jinja2, WebSockets
- Pytest

## Quick start
```bash
pip install -r requirements.txt
python -m sim.run --seed 42
python -m api.server
```

Open: `http://localhost:8000`

## Docker
```bash
docker build -t stadiumgenius-ai .
docker run -p 8000:8000 -e PORT=8000 stadiumgenius-ai
```

## Testing
```bash
pytest
```
