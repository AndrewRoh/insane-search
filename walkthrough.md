# Walkthrough - Insane Search Web UI Playground Updates

We have successfully updated the Insane Search Playground web application and the underlying fetch engine to support YouTube subtitles extraction, dynamic CSR selectors, and interactive example scenarios.

## Accomplishments

### 1. YouTube Subtitles Support (`engine/phase0.py`)
- Modified `_youtube` to run `yt-dlp` from the PATH, falling back to `sys.executable -m yt_dlp` or `python -m yt_dlp` depending on environment availability.
- Implemented timedtext JSON3 subtitle downloading and parsing. If a video contains subtitles (prioritizing Korean `ko` first, then English `en`), the engine fetches and formats the subtitles into a clean paragraph text, which is appended to the video metadata (Title, Channel, Description).

### 2. Windows Encoding Fix (`engine/executor.py`)
- Added `encoding="utf-8"` to the `subprocess.run` call that runs local Node templates. This resolves `UnicodeDecodeError` (e.g. `cp949`) on Korean Windows environments when parsing HTML containing multi-byte characters.

### 3. Playground UI Updates (`app/static/` & `app/main.py`)
- **Quick Examples Panel**: Added a section in the sidebar with one-click templates for:
  1. **YouTube Subtitles**: populates a video URL to test metadata & subtitle extraction.
  2. **Naver Shopping Festa**: populates the Festa URL and CSS selectors to retrieve client-side rendered listings.
  3. **AliExpress Products**: populates the site URL and CSS selectors to test WAF bypass using browser fallback.
- **Force Playwright**: Added a checkbox in the advanced parameters. If checked, the API sends `max_attempts=0` to skip the curl grid and escalate to Playwright directly after the initial probe.

---

## Verification & Testing Results

1. **Example 1: YouTube Subtitles**
   - Fetched `https://www.youtube.com/watch?v=vjSZIyYd0NI`.
   - Verified that the response is returned instantly (`ok: true`, `verdict: strong_ok`) and includes the parsed subtitles in the preview tab:
     ```
     Title: [데모 3] 안개낀 크롬에서 길을 안내해~ 에이전트 전용 웹페이지 리더 Insane-search...
     Channel: 김파고
     Description: ...
     --- Subtitles (ko) ---
     안녕하십니까 김파고 입니다...
     ```

2. **Example 2 & 3: Naver Shopping & AliExpress (Playwright fallback)**
   - Ran with selectors and `force_playwright=true`.
   - Verified that local Node `playwright_real_chrome.js` launched, loaded the pages, and extracted fully rendered product HTML.

---

## How to Run

1. Make sure Node.js dependencies are installed:
   ```bash
   npm install playwright playwright-extra puppeteer-extra-plugin-stealth
   npx playwright install chrome
   ```
2. Start the FastAPI server:
   ```bash
   $env:PYTHONPATH="skills/insane-search"; $env:PYTHONIOENCODING="utf-8"; uv run --with fastapi --with uvicorn --with pydantic --with curl_cffi --with beautifulsoup4 --with pyyaml --with yt-dlp python app/main.py
   ```
3. Open `http://localhost:8000` in your web browser.
