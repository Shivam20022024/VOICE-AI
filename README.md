<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Voice AI

## Run Locally

Prerequisites: Node.js and Python 3.11+

1. Install frontend dependencies:
   `npm install`
2. Create and use the backend virtual environment:
   `cd backend`
   `python -m venv venv`
   `.\venv\Scripts\activate`
   `pip install -r ..\requirements.txt`
3. Set `GEMINI_API_KEY` and MongoDB settings in [backend/.env.local](backend/.env.local) or the project [.env.local](.env.local).
4. Start the backend with the virtualenv interpreter:
   `.\venv\Scripts\python.exe server.py`
5. In a second terminal, start the frontend:
   `npm run dev`

If the backend is started with system Python instead of `backend\venv\Scripts\python.exe`, optional Gemini features may be unavailable unless those packages are also installed globally.





# Voice AI Project

## Features
- AI Voice Interaction
- Backend API (Python)
- Frontend (React + Vite)

## Tech Stack
- Python
- FastAPI / Flask
- React
- Vite

## Setup
# Backend
cd backend
pip install -r requirements.txt
python server.py

# Frontend
cd frontend
npm install
npm run dev