# 🚀 Deployment & Independent Scheduling Guide

## 🛑 The Problem: "Server Stops When Machine Sleeps"
If you run the application locally (on your personal computer), the server **must stops** when your computer goes to sleep. This is unavoidable for local execution.

**To run the scheduler independently (24/7), you must use Cloud Automation.**

## ✅ The Solution: GitHub Actions + MongoDB
We have built-in support for **GitHub Actions**, which run your daily automation tasks on GitHub's servers. This works even if your computer is off.

### Prerequisites
1.  **MongoDB Atlas**: You must use a Cloud Database (not local SQLite) so both your App and the Worker can access the same data.
2.  **GitHub Repository**: Your code must be pushed to GitHub.

### Step 1: Configure MongoDB
1.  Create a free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster.
2.  Get your Connection String (URI).
3.  Update your local `.env` to use it (for testing):
    ```env
    DATABASE_URL=mongodb+srv://<user>:<pass>@cluster...
    STORAGE_TYPE=mongo
    ```

### Step 2: Configure GitHub Secrets
1.  Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2.  Click **New repository secret**.
3.  Name: `MONGO_URI`
4.  Value: Your MongoDB Connection String.

### Step 3: Verify the Workflow
The file `.github/workflows/daily_compute.yml` is already set up to runs every day at **21:00 UTC** (4:00 PM EST).
It performs the following:
1.  Checks out your code.
2.  Installs dependencies.
3.  Runs `src/jobs/daily_run.py`.
4.  Saves results to MongoDB.

### Step 4: Keep the Render API Awake (Optional)
If you deploy the backend API to **Render (Free Tier)**, it sleeps after inactivity.
To keep it awake or wake it up for requests:
1.  Use a service like [cron-job.org](https://cron-job.org).
2.  Create a job to ping `https://<your-app>.onrender.com/system/status` every 10 minutes.
3.  **Note**: The Python Internal Scheduler (`src/core/scheduler.py`) runs *inside* the API. If the API sleeps, the scheduler sleeps. This is why **GitHub Actions (Step 3)** is the preferred method for heavy daily tasks.

## 🛠 Manual Trigger (Testing)
You can manually trigger the daily run from GitHub:
1.  Go to **Actions** tab.
2.  Select **Daily Heavy Compute**.
3.  Click **Run workflow**.

## 📁 Environment Variables Reference
| Variable | Description | Location |
| :--- | :--- | :--- |
| `DATABASE_URL` | Connection string (Mongo or SQLite) | `.env` / Render / GitHub Secrets |
| `STORAGE_TYPE` | `mongo` or `sqlite` | `.env` / Render / GitHub Vars |
| `BACKEND_URL` | URL of your deployed API (for self-pings) | `.env` / Render |
