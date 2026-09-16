@echo off
echo Starting Meat Fish Streamlit Dashboard...
python -m streamlit run app_thit_ca.py --server.port 8502 --server.enableCORS false --server.enableXsrfProtection false
pause
