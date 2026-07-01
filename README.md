# PoolPilot — Intelligenter Pool-Wasser-Rechner

A Streamlit-based web app for pool water chemistry management.  
Track measurements, calculate balance indices (CSI/LSI/RSI), get dosing recommendations, and manage maintenance tasks.

---

## Features

- **Water Chemistry Calculation** — CSI (Wojtowicz), LSI (Langelier), RSI (Ryznar), CCPP with live gauge visualization
- **Dosing Recommendations** — Priority-ordered (alkalinity → pH → hardness → chlorine) with product-specific amounts
- **Measurement History** — Interactive Plotly charts for pH, chlorine, alkalinity, hardness, and balance indices over time
- **Multi-Pool Support** — Manage several pools with independent target ranges
- **Task Management** — Calendar view, recurring template tasks, auto-follow-ups after measurements
- **Instrument Profiles** — Configure which parameters each test kit can measure
- **Tap Water Profiles** — Store local tap water analysis as defaults for alkalinity/hardness
- **Photo Documentation** — Attach camera or upload photos to measurements
- **CSV Export** — Export measurement history
- **Docker & Devcontainer** — One-command setup with VS Code devcontainer support

## Architecture

```
├── Wasserrechner.py         # Main app entry point
├── pages/
│   ├── 01_Poolverwaltung.py # Pool, product, instrument & template admin
│   ├── 02_Verlauf.py        # Measurement history & trends
│   ├── 03_Wartung.py        # Task management
│   └── 04_Kalender.py       # Calendar view
├── pool_calculations/       # Chemistry engine
│   ├── csi.py               # Calcium Saturation Index (Wojtowicz)
│   ├── lsi.py               # Langelier Saturation Index
│   ├── rsi.py               # Ryznar Stability Index
│   ├── dosing.py            # Dosing recommendation logic
│   └── models.py            # Data classes (WaterTest, DosingRecommendation, etc.)
├── database/                # Persistence layer
│   ├── db.py                # SQLAlchemy engine, init, migration, config seeding
│   ├── models.py            # ORM models (Pool, Reading, Product, Task, etc.)
│   └── repository.py        # CRUD operations
├── utils/
│   └── config_loader.py     # TOML config loader
├── config.toml              # Default pool, targets, products, instruments
├── data/                    # SQLite DB + photos (gitignored)
└── tests/                   # 61 tests covering all modules
```

## Quick Start

### Local

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run the app
streamlit run Wasserrechner.py

# Or use Make
make install && make dev
```

### Docker

```bash
make build && make run
# Open http://localhost:8501
```

### VS Code Devcontainer

Open the repo in VS Code with the Dev Containers extension — it auto-installs dependencies, starts Streamlit, and mounts opencode config.

## Configuration

Edit `config.toml` to set your pool defaults before first run:

```toml
[pool]
name = "My Pool"
volume_liter = 10000
pool_type = "chlorine"

[targets]
ph_min = 7.2
ph_max = 7.6
chlorine_min = 0.5
chlorine_max = 3.0
alkalinity_min = 80
alkalinity_max = 120
hardness_min = 150
hardness_max = 250
```

On first start, the app seeds the database from `config.toml`. After that, all configuration is editable through the GUI.

## Development

```bash
make test       # Run all 61 tests
make dev        # Start Streamlit locally
make clean      # Remove DB, caches, containers
make restart    # Docker restart
```

### CI

GitHub Actions runs tests on Python 3.9 and 3.11 on every push/PR (see `.github/workflows/ci.yml`).

## Makefile Targets

| Target         | Description                        |
|----------------|------------------------------------|
| `make install` | Install dependencies               |
| `make dev`     | Run Streamlit locally              |
| `make test`    | Run all tests                      |
| `make build`   | Build Docker image                 |
| `make run`     | Start Docker container             |
| `make stop`    | Stop Docker container              |
| `make logs`    | Follow container logs              |
| `make shell`   | Open bash in running container     |
| `make clean`   | Remove containers, volumes, caches |
| `make help`    | Show all targets                   |

## License

MIT — see [LICENSE](LICENSE)
