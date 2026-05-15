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
    {"name": "Leg Press", "weight": 100, "reps": 12, "sets": 3, "skipped": false, "substituted_for": null}
  ],
  "cardio_type": "Treadmill",
  "cardio_min": 20,
  "notes": "Felt strong today"
}
```

- `substituted_for` is the *original planned* exercise when the user swapped (e.g. `"Leg Press"` if they performed Hack Squat instead). The actual exercise performed lives in `name`. The bot logs the swap as `[sub for <original>]` in the Notes column so PR/plateau detection keys off the actually-performed exercise.

### URL params (bot → mini app)
The bot's `_send_workout_button` constructs the WebApp URL with these query params:
- `prev=<base64>` — JSON of `{exerciseName: [weight, reps, sets]}` for last-session pre-fill
- `day=A|B` and `ago=<days>` — next-day suggestion + last session recency
- `sets=<n>&reps=<n>` — current program-phase rep scheme (Phase 10)
- `deload=1` — set when `_should_deload` fires (≥9 sessions AND ≥2 plateaued lifts); mini app renders a banner with a one-tap "Apply" that scales weights × 0.9 and drops a set when current sets ≥ 3
- `subs=<base64>` — JSON of `{exerciseName: [alt1, alt2, ...]}` so the mini app's swap menu can offer alternatives; catalog is owned by the bot (`SUBSTITUTES` constant in `telegram_workout.py`) so it can be updated without a Pages redeploy
- `next=<base64>` — JSON of `{exerciseName: [suggestedWeight, reason]}` for auto-progression (Phase 13). `reason ∈ {"progress", "hold"}`. When present, the mini app uses `suggestedWeight` as the weight input's pre-filled value (overriding `prev`) and renders a coloured badge: green "↑ +N (hit target)" for `"progress"`, grey "hold (didn't hit target)" for `"hold"`. Omitted on deload weeks — the bot's `_get_next_weights` returns `{}` when `_should_deload` fires, so the mini app falls back to the legacy "+2.5 chip"
- `deload_reason=planned|reactive` — paired with `deload=1` (Phase 15). `planned` = Week 4 of the 24-session mesocycle (`_is_planned_deload`); `reactive` = Phase 12 plateau trigger (`_should_deload`). Mini app uses this to pick banner copy: planned shows "Planned deload week" / scheduled-rest subtitle, reactive shows "Deload recommended" / plateau-detected subtitle. Defaults to `reactive` for backward compat with older bot versions.

### Design
- Dark theme by default with light mode via `prefers-color-scheme`
- Large touch targets (44px+ minimum)
- Fixed submit bar at bottom with gradient fade
- Keep the existing visual design intact — minimal, functional, no decorative cruft
