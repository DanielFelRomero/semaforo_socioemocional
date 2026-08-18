import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px
import qrcode
from io import BytesIO

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # ttl=2 segundos para que el dashboard del docente lea casi en tiempo real
        df = conn.read(ttl=2)
        if df is not None and not df.empty:
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
            return df
        return pd.DataFrame(columns=["fecha_hora", "asignatura", "estado", "motivo"])
    except Exception:
        return pd.DataFrame(columns=["fecha_hora", "asignatura", "estado", "motivo"])

def registrar_voto(asignatura, estado, motivo):
    webhook_url = st.secrets["WEBHOOK_URL"]
    payload = {
        "fecha_hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "asignatura": asignatura,
        "estado": estado,
        "motivo": motivo
    }
    # Envío directo por HTTP POST a Google Sheets
    response = requests.post(webhook_url, json=payload, timeout=8)
    return response.status_code == 200
