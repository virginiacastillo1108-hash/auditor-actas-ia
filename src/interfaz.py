import os
import sys
import base64

import streamlit as st

# Asegurar que los módulos del proyecto (app.py, acta.py, etc.) se
# encuentran aunque streamlit se lance desde otra carpeta.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from app import auditar_acta
from config import EXCEL_MAESTRO

ASSETS_DIR = os.path.join(ROOT_DIR, "assets")

RUTA_MAESTRO_DEFECTO = (
    EXCEL_MAESTRO
    if os.path.isabs(EXCEL_MAESTRO)
    else os.path.join(ROOT_DIR, EXCEL_MAESTRO)
)

# =====================================================
# CONFIGURACION DE LA PAGINA
# =====================================================
st.set_page_config(
    page_title="SIVAA",
    page_icon="=",
    layout="wide",
)

# Cargar estilos propios (style.css)
ruta_css = os.path.join(BASE_DIR, "style.css")
if os.path.exists(ruta_css):
    with open(ruta_css, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# =====================================================
# PANTALLA DE BIENVENIDA (SPLASH) - SOLO LOGO
# =====================================================
if "mostrado_intro" not in st.session_state:
    st.session_state.mostrado_intro = False

if not st.session_state.mostrado_intro:

    ruta_logo_sivaa = os.path.join(ASSETS_DIR, "logo_sivaa.png")
    logo_base64 = ""
    if os.path.exists(ruta_logo_sivaa):
        with open(ruta_logo_sivaa, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()

    st.markdown(
        """
        <style>
        [data-testid="stHeader"], [data-testid="stToolbar"] {
            display: none;
        }
        .block-container {
            padding-top: 1rem !important;
        }
        @keyframes fadeInLogo {
            0%   { opacity: 0; transform: scale(0.92); }
            100% { opacity: 1; transform: scale(1); }
        }
        .splash-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 78vh;
            text-align: center;
        }
        .splash-logo {
            width: 320px;
            animation: fadeInLogo 2.5s ease-in-out;
            margin-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="splash-wrapper">
            <img class="splash-logo" src="data:image/png;base64,{logo_base64}" />
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_boton, col_b = st.columns([2, 1, 2])
    with col_boton:
        if st.button("Entrar", use_container_width=True):
            st.session_state.mostrado_intro = True
            st.rerun()

    st.stop()

# =====================================================
# CABECERA CON LOGOS
# =====================================================
col_logo1, col_titulo, col_logo2 = st.columns([1, 4, 1])

with col_logo1:
    ruta_logo_esic = os.path.join(ASSETS_DIR, "logo_esic.png")
    if os.path.exists(ruta_logo_esic):
        st.image(ruta_logo_esic, width=110)

with col_titulo:
    st.markdown(
        """
        <div class="header">
            <h1>SIVAA</h1>
            <h3>Sistema Inteligente de Validacion de Actas Academicas</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_logo2:
    ruta_logo_sivaa = os.path.join(ASSETS_DIR, "logo_sivaa.png")
    if os.path.exists(ruta_logo_sivaa):
        st.image(ruta_logo_sivaa, width=110)

st.divider()

# =====================================================
# CARGA DEL ACTA
# =====================================================
st.header("Acta a auditar")
archivo_acta = st.file_uploader(
    "Selecciona el Excel del acta del profesor",
    type=["xlsx"],
)

with st.expander("Excel maestro (opcional - si no subes uno, se usa el del proyecto)"):
    archivo_maestro = st.file_uploader(
        "Excel maestro (.xlsx)",
        type=["xlsx"],
        key="maestro_uploader",
    )
    st.caption(f"Por defecto se usa: `{EXCEL_MAESTRO}`")

st.divider()

# =====================================================
# BOTON DE VALIDACION
# =====================================================
if st.button("VALIDAR ACTA", use_container_width=True):

    if archivo_acta is None:
        st.error("Debes seleccionar un acta antes de validar.")
    else:
        maestro_a_usar = (
            archivo_maestro if archivo_maestro is not None else RUTA_MAESTRO_DEFECTO
        )

        try:
            with st.spinner("Auditando acta, un momento..."):
                informe, asignatura, curso, total_alumnos = auditar_acta(
                    archivo_acta, maestro_a_usar
                )

            st.success(f"Auditoria completada: {asignatura}")

            # ---------------- Resumen ----------------
            st.divider()
            st.subheader("Resumen del acta")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Asignatura", asignatura)
            with col2:
                st.metric("Curso", curso)
            with col3:
                st.metric("Numero de alumnos", total_alumnos)

            # ---------------- Informe ----------------
            st.divider()
            st.subheader("Informe de auditoria")
            st.code(informe, language=None)

            st.download_button(
                "Descargar informe (.txt)",
                data=informe,
                file_name=f"informe_{asignatura}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        except (FileNotFoundError, ValueError) as error:
            st.error(f"Error: {error}")
        except Exception as error:
            st.error(f"Ha ocurrido un error inesperado: {error}")
