# Garage Manager

Desktop application for **automotive workshops**: clients, vehicles, work orders, appointments, expenses, income, and reports. Business logic lives in a **service layer** over **SQLite**; the UI is built with **PySide6** (Qt for Python).

## Features

- Workshop / work orders workflow  
- Agenda and scheduling  
- Reports (charts via **matplotlib**)  
- **SQLite** database with schema migrations on startup  
- **English / Spanish** UI strings via `locale/` and `LanguageService`  
- Themed desktop UI (`ui/theme/`)

## Requirements

- **Python 3.10+** (3.12+ recommended; tested with 3.13 locally)  
- Windows paths are assumed for the default user data directory (`%LOCALAPPDATA%\GarageManager`); the app may run elsewhere with adjusted environment.

## Quick start

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m ui
```

Optional: smoke-test the service layer from the repo root:

```bash
python main.py
```

## Tests

```bash
pytest
```

## Project layout

```
GarageManager/
├── database/           # SQLite connection, schema.sql, bootstrap
├── services/           # Business logic (CRUD and workflows)
│   ├── client_service.py
│   ├── vehicle_service.py
│   ├── order_service.py
│   ├── order_item_service.py
│   ├── appointment_service.py
│   ├── expense_service.py
│   ├── income_service.py
│   ├── report_service.py
│   └── language_service.py
├── ui/                 # PySide6 application
│   ├── __main__.py     # App entry: python -m ui
│   ├── main_window.py
│   ├── views/
│   ├── theme/
│   └── widgets/
├── locale/             # en.json, es.json
├── tests/              # pytest
├── main.py             # Console demo of services (development)
├── requirements.txt
├── GarageManager.spec  # PyInstaller onedir build
└── readme.md
```

## Building a Windows executable (optional)

With PyInstaller installed:

```bash
pip install pyinstaller
pyinstaller GarageManager.spec
```

Output is under `dist/GarageManager/`. Do not commit `build/` or `dist/`; they are local build artifacts.

## Architecture notes

- **Separation of concerns:** `services/` holds business rules; persistence goes through `database/connection.py`.  
- **UI** consumes services and does not own domain rules.  
- **Scalability:** the same service layer can back other front ends (e.g. web) if added later.

## License

Add a `LICENSE` file if you publish this repository publicly.
