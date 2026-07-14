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

RUTA_LOGO_ESIC = os.path.join(ASSETS_DIR, "logo_esic.png")
RUTA_LOGO_SIVAA = os.path.join(ASSETS_DIR, "logo_sivaa.png")

# =====================================================
# CONFIGURACION DE LA PAGINA
# =====================================================
st.set_page_config(
    page_title="SIVAA",
    page_icon="🎓",
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

    logo_base64 = ""
    if os.path.exists(RUTA_LOGO_SIVAA):
        with open(RUTA_LOGO_SIVAA, "rb") as f:
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
            st.session_state.pagina = "inicio"
            st.rerun()

    st.stop()

# =====================================================
# NAVEGACION
# =====================================================
if "pagina" not in st.session_state:
    st.session_state.pagina = "inicio"


def ir_a(pagina):
    st.session_state.pagina = pagina


# =====================================================
# MENU LATERAL
# =====================================================
with st.sidebar:
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        if os.path.exists(RUTA_LOGO_ESIC):
            st.image(RUTA_LOGO_ESIC, use_container_width=True)
    with col_l2:
        if os.path.exists(RUTA_LOGO_SIVAA):
            st.image(RUTA_LOGO_SIVAA, use_container_width=True)

    st.markdown("### Menú")

    pag_actual = st.session_state.pagina

    if st.button(
        "🏠  Inicio",
        use_container_width=True,
        type="primary" if pag_actual == "inicio" else "secondary",
    ):
        ir_a("inicio")
        st.rerun()

    if st.button(
        "📧  Asistente de correo",
        use_container_width=True,
        type="primary" if pag_actual == "correo" else "secondary",
    ):
        ir_a("correo")
        st.rerun()

    if st.button(
        "📋  Auditor de actas",
        use_container_width=True,
        type="primary" if pag_actual == "auditor" else "secondary",
    ):
        ir_a("auditor")
        st.rerun()

    if st.button(
        "📜  Generador de certificados",
        use_container_width=True,
        type="primary" if pag_actual == "certificados" else "secondary",
    ):
        ir_a("certificados")
        st.rerun()

    if st.button(
        "⚖️  Asistente de normativa académica",
        use_container_width=True,
        type="primary" if pag_actual == "normativa" else "secondary",
    ):
        ir_a("normativa")
        st.rerun()

    st.markdown("---")
    st.caption("Desarrollado con IA Generativa · CEOIAG7")


# =====================================================
# PAGINA: INICIO
# =====================================================
def pagina_inicio():
    col_logo1, col_titulo, col_logo2 = st.columns([1, 4, 1])

    with col_logo1:
        if os.path.exists(RUTA_LOGO_ESIC):
            st.image(RUTA_LOGO_ESIC, width=110)

    with col_titulo:
        st.markdown(
            """
            <div class="header" style="text-align: center;">
                <h1>SIVAA</h1>
                <h3>Asistente inteligente para la gestión académica</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_logo2:
        if os.path.exists(RUTA_LOGO_SIVAA):
            st.image(RUTA_LOGO_SIVAA, width=110)

    st.divider()

    st.markdown(
        """
        SIVAA es un asistente construido con Inteligencia Artificial Generativa
        pensado para apoyar las tareas administrativas y académicas del día a día
        de una universidad: revisar actas, redactar comunicaciones, generar
        documentos oficiales y resolver dudas de normativa, todo desde un mismo
        panel de control.

        Actualmente el módulo **Auditor de actas** está operativo. El resto de
        módulos forman parte de la hoja de ruta del proyecto.
        """
    )

    st.divider()

    tarjetas = [
        (
            "📧 Asistente de correo",
            "Redacción y respuesta automática de comunicaciones con alumnos, "
            "profesores y administración.",
        ),
        (
            "📋 Auditor de actas",
            "Compara actas de calificaciones contra el excel maestro y genera "
            "un informe de incidencias en segundos. Disponible.",
        ),
        (
            "📜 Generador de certificados",
            "Creación automática de certificados académicos a partir de "
            "plantillas oficiales.",
        ),
        (
            "⚖️ Asistente de normativa académica",
            "Consultas en lenguaje natural sobre normativa, reglamentos y "
            "procedimientos de la universidad.",
        ),
    ]

    col_a, col_b = st.columns(2)
    columnas = [col_a, col_b, col_a, col_b]

    for (titulo, descripcion), columna in zip(tarjetas, columnas):
        with columna:
            st.markdown(
                f"""
                <div style="border:1px solid #DDE3F0; border-radius:10px;
                            padding:16px; margin-bottom:16px; background:#F7F9FF;">
                    <h4 style="margin-top:0;">{titulo}</h4>
                    <p style="color:#555; margin-bottom:0;">{descripcion}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # =====================================================
# PAGINA: AUDITOR DE ACTAS (la que ya funcionaba)
# =====================================================
def pagina_auditor():
    col_logo1, col_titulo, col_logo2 = st.columns([1, 4, 1])

    with col_logo1:
        if os.path.exists(RUTA_LOGO_ESIC):
            st.image(RUTA_LOGO_ESIC, width=110)

    with col_titulo:
        st.markdown(
            """
            <div class="header">
                <h1>SIVAA</h1>
                <h3>Sistema Inteligente de Validación de Actas Académicas</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_logo2:
        if os.path.exists(RUTA_LOGO_SIVAA):
            st.image(RUTA_LOGO_SIVAA, width=110)

    st.divider()

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

                st.divider()
                st.subheader("Resumen del acta")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Asignatura", asignatura)
                with col2:
                    st.metric("Curso", curso)
                with col3:
                    st.metric("Numero de alumnos", total_alumnos)

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


# =====================================================
# PAGINAS "PROXIMAMENTE"
# =====================================================
def pagina_proximamente(titulo, descripcion):
    st.markdown(f"## {titulo}")
    st.info("🔜 Próximamente — este módulo forma parte de la hoja de ruta del proyecto.")
    st.write(descripcion)


# =====================================================
# ENRUTADO
# =====================================================
pagina = st.session_state.pagina

if pagina == "inicio":
    pagina_inicio()
elif pagina == "auditor":
    pagina_auditor()
elif pagina == "correo":
    pagina_proximamente(
        "📧 Asistente de correo",
        "Redactará y clasificará correos con alumnos y profesorado, "
        "aprovechando modelos de lenguaje para agilizar la comunicación diaria.",
    )
elif pagina == "certificados":
    pagina_proximamente(
        "📜 Generador de certificados",
        "Generará certificados académicos oficiales a partir de plantillas, "
        "rellenando automáticamente los datos del alumno.",
    )
elif pagina == "normativa":
    pagina_proximamente(
        "⚖️ Asistente de normativa académica",
        "Permitirá consultar la normativa y los reglamentos de la universidad "
        "en lenguaje natural, con respuestas basadas en los documentos oficiales.",
    )