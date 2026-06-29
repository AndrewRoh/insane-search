# Task List - Insane Search Web UI Playground Updates

- [x] **YouTube Subtitles Engine Support**
  - [x] Modify `skills/insane-search/engine/phase0.py` `_youtube` to fallback to `sys.executable -m yt_dlp`
  - [x] Implement subtitles parsing (ko/en) from timedtext URL in `_youtube`
  - [x] Verify YouTube subtitle parsing works via automated script

- [x] **Playground App Backend Updates**
  - [x] Update `app/main.py` `FetchRequest` to accept `force_playwright` parameter
  - [x] Support `force_playwright` in `api_fetch` by setting `max_attempts = 0`

- [x] **Playground App Frontend Updates**
  - [x] Update `app/static/index.html` with an "Examples" panel in the sidebar
  - [x] Add "Force Playwright" checkbox in the advanced parameters section
  - [x] Update `app/static/app.js` to handle sidebar examples click and auto-populate settings
  - [x] Bind "Force Playwright" checkbox state in API payload

- [x] **Testing & Verification**
  - [x] Verify Example 1 (YouTube subtitles) via local server
  - [x] Verify Example 2 (Naver Shopping) via local server
  - [x] Verify Example 3 (AliExpress) via local server
  - [x] Document final walkthrough
