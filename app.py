import streamlit as st
import pandas as pd
from io import BytesIO

# PDF (ReportLab)
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
# ESCALAS – MODELOS
# ============================================================
# Fugulin (modelo descritivo 1–4 por domínio)
# Observação: há variações institucionais. Este é um modelo operacional, legível e auditável.
# Inclui 12 itens: + Integridade cutâneo-mucosa, Curativo, Tempo de curativo.
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
        4: "Cuidados complexos (ex.: drogas vasoativas)",
    },
    "Integridade cutâneo-mucosa": {
        1: "Íntegra",
        2: "Risco/alteração leve (ex.: hiperemia, pele frágil)",
        3: "Lesão superficial / UPP estágio 1–2 / dermatite importante",
        4: "Lesão extensa / UPP estágio 3–4 / ferida complexa",
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

# Charlson (pesos clássicos; checklist)
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


def charlson_age_points(age: int) -> int:
    """Ajuste por idade (opcional): 50–59:+1 | 60–69:+2 | 70–79:+3 | >=80:+4."""
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


# ============================================================
# FUGULIN – CLASSIFICAÇÃO (conforme solicitado)
# ============================================================
def fugulin_classification(score: int) -> str:
    """
    Classificação do Fugulin (informada pelo usuário):
    - Intensivo: >34
    - Semi-intensivo: 28 a 34
    - Alta dependência: 23 a 28  (há sobreposição em 28; aqui adotamos Semi-intensivo em 28–34)
    - Intermediário: 18 a 22
    - Mínimo: 12 a 17

    Regra aplicada para evitar ambiguidade:
    - 28–34 => Semi-intensivo
    - 23–27 => Alta dependência
    """
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
    return "Fora da faixa esperada"


# ============================================================
# NORMALIZAÇÕES (0–100) + PESOS
# ============================================================
def normalize_charlson(charlson_total: int) -> float:
    """Charlson: cap em 13 e normalização contínua."""
    c = float(charlson_total or 0)
    c = max(0.0, min(c, 13.0))
    return (c / 13.0) * 100.0


def normalize_fugulin(fugulin_total: int) -> float:
    """
    Normalização Fugulin (0–100) baseada nas faixas operacionais:
    - Mínimo (12–17) -> 0
    - Intermediário (18–22) -> 25
    - Alta dependência (23–27) -> 50
    - Semi-intensivo (28–34) -> 75
    - Intensivo (>34) -> 100

    (Adotando 28 como Semi-intensivo para resolver a sobreposição descrita no texto.)
    """
    s = int(fugulin_total or 0)
    if s > 34:
        return 100.0
    if 28 <= s <= 34:
        return 75.0
    if 23 <= s <= 27:
        return 50.0
    if 18 <= s <= 22:
        return 25.0
    if 12 <= s <= 17:
        return 0.0
    # fora da faixa (ex.: score <12) — mantém 0 para não inflar risco
    return 0.0


def normalize_mrc(mrc_total: int) -> float:
    """MRC 0–60: risco = (60 - mrc)/60*100."""
    m = float(mrc_total or 0)
    m = max(0.0, min(m, 60.0))
    return ((60.0 - m) / 60.0) * 100.0


def normalize_asg(asg_label: str) -> float:
    """ASG: A=0, B=50, C=100."""
    mapping = {"A": 0.0, "B": 50.0, "C": 100.0}
    return float(mapping.get(asg_label, 0.0))


def normalize_fois(fois: int) -> float:
    """FOIS: 1→100, 2→90, 3→80, 4→60, 5→40, 6→20, 7→0."""
    mapping = {1: 100, 2: 90, 3: 80, 4: 60, 5: 40, 6: 20, 7: 0}
    return float(mapping.get(int(fois), 0.0))


def normalize_polypharmacy(n_meds: int) -> float:
    """Polifarmácia: ≤4=0; 5–6=25; 7–9=50; 10–12=75; ≥13=100."""
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


WEIGHTS = {
    "Charlson": 0.20,
    "Fugulin": 0.20,
    "MRC": 0.15,
    "ASG": 0.15,
    "FOIS": 0.15,
    "Polifarmácia": 0.15,
}


def classify(score_0_100: float, trigger_high: bool) -> str:
    """3 faixas (baixo/moderado/alto) + override por gatilho."""
    if trigger_high:
        return "Alto"
    if score_0_100 >= 67:
        return "Alto"
    if score_0_100 >= 34:
        return "Moderado"
    return "Baixo"


# ============================================================
# PDF
# ============================================================
def build_pdf(df: pd.DataFrame, summary: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
    )
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph("IRAH–Premier — Relatório Assistencial", styles["Title"]))
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
    t_sum = Table(summary_rows, colWidths=[180, 330])
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
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Lista de pacientes", styles["Heading2"]))
    elements.append(Spacer(1, 6))

    cols = [
        "Leito",
        "Iniciais",
        "IRAH_Premier",
        "Risco",
        "Gatilho_Alto",
        "Fugulin_total",
        "Fugulin_classificacao",
        "Charlson_total",
        "MRC",
        "ASG",
        "FOIS",
        "Polifarmacia",
    ]
    df_export = df.copy()
    for c in cols:
        if c not in df_export.columns:
            df_export[c] = ""
    df_export = df_export[cols].sort_values("Leito")

    table_data = [cols] + df_export.astype(str).values.tolist()
    t = Table(table_data, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
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
# SESSION STATE
# ============================================================
if "patients" not in st.session_state:
    st.session_state.patients = []


# ============================================================
# ABA PRINCIPAL
# ============================================================
with tab_calc:
    st.title("🩺 IRAH–Premier — Avaliação Assistencial")
    st.markdown(
        "Preencha as escalas para calcular o **IRAH–Premier** por paciente e acompanhar a "
        "**complexidade assistencial da unidade (20 leitos)**."
    )

    # -----------------------------
    # Identificação mínima
    # -----------------------------
    iniciais = st.text_input("Iniciais do paciente (ex.: JAS)", key="iniciais_input").strip().upper()
    leito = st.number_input("Leito (1 a 20)", min_value=1, max_value=20, step=1, key="leito_input")

    st.markdown("---")

    # -----------------------------
    # FUGULIN (com descrições)
    # -----------------------------
    st.subheader("🧾 Escala de Fugulin (preenchimento completo)")
    fugulin_scores = {}
    cols = st.columns(3)
    for i, (domain, options) in enumerate(FUGULIN_SCALE.items()):
        with cols[i % 3]:
            label_map = {f"{k} – {v}": k for k, v in options.items()}
            selected_label = st.selectbox(
                domain,
                list(label_map.keys()),
                index=0,
                key=f"fug_{domain}",
            )
            fugulin_scores[domain] = int(label_map[selected_label])

    fugulin_total = int(sum(fugulin_scores.values()))
    fugulin_cat = fugulin_classification(fugulin_total)

    st.info(f"**Fugulin total:** {fugulin_total}  |  **Classificação:** {fugulin_cat}")

    st.markdown(
        """<small>
        Classificação Fugulin (operacional): <br>
        • Mínimo (12–17) • Intermediário (18–22) • Alta dependência (23–28) • Semi-intensivo (28–34) • Intensivo (&gt;34)
        </small>""",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # -----------------------------
    # CHARLSON (checklist)
    # -----------------------------
    st.subheader("🧬 Índice de Charlson (preenchimento completo)")
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

    st.info(
        f"**Charlson (base):** {charlson_base}  |  **Idade:** {charlson_age}  |  **Charlson total:** {charlson_total}"
    )

    st.markdown("---")

    # -----------------------------
    # DEMAIS ESCALAS (entrada direta)
    # -----------------------------
    st.subheader("⚙️ Demais escalas (entrada direta)")
    mrc = st.number_input("MRC (0 a 60)", min_value=0, max_value=60, step=1, key="mrc_input")
    asg = st.selectbox("ASG", ["A", "B", "C"], index=0, key="asg_input")

    fois_label_map = {
        "1 – Nutrição alternativa (não oral)": 1,
        "2 – Via alternativa predominante com ingestão oral mínima": 2,
        "3 – Ingestão oral consistente + via alternativa": 3,
        "4 – Ingestão oral de consistência única": 4,
        "5 – Ingestão oral com preparação especial": 5,
        "6 – Ingestão oral com restrição mínima": 6,
        "7 – Ingestão oral plena (sem restrições)": 7,
    }
    fois_label = st.selectbox("FOIS", list(fois_label_map.keys()), index=6, key="fois_input")
    fois = int(fois_label_map[fois_label])

    poly = st.number_input(
        "Polifarmácia (nº de medicamentos contínuos)",
        min_value=0,
        max_value=50,
        step=1,
        key="poly_input",
    )

    # -----------------------------
    # CÁLCULO IRAH–Premier
    # -----------------------------
    charlson_norm = normalize_charlson(charlson_total)
    fugulin_norm = normalize_fugulin(fugulin_total)
    mrc_norm = normalize_mrc(mrc)
    asg_norm = normalize_asg(asg)
    fois_norm = normalize_fois(fois)
    poly_norm = normalize_polypharmacy(poly)

    # Gatilhos de alto risco (Premier)
    trigger_high = (fois <= 3) or (poly >= 13) or (mrc <= 35)

    irah = (
        charlson_norm * WEIGHTS["Charlson"]
        + fugulin_norm * WEIGHTS["Fugulin"]
        + mrc_norm * WEIGHTS["MRC"]
        + asg_norm * WEIGHTS["ASG"]
        + fois_norm * WEIGHTS["FOIS"]
        + poly_norm * WEIGHTS["Polifarmácia"]
    )
    irah = round(float(irah), 1)
    risco = classify(irah, trigger_high)

    # -----------------------------
    # RESULTADO INDIVIDUAL
    # -----------------------------
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

    with st.expander("Ver detalhes do cálculo (normalização e contribuição)"):
        df_detail = pd.DataFrame(
            [
                ["Charlson", charlson_total, round(charlson_norm, 1), WEIGHTS["Charlson"], round(charlson_norm * WEIGHTS["Charlson"], 1)],
                ["Fugulin", fugulin_total, round(fugulin_norm, 1), WEIGHTS["Fugulin"], round(fugulin_norm * WEIGHTS["Fugulin"], 1)],
                ["MRC", mrc, round(mrc_norm, 1), WEIGHTS["MRC"], round(mrc_norm * WEIGHTS["MRC"], 1)],
                ["ASG", asg, round(asg_norm, 1), WEIGHTS["ASG"], round(asg_norm * WEIGHTS["ASG"], 1)],
                ["FOIS", fois, round(fois_norm, 1), WEIGHTS["FOIS"], round(fois_norm * WEIGHTS["FOIS"], 1)],
                ["Polifarmácia", poly, round(poly_norm, 1), WEIGHTS["Polifarmácia"], round(poly_norm * WEIGHTS["Polifarmácia"], 1)],
            ],
            columns=["Escala", "Entrada", "Normalizado (0–100)", "Peso", "Contribuição"],
        )
        st.dataframe(df_detail, use_container_width=True)

    # -----------------------------
    # AÇÕES – CLÍNICA (20 leitos)
    # -----------------------------
    st.markdown("---")
    st.subheader("Clínica (20 leitos) — Lista e Complexidade Assistencial")

    a1, a2, a3 = st.columns(3)
    with a1:
        add = st.button("➕ Adicionar/Atualizar leito", use_container_width=True)
    with a2:
        remove = st.button("🗑️ Remover leito", use_container_width=True)
    with a3:
        clear = st.button("♻️ Limpar lista", use_container_width=True)

    if add:
        if not iniciais:
            st.error("Informe as **iniciais do paciente** antes de adicionar.")
        else:
            # 1 paciente por leito (atualiza se já existir)
            st.session_state.patients = [p for p in st.session_state.patients if int(p.get("Leito", -1)) != int(leito)]

            st.session_state.patients.append(
                {
                    "Leito": int(leito),
                    "Iniciais": iniciais,
                    "IRAH_Premier": irah,
                    "Risco": risco,
                    "Gatilho_Alto": "SIM" if trigger_high else "",
                    "Fugulin_total": int(fugulin_total),
                    "Fugulin_classificacao": fugulin_cat,
                    "Fugulin_detalhes": fugulin_scores,  # dicionário por domínio
                    "Charlson_total": int(charlson_total),
                    "Charlson_base": int(charlson_base),
                    "Charlson_idade_pts": int(charlson_age),
                    "Charlson_detalhes": [k for k, v in charlson_checks.items() if v],
                    "MRC": int(mrc),
                    "ASG": asg,
                    "FOIS": int(fois),
                    "Polifarmacia": int(poly),
                }
            )
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
        st.success("Lista da clínica limpa.")

    # -----------------------------
    # TABELA + EXPORTAÇÕES
    # -----------------------------
    if st.session_state.patients:
        df = pd.DataFrame(st.session_state.patients).sort_values("Leito")

        st.dataframe(
            df[
                [
                    "Leito",
                    "Iniciais",
                    "IRAH_Premier",
                    "Risco",
                    "Gatilho_Alto",
                    "Fugulin_total",
                    "Fugulin_classificacao",
                    "Charlson_total",
                    "MRC",
                    "ASG",
                    "FOIS",
                    "Polifarmacia",
                ]
            ],
            use_container_width=True,
        )

        total = int(len(df))
        baixo = int((df["Risco"] == "Baixo").sum())
        moderado = int((df["Risco"] == "Moderado").sum())
        alto = int((df["Risco"] == "Alto").sum())

        media = round(float(df["IRAH_Premier"].mean()), 1)
        mediana = round(float(df["IRAH_Premier"].median()), 1)
        carga_total = round(float(df["IRAH_Premier"].sum()), 1)
        ocupacao = f"{total}/20"
        complexidade_global = "Baixa" if media < 34 else "Moderada" if media < 67 else "Alta"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ocupação", ocupacao)
        c2.metric("Média IRAH", f"{media}")
        c3.metric("Mediana IRAH", f"{mediana}")
        c4.metric("Carga total (soma)", f"{carga_total}")

        distribuicao = f"🟢 Baixo: {baixo} | 🟡 Moderado: {moderado} | 🔴 Alto: {alto}"
        st.markdown(f"**Distribuição de risco:** {distribuicao}")
        st.info(f"**Complexidade assistencial global da clínica (pela média do IRAH): {complexidade_global}**")

        # CSV completo (inclui detalhes em colunas serializadas)
        df_csv = df.copy()
        for col in ["Fugulin_detalhes", "Charlson_detalhes"]:
            if col in df_csv.columns:
                df_csv[col] = df_csv[col].apply(lambda x: str(x))

        st.download_button(
            "⬇️ Baixar CSV completo (clínica)",
            data=df_csv.to_csv(index=False).encode("utf-8"),
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
        pdf_bytes = build_pdf(df, summary)
        st.download_button(
            "⬇️ Baixar PDF (relatório da clínica)",
            data=pdf_bytes,
            file_name="irah_premier_relatorio.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        with st.expander("🔎 Ver escalas detalhadas por paciente"):
            for _, row in df.sort_values("Leito").iterrows():
                st.markdown(f"**Leito {int(row['Leito'])} — {row['Iniciais']}**")
                colx, coly = st.columns(2)
                with colx:
                    st.markdown("**Fugulin (detalhes)**")
                    fug_det = row.get("Fugulin_detalhes", {})
                    if isinstance(fug_det, dict) and fug_det:
                        for k, v in fug_det.items():
                            desc = FUGULIN_SCALE.get(k, {}).get(int(v), "")
                            st.write(f"- {k}: {v} ({desc})")
                    else:
                        st.write("- (sem detalhes)")
                with coly:
                    st.markdown("**Charlson (detalhes)**")
                    ch_list = row.get("Charlson_detalhes", [])
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
# ABA SOBRE (README.md)
# ============================================================
with tab_about:
    st.markdown("## 📘 IRAH–Premier — Documento Institucional")
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            st.markdown(f.read())
    except FileNotFoundError:
        st.warning("README.md não encontrado na raiz do repositório.")
