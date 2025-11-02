#!/bin/bash
# Linux/Mac script to run Streamlit app
cd packages/agent
source ../../venv/bin/activate
streamlit run src/streamlit_app.py --server.port 8501

