# 🚀 Deployment Guide

This system is optimized for free/low-cost deployment on platforms like Render, Railway, or Fly.io.

## 🛠️ Option 1: Render.com (Recommended)

1.  **Push Code**: Commit all changes to your GitHub repository.
2.  **Dashboard**: Go to [dashboard.render.com](https://dashboard.render.com/).
3.  **Blueprints**: Click "New" -> "Blueprint".
    -   Connect your GitHub repo.
    -   Render will automatically detect `render.yaml`.
4.  **Apply**: It will create 3 services:
    -   `forecasting-api` (The Web Service)
    -   `daily-automation` (Cron Job)
    -   `weekly-training` (Cron Job)

### Environment Variables
The `render.yaml` sets defaults, but for production you should override:
-   `DATABASE_URL`: Your MongoDB URI (if using Mongo) or keep default for SQLite (note: SQLite resets on redeploy in free tier).
-   `API_KEY`: If you add auth later.

## ⏳ Cron Schedules
-   **Daily Automation**: Runs at **08:00 UTC** every day.
    -   Updates Market Data.
    -   Runs Walk-Forward Analysis.
    -   Updates System Status.
-   **Weekly Training**: Runs at **09:00 UTC on Sundays**.
    -   Retrains Regime Classifier.
    -   Retrains Deep Learning models.
    -   Optimizes LightGBM Parameters.

## 📡 Monitoring
Once deployed, check your system health at:
`https://<your-app-url>.onrender.com/system/status`
(Or use the Frontend Dashboard "System Status" tab).
