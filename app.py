import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px
import qrcode
from io import BytesIO

# Configuración de página
st.set_page_config(
    page_title="Semáforo Socioemocional",
    page_icon="🚦",
    layout="wide"
)

# ---------------------------------------------------------
# Conexión a Google Sheets
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df = conn.read(ttl=5) # ttl=5 segundos para refresco rápido
        if df is not None and not df.empty:
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
            return df
        return pd.DataFrame(columns=["fecha_hora", "asignatura", "estado", "motivo"])
    except Exception:
        return pd.DataFrame(columns=["fecha_hora", "asignatura", "estado", "motivo"])

def registrar_voto(asignatura, estado, motivo):
    df_actual = cargar_datos()
    nuevo_registro = pd.DataFrame([{
        "fecha_hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "asignatura": asignatura,
        "estado": estado,
        "motivo": motivo
    }])
    df_actualizado = pd.concat([df_actual, nuevo_registro], ignore_index=True)
    conn.update(data=df_actualizado)

# ---------------------------------------------------------
# Barra Lateral y Roles
# ---------------------------------------------------------
st.sidebar.title("🚦 Navegación")
rol = st.sidebar.radio("Ir a:", ["👨‍🎓 Estudiante (Votar)", "📊 Docente (Proyector & Dashboard)"])

# ---------------------------------------------------------
# VISTA: ESTUDIANTE
# ---------------------------------------------------------
if rol == "👨‍🎓 Estudiante (Votar)":
    st.title("🚦 Check-in Socioemocional")
    st.write("Tu respuesta es **100% anónima** y ayuda a calibrar el ritmo de la sesión.")

    asignatura = st.selectbox(
        "Asignatura / Sesión:",
        ["General", "Ingeniería de Datos", "ETL", "Arquitecturas Analíticas", "Estadística"]
    )

    st.markdown("### ¿Cómo te sientes para la clase de hoy?")
    
    col1, col2, col3 = st.columns(3)
    estado_elegido = None

    with col1:
        st.markdown("#### 🟢 Verde")
        st.caption("Tranquilo, motivado y listo.")
        if st.button("🟢 Elegir Verde", use_container_width=True, type="primary"):
            estado_elegido = "Verde"

    with col2:
        st.markdown("#### 🟡 Amarillo")
        st.caption("Cansado, disperso o con dudas.")
        if st.button("🟡 Elegir Amarillo", use_container_width=True):
            estado_elegido = "Amarillo"

    with col3:
        st.markdown("#### 🔴 Rojo")
        st.caption("Abrumado, estresado o bloqueado.")
        if st.button("🔴 Elegir Rojo", use_container_width=True):
            estado_elegido = "Rojo"

    motivo = st.text_input("Comentario breve u opcional (ej. 'Semana de parciales', 'Todo claro'):")

    if estado_elegido:
        with st.spinner("Guardando tu respuesta..."):
            registrar_voto(asignatura, estado_elegido, motivo)
        st.success(f"¡Listo! Registraste tu estado: {estado_elegido}")
        if estado_elegido == "Verde":
            st.balloons()

# ---------------------------------------------------------
# VISTA: DOCENTE (DASHBOARD)
# ---------------------------------------------------------
else:
    st.title("📊 Panel Docente & Proyector de Aula")
    
    # Protección básica con contraseña (configurada en Secrets o por defecto 'admin123')
    admin_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
    ingreso = st.sidebar.text_input("Contraseña de Docente:", type="password")

    if ingreso != admin_password:
        st.warning("🔒 Ingresa la contraseña de docente en la barra lateral para ver los resultados.")
    else:
        tab_qr, tab_dashboard = st.tabs(["📲 Proyectar QR de Votación", "📈 Métricas en Vivo"])

        # Pestaña 1: Código QR para proyectar en el salón
        with tab_qr:
            st.subheader("Escanea para registrar tu estado:")
            app_url = st.secrets.get("APP_URL", "https://share.streamlit.io")
            
            # Generar QR
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(app_url)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="#1E1E1E", back_color="white")
            
            buf = BytesIO()
            img_qr.save(buf, format="PNG")
            
            col_qr_img, col_qr_txt = st.columns([1, 2])
            with col_qr_img:
                st.image(buf.getvalue(), width=260)
            with col_qr_txt:
                st.markdown(f"**URL:** [{app_url}]({app_url})")
                st.info("💡 Proyecta esta pestaña los primeros 3 minutos de clase para que los estudiantes voten desde sus móviles.")

        # Pestaña 2: Resultados y Dashboard
        with tab_dashboard:
            df = cargar_datos()

            if df.empty or "estado" not in df.columns or df["estado"].dropna().empty:
                st.info("Aún no hay respuestas registradas.")
            else:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    materias = ["Todas"] + sorted([str(x) for x in df["asignatura"].dropna().unique()])
                    sel_mat = st.selectbox("Asignatura:", materias)
                with col_f2:
                    solo_hoy = st.checkbox("Solo registros de hoy", value=True)

                # Filtrado
                df_f = df.copy()
                if sel_mat != "Todas":
                    df_f = df_f[df_f["asignatura"] == sel_mat]
                if solo_hoy and "fecha_hora" in df_f.columns:
                    hoy = datetime.date.today()
                    df_f = df_f[df_f["fecha_hora"].dt.date == hoy]

                if df_f.empty:
                    st.warning("No hay registros que coincidan con los filtros.")
                else:
                    total = len(df_f)
                    conteos = df_f["estado"].value_counts().to_dict()
                    v = conteos.get("Verde", 0)
                    a = conteos.get("Amarillo", 0)
                    r = conteos.get("Rojo", 0)

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total Check-ins", total)
                    m2.metric("🟢 Verde", f"{v} ({v/total*100:.1f}%)")
                    m3.metric("🟡 Amarillo", f"{a} ({a/total*100:.1f}%)")
                    m4.metric("🔴 Rojo", f"{r} ({r/total*100:.1f}%)")

                    if total >= 3 and (r / total) >= 0.25:
                        st.error("🚨 **Alerta Pedagógica:** Más del 25% del curso está en Rojo. Conviene revisar carga, hacer una pausa activa o abrir dudas.")

                    st.markdown("---")
                    
                    cg1, cg2 = st.columns([1, 1])
                    with cg1:
                        fig = px.pie(
                            df_f,
                            names="estado",
                            title="Estado Emocional del Aula",
                            color="estado",
                            color_discrete_map={"Verde": "#27ae60", "Amarillo": "#f39c12", "Rojo": "#c0392b"},
                            hole=0.45
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    with cg2:
                        st.subheader("💬 Motivos anónimos recientes")
                        mensajes = df_f[df_f["motivo"].fillna("").str.strip() != ""]
                        if mensajes.empty:
                            st.caption("Sin comentarios adicionales.")
                        else:
                            for _, row in mensajes.tail(6).iloc[::-1].iterrows():
                                ic = "🟢" if row["estado"] == "Verde" else ("🟡" if row["estado"] == "Amarillo" else "🔴")
                                st.markdown(f"**{ic}:** {row['motivo']}")

            if st.button("🔄 Actualizar Resultados"):
                st.rerun()
