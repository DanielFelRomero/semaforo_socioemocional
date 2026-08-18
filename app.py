import streamlit as st
import pandas as pd
import requests
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
# Funciones de Datos
# ---------------------------------------------------------
def cargar_datos():
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id = sheet_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
        
        df = pd.read_csv(csv_url)
        if not df.empty and "fecha_hora" in df.columns:
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
            return df
        return pd.DataFrame(columns=["fecha_hora", "asignatura", "estado", "motivo"])
    except Exception as e:
        return pd.DataFrame(columns=["fecha_hora", "asignatura", "estado", "motivo"])

def registrar_voto(asignatura, estado, motivo):
    try:
        webhook_url = st.secrets["WEBHOOK_URL"]
        payload = {
            "fecha_hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "asignatura": asignatura,
            "estado": estado,
            "motivo": motivo
        }
        response = requests.post(webhook_url, json=payload, timeout=8, allow_redirects=True)
        return response.status_code == 200
    except Exception:
        return False

# ---------------------------------------------------------
# Navegación y Roles
# ---------------------------------------------------------
st.sidebar.title("🚦 Navegación")
rol = st.sidebar.radio("Ir a:", ["👨‍🎓 Estudiante (Votar)", "📊 Docente (Proyector & Dashboard)"])

# ---------------------------------------------------------
# VISTA: ESTUDIANTE (Con formulario y botón de enviar)
# ---------------------------------------------------------
if rol == "👨‍🎓 Estudiante (Votar)":
    st.title("🚦 Check-in Socioemocional")
    st.write("Tu registro es **100% anónimo**. Ayúdanos a calibrar el ritmo de la sesión.")

    # Formulario que agrupa todas las entradas antes de enviar
    with st.form("form_checkin", clear_on_submit=True):
        asignatura = st.selectbox(
            "Asignatura / Sesión:",
            ["ETL", "Arquitecturas Analíticas", "Otro"]
        )

        st.markdown("### Selecciona tu estado:")
        
        # Selector de opciones con descripción
        opciones = [
            "🟢 Verde — Enfocado, tranquilo y listo para aprender",
            "🟡 Amarillo — Cansado, con dudas o algo disperso",
            "🔴 Rojo — Abrumado, frustrado o bloqueado"
        ]
        seleccion = st.radio(
            "¿Cómo te sientes hoy?",
            opciones,
            index=0
        )

        motivo = st.text_input(
            "Comentario breve u opcional (ej. 'Semana pesada de parciales', 'Todo claro'):",
            max_chars=150
        )

        # Botón explícito de votación
        enviado = st.form_submit_button("🚀 Enviar Check-in", use_container_width=True, type="primary")

    if enviado:
        # Extraer únicamente el color ("Verde", "Amarillo" o "Rojo")
        estado_elegido = "Verde" if "Verde" in seleccion else ("Amarillo" if "Amarillo" in seleccion else "Rojo")
        
        with st.spinner("Registrando respuesta..."):
            exito = registrar_voto(asignatura, estado_elegido, motivo)
        
        if exito:
            st.success(f"¡Gracias! Tu estado ({estado_elegido}) fue registrado con éxito.")
            if estado_elegido == "Verde":
                st.balloons()
        else:
            st.error("Hubo un problema al registrar tu respuesta. Intenta de nuevo.")

# ---------------------------------------------------------
# VISTA: DOCENTE (Con autorefresco en vivo cada 2 segundos)
# ---------------------------------------------------------
else:
    st.title("📊 Panel Docente & Proyector de Aula")
    
    admin_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
    ingreso = st.sidebar.text_input("Contraseña de Docente:", type="password")

    if ingreso != admin_password:
        st.warning("🔒 Ingresa la contraseña de docente en la barra lateral para ver los resultados.")
    else:
        tab_qr, tab_dashboard = st.tabs(["📲 Proyectar QR de Votación", "📈 Métricas en Vivo (Streaming)"])

        # Pestaña 1: Proyector QR
        with tab_qr:
            st.subheader("Escanea para registrar tu estado:")
            host = st.context.headers.get("Host", "share.streamlit.io")
            app_url = f"https://{host}" if not host.startswith("http") else host
            
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
                st.info("💡 Proyecta esta pestaña los primeros 3 minutos de clase.")

        # Pestaña 2: Fragmento con actualización automática continua
        with tab_dashboard:
            # Decorador que hace que SOLO esta sección se ejecute cada 2 segundos
            @st.fragment(run_every=1)
            def render_dashboard_en_vivo():
                df = cargar_datos()

                if df.empty or "estado" not in df.columns or df["estado"].dropna().empty:
                    st.info("Esperando los primeros votos...")
                    return

                # Barra superior con estado en vivo y selector
                c_head1, c_head2 = st.columns([3, 1])
                with c_head1:
                    st.caption(f"🟢 **En vivo** — Última sincronización: {datetime.datetime.now().strftime('%H:%M:%S')}")
                with c_head2:
                    solo_hoy = st.checkbox("Solo hoy", value=True)

                materias = ["Todas"] + sorted([str(x) for x in df["asignatura"].dropna().unique()])
                sel_mat = st.selectbox("Filtrar por Asignatura:", materias)

                # Filtros
                df_f = df.copy()
                if sel_mat != "Todas":
                    df_f = df_f[df_f["asignatura"] == sel_mat]
                if solo_hoy and "fecha_hora" in df_f.columns:
                    hoy = datetime.date.today()
                    df_f = df_f[df_f["fecha_hora"].dt.date == hoy]

                if df_f.empty:
                    st.warning("No hay registros con los filtros seleccionados.")
                    return

                total = len(df_f)
                conteos = df_f["estado"].value_counts().to_dict()
                v = conteos.get("Verde", 0)
                a = conteos.get("Amarillo", 0)
                r = conteos.get("Rojo", 0)

                # Métricas estilo tarjetas
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Check-ins", total)
                m2.metric("🟢 Verde", f"{v} ({v/total*100:.0f}%)")
                m3.metric("🟡 Amarillo", f"{a} ({a/total*100:.0f}%)")
                m4.metric("🔴 Rojo", f"{r} ({r/total*100:.0f}%)")

                if total >= 3 and (r / total) >= 0.25:
                    st.error("🚨 **Alerta:** Más del 25% del grupo está en Rojo.")

                st.markdown("---")
                
                # Gráfico y comentarios
                cg1, cg2 = st.columns([1, 1])
                with cg1:
                    fig = px.pie(
                        df_f,
                        names="estado",
                        title="Distribución del Semáforo",
                        color="estado",
                        color_discrete_map={"Verde": "#27ae60", "Amarillo": "#f39c12", "Rojo": "#c0392b"},
                        hole=0.45
                    )
                    fig.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=300)
                    st.plotly_chart(fig, use_container_width=True)

                with cg2:
                    st.subheader("💬 Motivos recientes")
                    mensajes = df_f[df_f["motivo"].fillna("").astype(str).str.strip() != ""]
                    if mensajes.empty:
                        st.caption("Sin comentarios.")
                    else:
                        for _, row in mensajes.tail(5).iloc[::-1].iterrows():
                            ic = "🟢" if row["estado"] == "Verde" else ("🟡" if row["estado"] == "Amarillo" else "🔴")
                            st.markdown(f"**{ic}:** {row['motivo']}")

            # Ejecutar el fragmento en vivo
            render_dashboard_en_vivo()
