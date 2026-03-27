# Drone controller for bitcraze drones
---

### Pre-launch
Prepare python venv to install all necessary packages.
Documentation for uv package manager: https://docs.astral.sh/uv/
```
uv sync
```

#### Options (in progress)
* Launch script
```
uv run api.py ---uri "drone_uri"
```

* Launch with GUI
```
uv run api.py --uri "drone_uri" --gui
```

* Launch with CLI (in progress, not active for now)
```
uv run api.py --uri "drone_uri" --cli
```