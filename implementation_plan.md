# Implementation Plan - Insane Search Web UI Playground Updates

We will update the `insane-search` engine and the Web UI Playground application to support the three user examples:
1. **Example 1: YouTube subtitles and metadata extraction** (YouTube subtitle downloading and cleaning in `engine/phase0.py`).
2. **Example 2: Naver Shopping Hot Deals** (Interactive testing with custom selectors / Playwright fallback).
3. **Example 3: AliExpress Product Data** (Robust visual tracking of challenges and browser fallback).

---

## User Review Required

> [!IMPORTANT]
> - **YouTube Subtitles**: We will modify `engine/phase0.py` to look up available subtitles (prioritizing Korean `ko`, then falling back to English `en`), download the `json3` format timed-text file, clean it into a readable text paragraph, and include it along with metadata in the output `content`.
> - **Playwright/Node Verification**: For local Playwright fallback on sites like Naver Shopping/AliExpress, Node.js and Playwright must be installed. We will ensure the CLI and backend handle environment differences robustly.
> - **Playwright MCP**: If the backend's local Playwright fails or is blocked by Cloudflare/Akamai, the API will output the `must_invoke_playwright_mcp=true` flag. The agent (Claude) can then run MCP browser tools in the current session.

## Open Questions

> [!NOTE]
> 1. Should we add a direct button/checkbox in the Web UI to "Force Playwright Fallback" directly, bypassing the initial curl grid attempts? (This is useful if you know a site definitely needs JS rendering).

---

## Proposed Changes

### 1. YouTube Subtitles Extraction (`engine`)

#### [MODIFY] [phase0.py](file:///e:/Projects/InSaneSearch/skills/insane-search/engine/phase0.py)
- Update `_youtube` to:
  - First attempt running `yt-dlp` from PATH, and if missing/fails, fall back to `sys.executable -m yt_dlp` and `python -m yt_dlp`.
  - Parse the output JSON. Look for available subtitles in `automatic_captions` or `subtitles` (prioritizing `ko`, then `en`).
  - Extract the `json3` timedtext URL and fetch the subtitles content.
  - Parse the timedtext data into a clean, paragraph-formatted transcript text.
  - Set `content` to contain the structured metadata (Title, Channel, Description) followed by the subtitles transcript.

### 2. Playground Web UI Frontend

#### [MODIFY] [index.html](file:///e:/Projects/InSaneSearch/app/static/index.html)
- Add a new **"Quick Examples"** section in the Sidebar containing cards for:
  - **YouTube Subtitle & Metadata Extraction**
  - **Naver Shopping Hot Deals**
  - **AliExpress Products**
- Add a **"Force Playwright"** checkbox under advanced settings.

#### [MODIFY] [app.js](file:///e:/Projects/InSaneSearch/app/static/app.js)
- Add event listeners for the quick examples to populate the URL, selectors, and hints automatically when clicked.
- Handle the **"Force Playwright"** parameter. If checked, send `max_attempts: 0` or similar payload indicator to force immediate Playwright escalation in the backend.

### 3. Playground Web UI Backend

#### [MODIFY] [main.py](file:///e:/Projects/InSaneSearch/app/main.py)
- Update `FetchRequest` to accept `force_playwright: bool = False`.
- In `api_fetch`, if `force_playwright` is `True`, set `max_attempts = 0` to skip the curl grid and trigger the Playwright executor immediately.

---

## Verification Plan

### Automated Tests
- Run tests on YouTube subtitles extraction:
  ```bash
  uv run --with curl_cffi --with pydantic --with beautifulsoup4 --with pyyaml --with yt-dlp python -c "from engine import fetch; res = fetch('https://www.youtube.com/watch?v=vjSZIyYd0NI'); print('ok:', res.ok); print('has subtitles:', 'Subtitles' in res.content)"
  ```

### Manual Verification
- Start the playground server:
  ```bash
  uv run --with fastapi --with uvicorn --with pydantic --with curl_cffi --with beautifulsoup4 --with pyyaml --with yt-dlp python app/main.py
  ```
- Click each of the three Examples in the sidebar.
- Verify that Example 1 retrieves and renders YouTube subtitles in the preview pane.
- Verify that Example 2 and 3 retrieve product data successfully.
