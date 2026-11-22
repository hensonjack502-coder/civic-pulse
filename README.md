# Civic Pulse – Your Voice, Your City

Stage 1 adds a Flask API and SQLite database while keeping the existing HTML and CSS design. The current page still contains public information, government scheme links, and the prepared-answer assistant.

## Files

- `index.html` is the web page and contains the existing forms and content sections.
- `styles.css` controls the existing page appearance. A small rule shows API errors and the form's loading state.
- `app.js` sends complaint submissions to Flask, looks up IDs through Flask, refreshes dashboard counts, and keeps the assistant and mobile navigation working.
- `app.py` serves the page and provides the complaint API. It validates submitted fields and saves reports in SQLite.
- `instance/civic_pulse.db` is created automatically when the Flask server first starts. It stores complaints between restarts.
- `requirements.txt` lists the one external package: Flask.
- `test_app.py` checks successful submission and tracking, validation errors, missing IDs, and dashboard totals.
- `.gitignore` keeps the local database and Python cache files out of version control.

## Run it on Windows

Open PowerShell in this folder, then run these commands:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser. Keep the PowerShell window open while you use the page; it is running the local server.

To run the automated checks, open a second PowerShell window in this folder and run:

```powershell
python -m unittest -v
```

If `python` is not recognized on your computer, install Python 3 from python.org and select the option to add it to PATH, then reopen PowerShell.

## API endpoints

- `POST /api/complaints` accepts JSON with `category`, `location`, and `description`. It returns a unique ID and the saved complaint.
- `GET /api/complaints/<id>` returns the matching complaint or a clear 404 message.
- `GET /api/complaints/summary` returns total, pending, and resolved counts for the existing dashboard.

Only the categories already offered by the form are accepted. Each new complaint starts as `Pending`. This demo saves reports to a local SQLite file; it does not notify or connect to a real government office.
