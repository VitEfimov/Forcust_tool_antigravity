# 🚀 Deployment Guide
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
