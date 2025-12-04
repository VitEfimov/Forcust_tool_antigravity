# Deployment Guide

This guide explains how to deploy the Antigravity application to the web for free.

## Architecture Overview

Because this is a full-stack application with a Python backend (ML models) and a React frontend, we need to deploy them separately:

1.  **Database (MongoDB Atlas)**: Stores your daily forecasts and history.
    *   *Why?* The local SQLite file (`forecasts.db`) will be deleted every time a cloud server restarts. You need a cloud database for persistence.
2.  **Backend (Render)**: Hosts the FastAPI Python API and runs the background scheduler.
    *   *Why?* Vercel is great for frontends but has strict limits for Python backends (execution time, file size). Render is better for long-running apps.
3.  **Frontend (Vercel)**: Hosts the React User Interface.

---

## Part 1: Database Setup (MongoDB Atlas)

1.  Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) and create a free account.
2.  Create a new **Cluster** (select the Free Shared tier).
3.  Create a **Database User**:
    *   Username: `admin`
    *   Password: (Generate a secure password and save it)
4.  **Network Access**:
    *   Click "Add IP Address" -> "Allow Access from Anywhere" (`0.0.0.0/0`). (Required for Render to connect).
5.  **Get Connection String**:
    *   Click "Connect" -> "Drivers" -> Copy the connection string.
    *   It looks like: `mongodb+srv://admin:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority`
    *   Replace `<password>` with your actual password.

---

## Part 2: Backend Deployment (Render)

1.  Push your code to **GitHub**.
2.  Go to [Render](https://render.com/) and create a free account.
3.  Click **"New +"** -> **"Web Service"**.
4.  Connect your GitHub repository.
5.  **Configure Service**:
    *   **Name**: `antigravity-api`
    *   **Runtime**: Python 3
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
6.  **Environment Variables**:
    *   Add `DATABASE_URL`: Paste your MongoDB connection string from Part 1.
    *   Add `PYTHON_VERSION`: `3.10.0` (or similar).
7.  Click **"Create Web Service"**.
8.  Wait for deployment. Copy the **Service URL** (e.g., `https://antigravity-api.onrender.com`).

---

## Part 3: Frontend Deployment (Vercel)

1.  Go to [Vercel](https://vercel.com/) and create a free account.
2.  Click **"Add New..."** -> **"Project"**.
3.  Import your GitHub repository.
4.  **Configure Project**:
    *   **Framework Preset**: Vite
    *   **Root Directory**: `frontend` (Important! Click "Edit" and select the `frontend` folder).
5.  **Environment Variables**:
    *   Name: `VITE_API_URL`
    *   Value: Your Render Backend URL (e.g., `https://antigravity-api.onrender.com`).
    *   *Note*: You might need to update your frontend code to use this variable instead of hardcoded `localhost:8000`.
6.  Click **"Deploy"**.

---

## Part 4: Connecting the Pieces

### 1. Update Frontend API Calls
Currently, the frontend might be hardcoded to `http://localhost:8000`. You need to update `src/api/config.js` (or wherever axios is configured) to use the environment variable.

**Example `frontend/src/config.js`**:
```javascript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export default API_URL;
```

### 2. Update Backend Database Logic
Currently, the app uses **SQLite**. To use MongoDB, you need to update `src/core/database.py` to check for the `DATABASE_URL` environment variable and connect to Mongo if present.

**Do you need to do this?**
*   **YES**, if you want to save daily results and see history on the "Archive" page after deployment.
*   **NO**, if you only care about the "Market Overview" (which generates fresh forecasts on the fly) and don't mind losing historical records on restart.

### 3. "Market Overview" vs. "Saved History"
*   **Market Overview**: Calculates forecasts *right now* (or simulates them for a past date). It works fine without a persistent DB, as long as it can fetch data from Yahoo Finance.
*   **Archive / Saved History**: This requires a persistent DB to remember "What did the model predict 3 months ago?".

## Summary
1.  **Deploy DB**: MongoDB Atlas.
2.  **Deploy Backend**: Render.
3.  **Deploy Frontend**: Vercel.
4.  **Update Code**: Switch from SQLite to MongoDB in `database.py`.
