# Deployment Guide for Render.com

This project is prepared for deployment on [Render](https://render.com).

## Steps to Deploy

1. **Push to GitHub**: Upload your entire project directory to a new GitHub repository.
2. **Create a "Web Service" on Render**:
   - Link your GitHub repository.
   - **Name**: `ai-english-speaking-partner` (or any name).
   - **Environment**: `Python 3`.
   - **Root Directory**: `.` (leave as root).
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app --bind 0.0.0.0:$PORT`
3. **Environment Variables**:
   - Go to the **Environment** tab in Render.
   - Add a new variable: `GOOGLE_API_KEY` or `GEMINI_API_KEY`.
   - Paste your Gemini API key there.
4. **Deploy**: Click "Create Web Service".

## Why This Works
- Your frontend is automatically served by the FastAPI backend.
- The `/chat` endpoint is now relative, so the frontend knows to talk to the same server it was loaded from.
- `gunicorn` provides a robust production server.
