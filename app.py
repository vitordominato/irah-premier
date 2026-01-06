import streamlit as st
import pandas as pd
from io import BytesIO

from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(page_title="IRAH–Premier", layout="centered")
tab_calc, tab_about = st.tabs(["🧮 Avaliação Assistencial", "📘 Sobre o IRAH–Premier"])

# ============================================================
# FUGULIN – ESCALA COMPLETA (12 ITENS)
# ============================================================
FUGULIN_SCALE = {
    "Estado mental": {
        1: "Lúcido, orientado",
        2: "Desorientado ocasionalmente",
        3: "Desorientado frequentemente",
        4: "Inconsciente / sedado",
    },
    "Oxigenação": {
        1: "Respiração espontânea em ar ambiente",
        2: "Oxigênio por cateter nasal",
        3: "Oxigênio por máscara",
        4: "VNI ou ventilação invasiva",
    },
    "Sinais vitais": {
        1: "Controle de rotina (≥8/8h)",
        2: "Controle a cada 6 horas",
        3: "Controle a cada 4 horas",
        4: "Monitorização contínua",
    },
    "Motilidade": {
        1: "Move-se espontaneamente",
        2: "Dificuldade para movimentos",
        3: "Movimentos limitados",
        4: "Imóvel",
    },
    "Deambulação": {
        1: "Deambula sozinho",
        2: "Deambula com auxílio",
        3: "Não deambula, senta com ajuda",
        4: "Restrito ao leito",
    },
    "Alimentação": {
        1: "Alimenta-se sozinho",
        2: "Auxílio parcial",
        3: "Auxílio total",
        4: "Nutrição enteral/parenteral",
    },
    "Cuidado corporal": {
        1: "Autossuficiente",
        2: "Auxílio parcial",
        3: "Auxílio total",
        4: "Dependência completa",
    },
    "Eliminação": {
        1: "Controle esfincteriano",
        2: "Uso eventual de fralda",
        3: "Uso contínuo de fralda",
        4: "SVD / ostomias",
    },
    "Terapêutica": {
        1: "Medicação oral simples",
        2: "Medicação EV intermitente",
        3: "Múltiplas medicações EV",
        4: "Cuidados complexos",
    },
    "Integridade cutâneo-mucosa": {
        1: "Íntegra",
        2: "Alteração leve",
        3: "Lesão superficial",
        4: "Lesão extensa / ferida complexa",
    },
    "Curativo": {
        1: "Sem curativo",
        2: "Curativo simples",
        3: "Curativo moderado",
        4: "Curativo complexo",
    },
    "Tempo de curativo": {
        1: "<5 minutos",
        2: "5–15 minutos",
        3: "16–30 minutos",
        4: ">30 minutos",
    },
}

# ============================================================
# FUNÇÕES
# ============================================================
def fugulin_classification(score):
    if score > 34:
        return "Intensivo"
    if 28 <= score <= 34:
        return "Semi-intensivo"
    if 23 <= score <= 27:
        return "Alta dependência"
    if 18 <= score <= 22:
        return "Intermediário"
    if 12 <= score <= 17:
        return "Mínimo"
    return "Fora da faixa"

def normalize_fugulin(score):
    if score > 34:
        return 100
    if 28 <= score <= 34:
        return 75
    if 23 <= score <= 27:
        return 50
    if 18 <= score <= 22:
        return 25
    return 0

def classify_irah(score):
    if score >= 67:
        return "Alto"
    if score >= 34:
        return "Moderado"
    return "Baixo"

# ============================================================
# SESSION STATE
# ============================================================
if "patients" not in st.session_state:
    st.session_state.patients = []

# ============================================================
# ABA PRINCIPAL
# ============================================================
with tab_calc:
    st.title("🩺 IRAH–Premier")

    iniciais = st.text_input("Iniciais do paciente").upper()
    leito = st.number_input("Leito", min_value=1, max_value=20, step=1)

    st.subheader("Escala de Fugulin")

    fugulin_scores = {}
    cols = st.columns(3)

    for i, (item, options) in enumerate(FUGULIN_SCALE.items()):
        with cols[i % 3]:
            label_map = {f"{k} – {v}": k for k, v in options.items()}
            choice = st.selectbox(item, list(label_map.keys()), key=item)
            fugulin_scores[item] = label_map[choice]

    fugulin_total = sum(fugulin_scores.values())
    fugulin_cat = fugulin_classification(fugulin_total)
    fugulin_norm = normalize_fugulin(fugulin_total)

    st.info(f"Fugulin total: {fugulin_total} | Classificação: {fugulin_cat}")

    irah = fugulin_norm
    risco = classify_irah(irah)

    st.metric("IRAH–Premier", irah)
    st.write(f"Risco: **{risco}**")

    if st.button("Adicionar / Atualizar paciente"):
        st.session_state.patients = [
            p for p in st.session_state.patients if p["Leito"] != leito
        ]
        st.session_state.patients.append({
            "Leito": leito,
            "Iniciais": iniciais,
            "Fugulin_total": fugulin_total,
            "Fugulin_classificacao": fugulin_cat,
            "IRAH_Premier": irah,
            "Risco": risco
        })

    if st.session_state.patients:
        st.subheader("Clínica – 20 leitos")

        df = pd.DataFrame(st.session_state.patients)
        df = df.sort_values("Leito")

        st.dataframe(df, use_container_width=True)

        baixo = int((df["Risco"] == "Baixo").sum())
        moderado = int((df["Risco"] == "Moderado").sum())
        alto = int((df["Risco"] == "Alto").sum())

        media = round(df["IRAH_Premier"].mean(), 1)

        st.markdown(
            f"**Distribuição:** 🟢 {baixo} | 🟡 {moderado} | 🔴 {alto}<br>"
            f"**Média IRAH da clínica:** {media}",
            unsafe_allow_html=True
        )

# ============================================================
# ABA SOBRE
# ============================================================
with tab_about:
    st.markdown("## IRAH–Premier")
    st.markdown(
        """
        Índice de Risco Assistencial Hospitalar para instituições de transição de cuidados.
        


        Desenvolvido por **Vitor Dominato Rocha** e **Wlademinck Reis**.
        """
    )
