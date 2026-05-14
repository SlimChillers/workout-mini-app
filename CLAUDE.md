# Workout Mini App — Architecture & Development Guide

## Architecture

- **Static HTML app** — a single `index.html` file with embedded CSS and JS. No build step, no framework, no server.
- **Telegram Mini App** — opens inside Telegram's in-app browser via a WebApp button. Uses the [Telegram Web App SDK](https://core.telegram.org/bots/webapps) loaded from CDN.
- **Data flow**: User fills form → `Tg.sendData(JSON.stringify(payload))` → bot receives `web_app_data` update → bot processes (Google Sheets, DB, etc.)
- **Theme**: Auto-detects Telegram theme colors and applies them via CSS custom properties. Falls back to dark theme defaults for non-Telegram preview.

## Key Deployment

- **Hosting**: GitHub Pages (free, HTTPS, no server)
- **Repo**: `dilipjdaniel-ui/workout-mini-app` (public)
- **Branch**: `main`
- **Pages source**: `main` branch, root directory (`/`)
- **URL**: `https://dilipjdaniel-ui.github.io/workout-mini-app/`
- **Deploy**: Push to `main` → GitHub Pages auto-deploys

To register with BotFather:
```
/mybots → select bot → Bot Settings → Menu Button
→ Set URL to https://dilipjdaniel-ui.github.io/workout-mini-app/
```

## Code Standards

### Data Submission
- **Always use `Tg.sendData()`** — never `fetch()` for submitting workout data. The mini app runs in Telegram's webview; there is no backend to receive HTTP requests. Data MUST flow through the Telegram Web App SDK.
- Data flows one direction: app → bot. After `Tg.sendData()`, close the app with `Tg.close()`.

### Tg Object Safety
- **Always check `window.Telegram.WebApp` exists** before calling `Tg.ready()`, `Tg.expand()`, etc. The app may be opened in a regular browser for preview.
- Provide a mock `Tg` object with no-op functions when the SDK is unavailable.
- Show a banner "📱 Open in Telegram for full functionality" when not in Telegram.

### Data Contract
Workout log payload structure:
```json
{
  "type": "workout_log",
  "date": "2026-05-13",
  "workout": "Day A",
  "exercises": [
    {"name": "Leg Press", "weight": 100, "reps": 12, "sets": 3, "skipped": false}
  ],
  "cardio_type": "Treadmill",
  "cardio_min": 20,
  "notes": "Felt strong today"
}
```

### Design
- Dark theme by default with light mode via `prefers-color-scheme`
- Large touch targets (44px+ minimum)
- Fixed submit bar at bottom with gradient fade
- Keep the existing visual design intact — minimal, functional, no decorative cruft
