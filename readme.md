# Garage Manager

Desktop application for **automotive workshops**: clients, vehicles, work orders, appointments, expenses, income, and reports. Business logic lives in a **service layer** over **SQLite**; the UI is built with **PySide6** (Qt for Python).

## Features

- Workshop / work orders workflow (pending → completed or cancelled), walk-in orders without an appointment, and corrections of completed orders  
- Agenda and scheduling, with a configurable number of cars per time slot (sidebar); appointments sent to the workshop ("In workshop") or marked "Did not attend" stay as history  
- Client and vehicle editing from the Agenda contact list  
- Reports (charts via **matplotlib**); ledgers list manual entries (editable) and the completed orders behind the totals  
- **SQLite** database with versioned migrations (`PRAGMA user_version`), applied once at startup  
- **English / Spanish** UI strings via `locale/` and `LanguageService`; the chosen language is remembered (first start: system language, Spanish by default), and amounts/dates follow it (`$ 1.234,56`, `31/10/2026`)  
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

From the repo root:

```bash
pytest
```

Tests use a temporary database, never your real data. `tests/test_known_bugs.py`
lists known bugs as `xfail(strict=True)`: they are expected to fail until fixed.
When a fix makes one pass, pytest reports it as an error so the marker gets removed.

## Changing the database schema

1. Update `database/schema.sql` (used to create new databases at the latest version).
2. Add a function with the next version number to `MIGRATIONS` in
   `database/migrations.py` (used to upgrade existing databases).
3. Add a test in `tests/test_migrations.py` that upgrades an older database.

Each migration runs once, inside a transaction together with the version bump.
A database written by a newer app version is refused instead of being modified.

## Data, backups and logs

Everything lives in `%LOCALAPPDATA%\GarageManager\`:

| File | Purpose |
|---|---|
| `garage_manager.db` | The SQLite database |
| `backups\garage_manager_YYYY-MM-DD.db` | Automatic copy made on the first start of each day; the 14 most recent are kept |
| `garage_manager.log` | Startup info and any unexpected error with its full traceback (rotates at 1 MB, 5 files) |

To restore a backup: close the app, replace `garage_manager.db` with the chosen
copy (renamed to `garage_manager.db`), and start the app again.

Backups are stored on the same disk as the database: they protect against mistakes
and corrupted files, not against a disk failure. Copy the `backups` folder
elsewhere from time to time.

## Project layout

```
GarageManager/
├── database/           # SQLite connection, schema.sql, versioned migrations, daily backup
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
│   ├── error_handling.py  # Log file + global handler for unexpected errors
│   ├── views/
│   ├── theme/
│   └── widgets/
├── locale/             # en.json, es.json
├── tests/              # pytest
├── main.py             # Console demo of services (development)
├── requirements.txt
├── pyproject.toml      # pytest configuration
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


