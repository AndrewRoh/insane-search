# Walkthrough - Insane Search Web UI Playground

We have successfully implemented a web-based playground application for `insane-search` in the current project directory.

## Accomplishments

1.  **Backend Setup (`app/main.py`)**:
    - Created a FastAPI application that serves the static frontend files and exposes a JSON API endpoint at `POST /api/fetch`.
    - Integrated python path configuration to load the `engine` module dynamically from `skills/insane-search/engine`.
    - Refactored the endpoint to a synchronous `def` function (so FastAPI automatically runs it in a background thread pool) to prevent blocking the async event loop during WAF Grid search fetches.
2.  **Frontend Interface (`app/static/`)**:
    - `index.html`: Designed a dashboard layout with a parameter control panel (collapsible advanced section) and a results pane with tabbed views (Visual Preview, Attempt Trace, Raw HTML, JSON).
    - `style.css`: Implemented a dark theme using glassmorphism, smooth animations, and a responsive CSS grid layout.
    - `app.js`: Handled dynamic API calls, loading indicators, and mapping output arrays to trace tables and preview elements.

## Verification & Testing

1.  **FastAPI Server Start**:
    - Successfully launched the server in the background using `uv run`.
    - Log verified: `INFO: Uvicorn running on http://127.0.0.1:8000`
2.  **API Retrieval Test**:
    - Sent a test API request to `http://127.0.0.1:8000/api/fetch` to fetch `https://example.com`.
    - The server successfully called `engine.fetch()` under the hood and returned the full trace and HTML content:
      ```json
      {
        "ok": true,
        "final_url": "https://example.com/",
        "verdict": "weak_ok",
        "trace": [
          {
            "phase": "probe",
            "executor": "curl_cffi",
            "url": "https://example.com",
            "status": 200,
            "verdict": "weak_ok"
          }
        ]
      }
      ```

## How to Run

To start the Web UI playground, execute the following command in PowerShell from the project root:

```powershell
$env:PYTHONPATH="skills/insane-search"; $env:PYTHONIOENCODING="utf-8"; uv run --with fastapi --with uvicorn --with pydantic --with curl_cffi --with beautifulsoup4 --with pyyaml python app/main.py
```

Then, open your web browser and navigate to:
**`http://127.0.0.1:8000`**
