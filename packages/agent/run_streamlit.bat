@echo off
REM Windows batch script to run Streamlit app
cd packages/agent
..\..\venv\Scripts\python.exe -m streamlit run src/streamlit_app.py --server.port 8501

