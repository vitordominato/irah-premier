import streamlit as st
import pandas as pd
import json
from io import BytesIO

# PDF (ReportLab)
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(page_title="IRAH–Premier", layout="centered")
tab_calc, tab_about = st.tabs(["🧮 Avaliação Assistencial", "📘 Sobre o IRAH–Premier"])

# ============================================================
# ESCALAS
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
        4: "Cuidados complexos (ex.: múltiplas infusões, protocolos intensivos)",
    },
    "Integridade cutâneo-mucosa": {
        1: "Íntegra",
        2: "Alteração leve / risco (ex.: hiperemia, pele frágil)",
        3: "Lesão superficial / UPP 1–2 / dermatite importante",
        4: "Lesão extensa / UPP 3–4 / ferida complexa",
    },
    "Curativo": {
        1: "Sem curativo",
        2: "Curativo simples (baixa complexidade)",
        3: "Curativo moderado (ex.: múltiplas lesões / técnica específica)",
        4: "Curativo complexo (ex.: grande área / terapia avançada)",
    },
    "Tempo de curativo": {
        1: "< 5 min / não se aplica",
        2: "5–15 min",
        3: "16–30 min",
        4: "> 30 min",
    },
}

CHARLSON_ITEMS = {
    "Infarto do miocárdio": 1,
    "Insuficiência cardíaca congestiva": 1,
    "Doença vascular periférica": 1,
    "Doença cerebrovascular (AVC/AIT)": 1,
    "Demência": 1,
    "DPOC / doença pulmonar crônica": 1,
    "Doença do tecido conjuntivo": 1,
    "Doença ulcerosa péptica": 1,
    "Doença hepática leve": 1,
    "Diabetes sem complicações": 1,
    "Diabetes com lesão de órgão-alvo": 2,
    "Hemiplegia/paraplegia": 2,
    "Doença renal moderada/grave": 2,
    "Neoplasia (sólida) sem metástase": 2,
    "Leucemia": 2,
    "Linfoma": 2,
    "Doença hepática moderada/grave": 3,
    "Neoplasia metastática": 6,
    "AIDS/HIV (com doença)": 6,
}

FOIS_LABEL_MAP = {
    "1 – Nutrição alternativa (não oral)": 1,
    "2 – Via alternativa predominante com ingestão oral mínima": 2,
    "3 – Ingestão oral consistente + via alternativa": 3,
    "4 – Ingestão oral de consistência única": 4,
    "5 – Ingestão oral com preparação especial": 5,
    "6 – Ingestão oral com restrição mínima": 6,
    "7 – Ingestão oral plena (sem restrições)": 7,
}

WEIGHTS = {
    "Charlson": 0.20,
    "Fugulin": 0.20,
    "MRC": 0.15,
    "ASG": 0.15,
    "FOIS": 0.15,
    "Polifarmacia": 0.15,
}

# ============================================================
# FUNÇÕES
# ============================================================
def charlson_age_points(age: int) -> int:
    if age is None:
        return 0
    if age >= 80:
        return 4
    if age >= 70:
        return 3
    if age >= 60:
        return 2
    if age >= 50:
        return 1
    return 0


def fugulin_classification(score: int) -> str:
    # Regra operacional (resolve sobreposição do 28)
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


def normalize_fugulin(score: int) -> float:
    if score > 34:
        return 100.0
    if 28 <= score <= 34:
        return 75.0
    if 23 <= score <= 27:
        return 50.0
    if 18 <= score <= 22:
        return 25.0
    return 0.0


def normalize_charlson(total: int) -> float:
    c = float(total or 0)
    c = max(0.0, min(c, 13.0))
    return (c / 13.0) * 100.0


def normalize_mrc(mrc_total: int) -> float:
    m = float(mrc_total or 0)
    m = max(0.0, min(m, 60.0))
    return ((60.0 - m) / 60.0) * 100.0


def normalize_asg(asg_label: str) -> float:
    return {"A": 0.0, "B": 50.0, "C": 100.0}.get(asg_label, 0.0)


def normalize_fois(fois: int) -> float:
    mapping = {1: 100, 2: 90, 3: 80, 4: 60, 5: 40, 6: 20, 7: 0}
    return float(mapping.get(int(fois), 0.0))


def normalize_poly(n_meds: int) -> float:
    n = int(n_meds or 0)
    if n <= 4:
        return 0.0
    if n <= 6:
        return 25.0
    if n <= 9:
        return 50.0
    if n <= 12:
        return 75.0
    return 100.0


# ============================================================
# RISCOS IDENTIFICADOS (DERIVADOS DAS ESCALAS)
# ============================================================
def _bump_level(level: str, n: int = 1) -> str:
    order = ["Baixo", "Moderado", "Alto"]
    if level not in order:
        level = "Baixo"
    i = order.index(level)
    return order[min(len(order) - 1, i + n)]

def risk_broncoaspiracao(fois: int) -> str:
    # FOIS baixo = maior risco de aspiração
    if int(fois) <= 3:
        return "Alto"
    if int(fois) <= 5:
        return "Moderado"
    return "Baixo"

def risk_queda(mrc: int, fugulin_deambulacao: int | None = None) -> str:
    # Regra simples e operacional: fraqueza funcional aumenta risco de queda
    if int(mrc) <= 35:
        lvl = "Alto"
    elif int(mrc) <= 47:
        lvl = "Moderado"
    else:
        lvl = "Baixo"

    # Ajuste opcional pelo item Deambulação do Fugulin (3-4 sugere maior risco)
    if fugulin_deambulacao is not None and int(fugulin_deambulacao) >= 3 and lvl != "Alto":
        lvl = _bump_level(lvl, 1)
    return lvl

def risk_lpp(fug_scores: dict) -> str:
    # Usa itens do Fugulin como proxy assistencial para risco de LPP
    integ = int(fug_scores.get("Integridade cutâneo-mucosa", 1) or 1)
    motil = int(fug_scores.get("Motilidade", 1) or 1)
    corpo = int(fug_scores.get("Cuidado corporal", 1) or 1)
    deamb = int(fug_scores.get("Deambulação", 1) or 1)

    if integ >= 3:
        lvl = "Alto"
    elif motil >= 3 or corpo >= 3:
        lvl = "Moderado"
    else:
        lvl = "Baixo"

    # Restrito ao leito agrava
    if deamb == 4 and lvl != "Alto":
        lvl = _bump_level(lvl, 1)
    return lvl

def risk_nutricional(asg: str, fois: int) -> str:
    # ASG é a referência da admissão e mantém consistência assistencial
    asg = (asg or "").strip().upper()
    if asg == "C":
        lvl = "Alto"
    elif asg == "B":
        lvl = "Moderado"
    else:
        lvl = "Baixo"

    # Deglutição/via oral piora risco nutricional
    if int(fois) <= 4 and lvl != "Alto":
        lvl = _bump_level(lvl, 1)
    return lvl

def risk_medicamentoso(poly: int) -> str:
    n = int(poly or 0)
    if n >= 13:
        return "Alto"
    if n >= 10:
        return "Moderado"
    if n >= 7:
        return "Moderado"
    return "Baixo"



def classify(score_0_100: float, trigger_high: bool) -> str:
    if trigger_high:
        return "Alto"
    if score_0_100 >= 67:
        return "Alto"
    if score_0_100 >= 34:
        return "Moderado"
    return "Baixo"


def safe_json_dumps(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return "{}"


def safe_json_loads(s: str):
    try:
        return json.loads(s) if s else {}
    except Exception:
        return {}


def build_pdf(df_any: pd.DataFrame, summary: dict) -> bytes:
    """Gera PDF em A4 paisagem com tabela-resumo enxuta:
    Leito | Iniciais | IRAH | Classificação | Riscos (palavras-chave/ícones).
    """
    buffer = BytesIO()

    # Página em paisagem para melhor leitura
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontName = "Helvetica"
    normal.fontSize = 8
    normal.leading = 9

    elements = []
    elements.append(Paragraph("IRAH–Premier — Relatório Assistencial (Resumo)", styles["Title"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Resumo da unidade (20 leitos)", styles["Heading2"]))

    summary_rows = [
        ["Ocupação", summary.get("ocupacao", "")],
        ["Média IRAH", summary.get("media", "")],
        ["Mediana IRAH", summary.get("mediana", "")],
        ["Carga total (soma)", summary.get("carga_total", "")],
        ["Distribuição", summary.get("distribuicao", "")],
        ["Complexidade global (pela média)", summary.get("complexidade_global", "")],
    ]
    t_sum = Table(summary_rows, colWidths=[170, 530])
    t_sum.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(t_sum)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("Tabela-resumo de pacientes", styles["Heading2"]))
    elements.append(Spacer(1, 6))

    # Seleciona colunas essenciais (tolerante a ausência)
    col_map = {
        "Leito": "Leito",
        "Iniciais": "Iniciais",
        "IRAH_Premier": "IRAH",
        "Risco": "Classificação",
        "Riscos_identificados": "Riscos",
    }

    # monta df enxuto
    df_pdf = pd.DataFrame()
    for src, dst in col_map.items():
        if src in df_any.columns:
            df_pdf[dst] = df_any[src]
        else:
            df_pdf[dst] = ""

    # Formata IRAH
    if "IRAH" in df_pdf.columns:
        df_pdf["IRAH"] = pd.to_numeric(df_pdf["IRAH"], errors="coerce").round(1).fillna("")

    # Gera uma versão curta e com ícones para os riscos
    def _risk_icon(level: str) -> str:
        level = (level or "").strip().capitalize()
        if level == "Alto":
            return "🔴"
        if level == "Moderado":
            return "🟡"
        if level == "Baixo":
            return "🟢"
        return "•"

    def _short_risks(riscos_str: str) -> str:
        # Esperado: "Queda: Alto | Lesão por pressão: Moderado | ..."
        if not riscos_str:
            return ""
        parts = [p.strip() for p in str(riscos_str).split("|") if p.strip()]
        out = []
        for p in parts:
            if ":" in p:
                k, v = [x.strip() for x in p.split(":", 1)]
                out.append(f"{_risk_icon(v)} {k}")
            else:
                out.append(p)
        return "  ".join(out)

    df_pdf["Riscos"] = df_pdf["Riscos"].apply(_short_risks)

    # Ordena por leito
    if "Leito" in df_pdf.columns:
        df_pdf["Leito"] = pd.to_numeric(df_pdf["Leito"], errors="coerce")
        df_pdf = df_pdf.sort_values("Leito", na_position="last")

    # Converte células longas para Paragraph para permitir quebra de linha
    header = list(df_pdf.columns)
    table_data = [header]
    for _, row in df_pdf.iterrows():
        r = []
        for col in header:
            val = "" if pd.isna(row[col]) else str(row[col])
            if col == "Riscos":
                # Permite quebra de linha automática no PDF
                val = Paragraph(val.replace("  ", "<br/>"), normal)
            r.append(val)
        table_data.append(r)

    # Larguras pensadas para A4 paisagem
    col_widths = [45, 60, 55, 85, 455]  # Leito, Iniciais, IRAH, Classificação, Riscos

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 10))
    elements.append(
        Paragraph(
            "Observação: ferramenta de apoio assistencial. Utilize julgamento clínico profissional.",
            styles["Normal"],
        )
    )

    doc.build(elements)
    return buffer.getvalue()

# ============================================================
# SESSION STATE (sem persistência real)
# ============================================================
if "patients" not in st.session_state:
    st.session_state.patients = []
if "last_added" not in st.session_state:
    st.session_state.last_added = None  # backup rápido (último paciente)

# ============================================================
# ABA PRINCIPAL
# ============================================================
with tab_calc:
    st.title("🩺 IRAH–Premier — Avaliação Assistencial")
    st.caption("Dica operacional: após inserir alguns pacientes, baixe o CSV/PDF para garantir backup local.")

    iniciais = st.text_input("Iniciais do paciente (ex.: JAS)", key="iniciais_input").strip().upper()
    leito = st.number_input("Leito (1 a 20)", min_value=1, max_value=20, step=1, key="leito_input")

    st.markdown("---")

    # FUGULIN
    st.subheader("🧾 Escala de Fugulin (12 itens — com texto)")
    fugulin_scores = {}
    cols = st.columns(3)
    for i, (domain, options) in enumerate(FUGULIN_SCALE.items()):
        with cols[i % 3]:
            label_map = {f"{k} – {v}": k for k, v in options.items()}
            selected_label = st.selectbox(domain, list(label_map.keys()), index=0, key=f"fug_{domain}")
            fugulin_scores[domain] = int(label_map[selected_label])

    fugulin_total = int(sum(fugulin_scores.values()))
    fugulin_cat = fugulin_classification(fugulin_total)
    st.info(f"**Fugulin total:** {fugulin_total}  |  **Classificação:** {fugulin_cat}")

    st.markdown(
        """<small>
        Classificação Fugulin: Mínimo (12–17) • Intermediário (18–22) • Alta dependência (23–28) • Semi-intensivo (28–34) • Intensivo (&gt;34).
        <br><b>Regra do app:</b> 28–34 = Semi-intensivo; 23–27 = Alta dependência.
        </small>""",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # CHARLSON
    st.subheader("🧬 Índice de Charlson (checklist)")
    c1, c2 = st.columns([1, 1])
    with c1:
        age = st.number_input("Idade (opcional)", min_value=0, max_value=120, step=1, key="age_input")
    with c2:
        use_age_adjust = st.checkbox("Aplicar ajuste por idade no Charlson", value=False, key="use_age_adjust")

    charlson_checks = {}
    cols_c = st.columns(2)
    items = list(CHARLSON_ITEMS.items())
    for i, (name, weight) in enumerate(items):
        with cols_c[i % 2]:
            charlson_checks[name] = st.checkbox(f"{name} (+{weight})", key=f"ch_{name}")

    charlson_base = int(sum(CHARLSON_ITEMS[name] for name, checked in charlson_checks.items() if checked))
    charlson_age = int(charlson_age_points(int(age))) if use_age_adjust else 0
    charlson_total = int(charlson_base + charlson_age)
    st.info(f"**Charlson (base):** {charlson_base}  |  **Idade:** {charlson_age}  |  **Charlson total:** {charlson_total}")

    st.markdown("---")

    # OUTRAS ESCALAS
    st.subheader("⚙️ Outras escalas")
    mrc = st.number_input("MRC (0 a 60)", min_value=0, max_value=60, step=1, key="mrc_input")
    asg = st.selectbox("ASG", ["A", "B", "C"], index=0, key="asg_input")
    fois_label = st.selectbox("FOIS", list(FOIS_LABEL_MAP.keys()), index=6, key="fois_input")
    fois = int(FOIS_LABEL_MAP[fois_label])
    poly = st.number_input("Polifarmácia (nº de medicamentos contínuos)", min_value=0, max_value=50, step=1, key="poly_input")

    # ============================================================
    # CÁLCULO IRAH–Premier
    # ============================================================
    charlson_norm = normalize_charlson(charlson_total)
    fugulin_norm = normalize_fugulin(fugulin_total)
    mrc_norm = normalize_mrc(mrc)
    asg_norm = normalize_asg(asg)
    fois_norm = normalize_fois(fois)
    poly_norm = normalize_poly(poly)

    trigger_high = (fois <= 3) or (poly >= 13) or (mrc <= 35)

    # ============================================================
    # RISCOS IDENTIFICADOS (CHECKLIST DE SEGURANÇA)
    # ============================================================
    fug_deamb = int(fugulin_scores.get("Deambulação", 1) or 1)
    riscos = {
        "Queda": risk_queda(mrc, fug_deamb),
        "Lesão por pressão": risk_lpp(fugulin_scores),
        "Broncoaspiração": risk_broncoaspiracao(fois),
        "Nutricional": risk_nutricional(asg, fois),
        "Medicamentoso": risk_medicamentoso(poly),
    }
    riscos_str = " | ".join([f"{k}: {v}" for k, v in riscos.items()])


    irah = (
        charlson_norm * WEIGHTS["Charlson"]
        + fugulin_norm * WEIGHTS["Fugulin"]
        + mrc_norm * WEIGHTS["MRC"]
        + asg_norm * WEIGHTS["ASG"]
        + fois_norm * WEIGHTS["FOIS"]
        + poly_norm * WEIGHTS["Polifarmacia"]
    )
    irah = round(float(irah), 1)
    risco = classify(irah, trigger_high)

    st.markdown("---")
    st.subheader("Resultado do paciente")
    st.metric("IRAH–Premier (0–100)", f"{irah}")

    if risco == "Baixo":
        st.success("Classificação: Baixo")
    elif risco == "Moderado":
        st.warning("Classificação: Moderado")
    else:
        st.error("Classificação: Alto")

    if trigger_high:
        st.info("⚠️ Gatilho de alto risco ativado (FOIS ≤ 3, Polifarmácia ≥ 13 ou MRC ≤ 35).")


    st.markdown("### 🧷 Riscos identificados (segurança clínica)")
    for k, v in riscos.items():
        if v == "Alto":
            st.error(f"🔴 {k}: {v}")
        elif v == "Moderado":
            st.warning(f"🟡 {k}: {v}")
        else:
            st.success(f"🟢 {k}: {v}")


    with st.expander("Ver detalhes do cálculo (normalização e contribuição)"):
        df_detail = pd.DataFrame(
            [
                ["Charlson", charlson_total, round(charlson_norm, 1), WEIGHTS["Charlson"], round(charlson_norm * WEIGHTS["Charlson"], 1)],
                ["Fugulin", fugulin_total, round(fugulin_norm, 1), WEIGHTS["Fugulin"], round(fugulin_norm * WEIGHTS["Fugulin"], 1)],
                ["MRC", mrc, round(mrc_norm, 1), WEIGHTS["MRC"], round(mrc_norm * WEIGHTS["MRC"], 1)],
                ["ASG", asg, round(asg_norm, 1), WEIGHTS["ASG"], round(asg_norm * WEIGHTS["ASG"], 1)],
                ["FOIS", fois, round(fois_norm, 1), WEIGHTS["FOIS"], round(fois_norm * WEIGHTS["FOIS"], 1)],
                ["Polifarmácia", poly, round(poly_norm, 1), WEIGHTS["Polifarmacia"], round(poly_norm * WEIGHTS["Polifarmacia"], 1)],
            ],
            columns=["Escala", "Entrada", "Normalizado (0–100)", "Peso", "Contribuição"],
        )
        st.dataframe(df_detail, use_container_width=True)

    # ============================================================
    # AÇÕES — CLÍNICA (20 leitos)
    # ============================================================
    st.markdown("---")
    st.subheader("Clínica (20 leitos) — Lista e Exportação")

    a1, a2, a3 = st.columns(3)
    with a1:
        add = st.button("➕ Adicionar/Atualizar leito", use_container_width=True)
    with a2:
        remove = st.button("🗑️ Remover leito", use_container_width=True)
    with a3:
        clear = st.button("♻️ Limpar lista", use_container_width=True)

    # Registro do paciente (somente tipos simples + JSON em string)
    fugulin_json = safe_json_dumps(fugulin_scores)
    charlson_list = [k for k, v in charlson_checks.items() if v]
    charlson_json = safe_json_dumps(charlson_list)

    patient_record = {
        "Leito": int(leito),
        "Iniciais": iniciais,
        "IRAH_Premier": float(irah),
        "Risco": risco,
        "Gatilho_Alto": "SIM" if trigger_high else "",
        "Fugulin_total": int(fugulin_total),
        "Fugulin_classificacao": fugulin_cat,
        "Charlson_total": int(charlson_total),
        "Charlson_base": int(charlson_base),
        "Charlson_idade_pts": int(charlson_age),
        "MRC": int(mrc),
        "ASG": asg,
        "FOIS": int(fois),
        "Polifarmacia": int(poly),
        "Fugulin_detalhes_json": fugulin_json,
        "Charlson_detalhes_json": charlson_json,
        "Riscos_identificados": riscos_str,
        "Risco_queda": riscos["Queda"],
        "Risco_LPP": riscos["Lesão por pressão"],
        "Risco_broncoaspiracao": riscos["Broncoaspiração"],
        "Risco_nutricional": riscos["Nutricional"],
        "Risco_medicamentoso": riscos["Medicamentoso"],
    }

    if add:
        if not iniciais:
            st.error("Informe as **iniciais do paciente** antes de adicionar.")
        else:
            st.session_state.patients = [p for p in st.session_state.patients if int(p.get("Leito", -1)) != int(leito)]
            st.session_state.patients.append(patient_record)
            st.session_state.last_added = patient_record
            st.success(f"Leito {int(leito)} atualizado para {iniciais}.")

    if remove:
        before = len(st.session_state.patients)
        st.session_state.patients = [p for p in st.session_state.patients if int(p.get("Leito", -1)) != int(leito)]
        after = len(st.session_state.patients)
        if after < before:
            st.success(f"Leito {int(leito)} removido.")
        else:
            st.info(f"Não havia paciente cadastrado no leito {int(leito)}.")

    if clear:
        st.session_state.patients = []
        st.session_state.last_added = None
        st.success("Lista da clínica limpa.")

    # ============================================================
    # BACKUP RÁPIDO
    # ============================================================
    if st.session_state.last_added:
        st.markdown("### ✅ Backup rápido do último paciente")
        last_df = pd.DataFrame([st.session_state.last_added])
        st.download_button(
            "⬇️ Baixar CSV (último paciente)",
            data=last_df.to_csv(index=False).encode("utf-8"),
            file_name=f"irah_premier_leito_{int(st.session_state.last_added['Leito'])}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ============================================================
    # TABELA + MÉTRICAS + EXPORTAÇÃO (SEGURO)
    # ============================================================
    if st.session_state.patients:
        df = pd.DataFrame(st.session_state.patients)

        display_cols = [
            "Leito",
            "Iniciais",
            "IRAH_Premier",
            "Risco",
            "Riscos_identificados",
        ]

        df = df.reindex(columns=display_cols + ["Fugulin_detalhes_json", "Charlson_detalhes_json"], fill_value="")
        df["Leito"] = pd.to_numeric(df["Leito"], errors="coerce")
        df["IRAH_Premier"] = pd.to_numeric(df["IRAH_Premier"], errors="coerce")
        df = df.sort_values("Leito", na_position="last")

        st.dataframe(df[display_cols], use_container_width=True)

        total = int(df["Leito"].notna().sum())
        baixo = int((df["Risco"] == "Baixo").sum())
        moderado = int((df["Risco"] == "Moderado").sum())
        alto = int((df["Risco"] == "Alto").sum())

        if df["IRAH_Premier"].notna().any():
            media = round(float(df["IRAH_Premier"].dropna().mean()), 1)
            mediana = round(float(df["IRAH_Premier"].dropna().median()), 1)
            carga_total = round(float(df["IRAH_Premier"].dropna().sum()), 1)
        else:
            media, mediana, carga_total = 0.0, 0.0, 0.0

        ocupacao = f"{total}/20"
        complexidade_global = "Baixa" if media < 34 else "Moderada" if media < 67 else "Alta"
        distribuicao = f"🟢 Baixo: {baixo} | 🟡 Moderado: {moderado} | 🔴 Alto: {alto}"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ocupação", ocupacao)
        c2.metric("Média IRAH", f"{media}")
        c3.metric("Mediana IRAH", f"{mediana}")
        c4.metric("Carga total (soma)", f"{carga_total}")

        st.markdown(f"**Distribuição de risco:** {distribuicao}")
        st.info(f"**Complexidade assistencial global (pela média do IRAH): {complexidade_global}**")

        # CSV completo
        st.download_button(
            "⬇️ Baixar CSV completo (clínica)",
            data=df[display_cols].to_csv(index=False).encode("utf-8"),
            file_name="irah_premier_clinica.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # PDF
        summary = {
            "ocupacao": ocupacao,
            "media": str(media),
            "mediana": str(mediana),
            "carga_total": str(carga_total),
            "distribuicao": distribuicao,
            "complexidade_global": complexidade_global,
        }
        pdf_bytes = build_pdf(df[display_cols], summary)
        st.download_button(
            "⬇️ Baixar PDF (relatório da clínica)",
            data=pdf_bytes,
            file_name="irah_premier_relatorio.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        with st.expander("🔎 Ver escalas detalhadas por paciente (seguro)"):
            for _, row in df.sort_values("Leito", na_position="last").iterrows():
                if pd.isna(row.get("Leito")):
                    continue
                st.markdown(f"**Leito {int(row['Leito'])} — {row.get('Iniciais','')}**")

                colx, coly = st.columns(2)
                with colx:
                    st.markdown("**Fugulin (detalhes)**")
                    fug_det = safe_json_loads(row.get("Fugulin_detalhes_json", ""))
                    if isinstance(fug_det, dict) and fug_det:
                        for k, v in fug_det.items():
                            desc = FUGULIN_SCALE.get(k, {}).get(int(v), "")
                            st.write(f"- {k}: {v} ({desc})")
                    else:
                        st.write("- (sem detalhes)")
                with coly:
                    st.markdown("**Charlson (detalhes)**")
                    ch_list = safe_json_loads(row.get("Charlson_detalhes_json", ""))
                    if isinstance(ch_list, list) and ch_list:
                        for item in ch_list:
                            st.write(f"- {item}")
                    else:
                        st.write("- (nenhuma comorbidade marcada)")
                st.markdown("---")
    else:
        st.info("Ainda não há pacientes adicionados. Calcule e clique em **Adicionar/Atualizar leito**.")

    st.markdown(
        "<small>Ferramenta de apoio assistencial. Sempre utilize o julgamento clínico profissional junto à ferramenta.</small>",
        unsafe_allow_html=True,
    )

# ============================================================
# ABA SOBRE
# ============================================================
with tab_about:
    st.markdown("## 📘 IRAH–Premier — Documento Institucional")
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            st.markdown(f.read())
    except FileNotFoundError:
        st.info("README.md não encontrado na raiz do repositório. (Se quiser exibir aqui, adicione o arquivo no GitHub.)")
