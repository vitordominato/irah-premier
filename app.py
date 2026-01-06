import streamlit as st
import pandas as pd

st.set_page_config(page_title="Índice de Risco Assistencial Hospitalar", layout="centered")
st.title("💉 Índice de Risco Assistencial Hospitalar (IRAH) – Premier")
st.markdown("Preencha os campos abaixo para calcular o risco assistencial do paciente e acompanhar a complexidade da clínica (20 leitos).")

# -----------------------------
# Normalizações (0–100)
# -----------------------------
def normalize_charlson(charlson: int) -> float:
    # Normalização simples e explicável: 0–13 → 0–100 (cap em 13)
    if charlson is None:
        return 0.0
    c = max(0, min(float(charlson), 13.0))
    return (c / 13.0) * 100.0

def normalize_fugulin(score: int) -> float:
    # Faixas usuais no PCS de Fugulin (podem ser ajustadas conforme protocolo local):
    # 9–14 mínimo | 15–20 intermediário | 21–26 alta dependência | 27–31 semi-intensivo | >31 intensivo
    s = float(score or 0)
    if s <= 14:
        return 0.0
    elif s <= 20:
        return 25.0
    elif s <= 26:
        return 50.0
    elif s <= 31:
        return 75.0
    else:
        return 100.0

def normalize_mrc(mrc_total: int) -> float:
    # MRC 0–60 (quanto menor, maior risco): risco = (60 - mrc) / 60 * 100
    m = float(mrc_total or 0)
    m = max(0.0, min(m, 60.0))
    return ((60.0 - m) / 60.0) * 100.0

def normalize_asg(asg_label: str) -> float:
    # ASG: A=0, B=50, C=100
    mapping = {
        "": 0.0,
        "Bem nutrido (ASG A)": 0.0,
        "Moderadamente desnutrido (ASG B)": 50.0,
        "Gravemente desnutrido (ASG C)": 100.0
    }
    return float(mapping.get(asg_label, 0.0))

def normalize_fois(fois: int) -> float:
    # FOIS (1–7): 1→100, 2→90, 3→80, 4→60, 5→40, 6→20, 7→0
    mapping = {1: 100, 2: 90, 3: 80, 4: 60, 5: 40, 6: 20, 7: 0}
    return float(mapping.get(int(fois), 0))

def normalize_polypharmacy(n_meds: int) -> float:
    # Polifarmácia (nº meds contínuos): ≤4=0; 5–6=25; 7–9=50; 10–12=75; ≥13=100
    n = int(n_meds or 0)
    if n <= 4:
        return 0.0
    elif n <= 6:
        return 25.0
    elif n <= 9:
        return 50.0
    elif n <= 12:
        return 75.0
    else:
        return 100.0

# -----------------------------
# Pesos IRAH–Premier (100%)
# -----------------------------
WEIGHTS = {
    "Charlson": 0.20,
    "Fugulin": 0.20,
    "MRC": 0.15,
    "ASG": 0.15,
    "FOIS": 0.15,
    "Polifarmácia": 0.15,
}

def classify(score_0_100: float, trigger_high: bool) -> str:
    # 3 faixas simples + override por gatilho
    if trigger_high:
        return "Alto"
    if score_0_100 >= 67:
        return "Alto"
    elif score_0_100 >= 34:
        return "Moderado"
    return "Baixo"

# -----------------------------
# Session state (lista de pacientes)
# -----------------------------
if "patients" not in st.session_state:
    st.session_state.patients = []

# -----------------------------
# Entradas do usuário (mantendo aparência simples)
# -----------------------------
iniciais = st.text_input("Iniciais do paciente (ex.: JAS)")
leito = st.number_input("Leito (1 a 20)", min_value=1, max_value=20, step=1)

fugulin = st.number_input("Pontuação da Escala Fugulin", min_value=0, max_value=60, step=1)
asg = st.selectbox("Classificação da ASG", ["", "Bem nutrido (ASG A)", "Moderadamente desnutrido (ASG B)", "Gravemente desnutrido (ASG C)"])
mrc = st.number_input("Pontuação da Escala MRC (0 a 60)", min_value=0, max_value=60, step=1)
charlson = st.number_input("Índice de Charlson", min_value=0, max_value=50, step=1)

fois = st.number_input("FOIS (1 a 7)", min_value=1, max_value=7, step=1)
poly = st.number_input("Polifarmácia (nº de medicamentos contínuos)", min_value=0, max_value=50, step=1)

# -----------------------------
# Cálculo (normalização + pesos + gatilhos)
# -----------------------------
charlson_norm = normalize_charlson(charlson)
fugulin_norm = normalize_fugulin(fugulin)
mrc_norm = normalize_mrc(mrc)
asg_norm = normalize_asg(asg)
fois_norm = normalize_fois(fois)
poly_norm = normalize_polypharmacy(poly)

# Gatilhos (Premier): FOIS ≤3 ou Polifarmácia ≥13 ou MRC ≤35
trigger_high = (fois <= 3) or (poly >= 13) or (mrc <= 35)

irah = (
    charlson_norm * WEIGHTS["Charlson"] +
    fugulin_norm * WEIGHTS["Fugulin"] +
    mrc_norm * WEIGHTS["MRC"] +
    asg_norm * WEIGHTS["ASG"] +
    fois_norm * WEIGHTS["FOIS"] +
    poly_norm * WEIGHTS["Polifarmácia"]
)

irah = round(irah, 1)
risco = classify(irah, trigger_high)

# -----------------------------
# Resultado individual (mantendo estilo)
# -----------------------------
st.markdown("---")
st.subheader("Resultado do IRAH–Premier")
st.metric("Pontuação do IRAH–Premier (0–100)", f"{irah}")

if risco == "Baixo":
    st.success("Classificação: Baixo")
elif risco == "Moderado":
    st.warning("Classificação: Moderado")
else:
    st.error("Classificação: Alto")

if trigger_high:
    st.info("⚠️ Gatilho de alto risco ativado (FOIS ≤ 3, Polifarmácia ≥ 13 ou MRC ≤ 35).")

# Mostrar cálculo por domínio (explicável, mas compacto)
with st.expander("Ver detalhes do cálculo (normalização e contribuição)"):
    df_detail = pd.DataFrame([
        ["Charlson", charlson, charlson_norm, WEIGHTS["Charlson"], round(charlson_norm * WEIGHTS["Charlson"], 1)],
        ["Fugulin", fugulin, fugulin_norm, WEIGHTS["Fugulin"], round(fugulin_norm * WEIGHTS["Fugulin"], 1)],
        ["MRC", mrc, mrc_norm, WEIGHTS["MRC"], round(mrc_norm * WEIGHTS["MRC"], 1)],
        ["ASG", asg, asg_norm, WEIGHTS["ASG"], round(asg_norm * WEIGHTS["ASG"], 1)],
        ["FOIS", fois, fois_norm, WEIGHTS["FOIS"], round(fois_norm * WEIGHTS["FOIS"], 1)],
        ["Polifarmácia", poly, poly_norm, WEIGHTS["Polifarmácia"], round(poly_norm * WEIGHTS["Polifarmácia"], 1)],
    ], columns=["Escala", "Entrada", "Normalizado (0–100)", "Peso", "Contribuição"])
    st.dataframe(df_detail, use_container_width=True)

# -----------------------------
# Gestão da clínica (20 leitos)
# -----------------------------
col1, col2, col3 = st.columns(3)

with col1:
    add = st.button("➕ Adicionar paciente à clínica", use_container_width=True)
with col2:
    remove = st.button("🗑️ Remover paciente do leito", use_container_width=True)
with col3:
    clear = st.button("♻️ Limpar lista (clínica)", use_container_width=True)

if add:
    if not iniciais.strip():
        st.error("Preencha as iniciais do paciente para adicionar à clínica.")
    else:
        # Remove qualquer registro prévio do mesmo leito (mantém 1 paciente por leito)
        st.session_state.patients = [p for p in st.session_state.patients if p["Leito"] != int(leito)]
        st.session_state.patients.append({
            "Leito": int(leito),
            "Iniciais": iniciais.strip().upper(),
            "IRAH_Premier": irah,
            "Risco": risco,
            "Gatilho_Alto": "SIM" if trigger_high else "",
            "Charlson": int(charlson),
            "Fugulin": int(fugulin),
            "MRC": int(mrc),
            "ASG": asg,
            "FOIS": int(fois),
            "Polifarmacia": int(poly),
        })
        st.success(f"Paciente {iniciais.strip().upper()} adicionado no leito {int(leito)}.")

if remove:
    # Remove pelo leito informado
    before = len(st.session_state.patients)
    st.session_state.patients = [p for p in st.session_state.patients if p["Leito"] != int(leito)]
    after = len(st.session_state.patients)
    if after < before:
        st.success(f"Paciente removido do leito {int(leito)}.")
    else:
        st.info(f"Não havia paciente cadastrado no leito {int(leito)}.")

if clear:
    st.session_state.patients = []
    st.success("Lista da clínica limpa.")

st.markdown("---")
st.subheader("Clínica (20 leitos) – Complexidade Assistencial")

if st.session_state.patients:
    df = pd.DataFrame(st.session_state.patients).sort_values("Leito")
    st.dataframe(df[["Leito", "Iniciais", "IRAH_Premier", "Risco", "Gatilho_Alto"]], use_container_width=True)

    total = len(df)
    baixo = int((df["Risco"] == "Baixo").sum())
    moderado = int((df["Risco"] == "Moderado").sum())
    alto = int((df["Risco"] == "Alto").sum())

    media = round(df["IRAH_Premier"].mean(), 1)
    mediana = round(df["IRAH_Premier"].median(), 1)
    carga_total = round(df["IRAH_Premier"].sum(), 1)  # “pontos de risco” acumulados
    ocupacao = f"{total}/20"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ocupação", ocupacao)
    c2.metric("Média IRAH", f"{media}")
    c3.metric("Mediana IRAH", f"{mediana}")
    c4.metric("Carga total (soma)", f"{carga_total}")

    st.markdown(
        f"**Distribuição de risco:** 🟢 Baixo: **{baixo}** | 🟡 Moderado: **{moderado}** | 🔴 Alto: **{alto}**"
    )

    # Interpretação simples da complexidade global
    # (pode ajustar depois com base em dados reais)
    complexidade_global = "Baixa" if media < 34 else "Moderada" if media < 67 else "Alta"
    st.info(f"**Complexidade assistencial global da clínica (pela média do IRAH): {complexidade_global}**")

    # Exportação (CSV) para auditoria rápida
    st.download_button(
        "⬇️ Baixar lista da clínica (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="irah_premier_clinica.csv",
        mime="text/csv",
        use_container_width=True
    )
else:
    st.info("Ainda não há pacientes adicionados à lista da clínica. Use o botão **Adicionar paciente à clínica** após calcular.")

# Rodapé
st.markdown(
    "<small>Ferramenta de apoio assistencial. Sempre utilize o julgamento clínico profissional junto à ferramenta.</small>",
    unsafe_allow_html=True
)
