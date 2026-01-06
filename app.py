import streamlit as st
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from io import BytesIO

# =========================================================
# CONFIGURAÇÃO
# =========================================================
st.set_page_config(
    page_title="IRAH–Premier",
    layout="centered"
)

tab_calc, tab_about = st.tabs(
    ["🧮 Avaliação Assistencial", "📘 Sobre o IRAH–Premier"]
)

# =========================================================
# DADOS DAS ESCALAS
# =========================================================
FUGULIN_DOMAINS = [
    "Estado mental", "Oxigenação", "Sinais vitais",
    "Motilidade", "Deambulação", "Alimentação",
    "Cuidado corporal", "Eliminação", "Terapêutica"
]

CHARLSON_ITEMS = {
    "IAM": 1, "ICC": 1, "Doença vascular periférica": 1,
    "AVC/AIT": 1, "Demência": 1, "DPOC": 1,
    "Doença tecido conjuntivo": 1, "Úlcera péptica": 1,
    "Doença hepática leve": 1, "Diabetes": 1,
    "Diabetes com lesão órgão-alvo": 2, "Hemiplegia": 2,
    "DRC moderada/grave": 2, "Neoplasia sólida": 2,
    "Leucemia": 2, "Linfoma": 2,
    "Doença hepática grave": 3,
    "Neoplasia metastática": 6,
    "AIDS": 6
}

def charlson_age_points(age):
    if age >= 80: return 4
    if age >= 70: return 3
    if age >= 60: return 2
    if age >= 50: return 1
    return 0

# =========================================================
# NORMALIZAÇÕES
# =========================================================
def norm_charlson(c): return min(c, 13) / 13 * 100
def norm_fugulin(f):
    if f <= 14: return 0
    if f <= 20: return 25
    if f <= 26: return 50
    if f <= 31: return 75
    return 100

def norm_mrc(m): return (60 - m) / 60 * 100
def norm_asg(a): return {"A": 0, "B": 50, "C": 100}[a]
def norm_fois(f): return {1:100,2:90,3:80,4:60,5:40,6:20,7:0}[f]
def norm_poly(p):
    if p <= 4: return 0
    if p <= 6: return 25
    if p <= 9: return 50
    if p <= 12: return 75
    return 100

WEIGHTS = {
    "charlson": 0.20,
    "fugulin": 0.20,
    "mrc": 0.15,
    "asg": 0.15,
    "fois": 0.15,
    "poly": 0.15
}

def classify(score):
    if score >= 67: return "Alto"
    if score >= 34: return "Moderado"
    return "Baixo"

# =========================================================
# SESSION STATE
# =========================================================
if "patients" not in st.session_state:
    st.session_state.patients = []

# =========================================================
# ABA PRINCIPAL
# =========================================================
with tab_calc:
    st.title("🩺 IRAH–Premier – Avaliação Assistencial")

    iniciais = st.text_input("Iniciais do paciente")
    leito = st.number_input("Leito", 1, 20)

    st.markdown("### 🩺 Escala de Fugulin")
    fug_scores = {}
    cols = st.columns(3)
    for i, d in enumerate(FUGULIN_DOMAINS):
        with cols[i % 3]:
            fug_scores[d] = st.selectbox(d, [1,2,3,4], key=f"f_{d}")

    fugulin_total = sum(fug_scores.values())
    st.info(f"Fugulin total: {fugulin_total}")

    st.markdown("### 🧬 Índice de Charlson")
    age = st.number_input("Idade", 0, 120)
    use_age = st.checkbox("Aplicar ajuste por idade")

    charlson_checks = {}
    cols2 = st.columns(2)
    for i, (k,v) in enumerate(CHARLSON_ITEMS.items()):
        with cols2[i % 2]:
            charlson_checks[k] = st.checkbox(f"{k} (+{v})")

    charlson_base = sum(v for k,v in CHARLSON_ITEMS.items() if charlson_checks.get(k))
    charlson_total = charlson_base + (charlson_age_points(age) if use_age else 0)

    st.info(f"Charlson total: {charlson_total}")

    st.markdown("### ⚙️ Demais escalas")
    mrc = st.number_input("MRC (0–60)", 0, 60)
    asg = st.selectbox("ASG", ["A","B","C"])
    fois = st.selectbox("FOIS", [1,2,3,4,5,6,7])
    poly = st.number_input("Nº medicamentos contínuos", 0, 50)

    irah = (
        norm_charlson(charlson_total)*WEIGHTS["charlson"] +
        norm_fugulin(fugulin_total)*WEIGHTS["fugulin"] +
        norm_mrc(mrc)*WEIGHTS["mrc"] +
        norm_asg(asg)*WEIGHTS["asg"] +
        norm_fois(fois)*WEIGHTS["fois"] +
        norm_poly(poly)*WEIGHTS["poly"]
    )

    trigger = fois <= 3 or poly >= 13 or mrc <= 35
    irah = round(irah,1)
    risco = "Alto" if trigger else classify(irah)

    st.subheader("Resultado")
    st.metric("IRAH–Premier", irah)
    st.success(f"Classificação: {risco}")

    if st.button("➕ Adicionar paciente"):
        st.session_state.patients.append({
            "Leito": leito,
            "Iniciais": iniciais,
            "IRAH": irah,
            "Risco": risco
        })

    if st.session_state.patients:
        df = pd.DataFrame(st.session_state.patients)
        st.dataframe(df)

        st.download_button(
            "⬇️ Exportar CSV",
            df.to_csv(index=False).encode(),
            "irah_premier.csv",
            "text/csv"
        )

        if st.button("📄 Gerar PDF"):
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = [Paragraph("IRAH–Premier – Relatório Assistencial", styles["Title"])]

            table_data = [df.columns.tolist()] + df.values.tolist()
            table = Table(table_data)
            table.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
                ("GRID",(0,0),(-1,-1),1,colors.black)
            ]))
            elements.append(table)
            doc.build(elements)
            st.download_button("⬇️ Baixar PDF", buffer.getvalue(), "irah_premier.pdf")

# =========================================================
# ABA SOBRE
# =========================================================
with tab_about:
    try:
        with open("README.md","r",encoding="utf-8") as f:
            st.markdown(f.read())
    except:
        st.info("Documento institucional não encontrado.")

