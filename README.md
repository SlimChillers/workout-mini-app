# Workout Mini App

[![Deployed](https://img.shields.io/badge/Live-GitHub_Pages-181717?logo=github)](https://slimchillers.github.io/workout-mini-app/)

A Telegram Mini App for logging Planet Fitness workouts directly to Google Sheets.

## 🔗 Live App
**https://slimchillers.github.io/workout-mini-app/**

## How it Works
- **Frontend**: `index.html` is a single-file static app. It uses the Telegram Web App SDK.
- **Submission**: User data is sent via `Tg.sendData()` to the Telegram Bot.
- **Storage**: The bot handler (Hermes Agent) extracts data and approws it to Google Sheets via the Google API.

## 🚀 Deployment
- **Host**: GitHub Pages (deployed automatically from the `main` branch).
- **CI/CD**: `.github/workflows/verify.yml` validates the build on every push.

## 📁 Project Structure
- `index.html` — The main application interface.
- `handler.py` / `webhook.py` — Telegram bot webhook handlers (Hermes Agent).
- `server.py` — Optional local development server.

## 🛠 Local Development
```bash
python3 -m http.server 8921
```
Then visit `http://localhost:8921` in your browser.
