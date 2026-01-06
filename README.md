[README_IRAH_Premier.md](https://github.com/user-attachments/files/24457871/README_IRAH_Premier.md)
# 🏥 IRAH–Premier  
**Índice de Risco Assistencial Hospitalar para Instituições de Transição de Cuidados**

## 📌 Visão Geral
O **IRAH–Premier** (Índice de Risco Assistencial Hospitalar – Premier) é um instrumento clínico-assistencial desenvolvido para **instituições de transição de cuidados**, com foco em pacientes em reabilitação, pós-eventos clínicos agudos e cuidados paliativos não exclusivos.

O índice tem como objetivo **estratificar o risco assistencial de forma padronizada**, apoiar decisões multiprofissionais e **monitorar a complexidade assistencial global da unidade**.

---

## 🎯 Objetivos do IRAH–Premier
- Identificar pacientes com **maior risco assistencial**
- Priorizar intervenções multiprofissionais
- Antecipar eventos adversos evitáveis (quedas, aspiração, delirium, reinternação)
- Monitorar a **complexidade assistencial da clínica como um todo**
- Padronizar a linguagem de risco entre equipes

---

## 🧠 Fundamentação Conceitual
Instituições de transição de cuidados concentram pacientes com:
- Alta carga de comorbidades
- Comprometimento funcional
- Risco nutricional e de disfagia
- Uso frequente de múltiplos medicamentos
- Necessidade contínua de cuidado multiprofissional

O **IRAH–Premier** foi desenhado para refletir essa **complexidade assistencial real**, indo além de modelos voltados exclusivamente ao hospital agudo.

---

## 🧩 Componentes do Índice
O IRAH–Premier é um índice composto, com escore final variando de **0 a 100**  
(**quanto maior o valor, maior o risco assistencial**).

| Dimensão | Escala | Peso |
|--------|------|------|
| Comorbidades | Índice de Charlson | 20% |
| Demanda de cuidado | Escala de Fugulin | 20% |
| Funcionalidade motora | MRC (Medical Research Council) | 15% |
| Estado nutricional | Avaliação Subjetiva Global (ASG) | 15% |
| Deglutição / ingestão oral | FOIS (Functional Oral Intake Scale) | 15% |
| Segurança medicamentosa | Polifarmácia | 15% |
| **Total** |  | **100%** |

---

## 🔢 Normalização das Escalas
Todas as escalas são **normalizadas para uma escala comum (0–100)** antes da aplicação dos pesos, garantindo:

- Transparência metodológica  
- Comparabilidade entre domínios  
- Facilidade de interpretação clínica  

---

## 🚦 Classificação de Risco
O resultado final é classificado em **três faixas simples**, para facilitar a aplicação assistencial:

| Escore IRAH–Premier | Classificação |
|-------------------|---------------|
| 0 – 33 | 🟢 Baixo risco |
| 34 – 66 | 🟡 Risco moderado |
| 67 – 100 | 🔴 Alto risco |

### ⚠️ Gatilhos de Alto Risco
Independentemente do escore final, o paciente é classificado como **Alto Risco** se apresentar **qualquer um** dos critérios abaixo:
- FOIS ≤ 3  
- Polifarmácia ≥ 13 medicamentos  
- MRC ≤ 35  

---

## 🏥 Uso Assistencial
O IRAH–Premier pode ser utilizado para:
- Planejamento e priorização de rounds multiprofissionais
- Definição da intensidade de reabilitação
- Monitoramento longitudinal da evolução clínica
- Avaliação da **complexidade assistencial global da unidade**
- Apoio à gestão e alocação de recursos

---

## 🛠️ Aplicativo (Streamlit)
Este repositório contém um **aplicativo web desenvolvido em Streamlit**, no qual:
- A entrada é feita a partir dos **escores originais das escalas**
- O sistema realiza automaticamente:
  - Normalização
  - Aplicação de pesos
  - Cálculo do IRAH–Premier
  - Classificação de risco
- Os dados são mantidos apenas durante a sessão (sem persistência de dados sensíveis)

---

## ⚠️ Aviso Importante
> O IRAH–Premier é uma **ferramenta de apoio à decisão clínica**.  
> Ele **não substitui o julgamento clínico profissional** nem protocolos institucionais específicos.

---

## 👨‍⚕️ Autoria e Desenvolvimento
Projeto desenvolvido por **Vitor Dominato Rocha**, médico e gestor em saúde,  
e **Wlademinck Reis**, enfermeiro e gestor em saúde.

---

## 📄 Licença
Projeto de uso institucional e educacional.  
Licença a ser definida conforme a política da instituição.
