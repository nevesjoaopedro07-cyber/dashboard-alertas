import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata

# 1. Configuração de tela e Estilo Eldorado
st.set_page_config(page_title="Dashboard Eldorado", layout="wide", initial_sidebar_state="expanded")

# CSS para layout, cores e correção de impressão (PDF)
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    h1 {color: #004a2f; font-size: 1.8rem !important; font-weight: bold;}
    
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #004a2f;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricLabel"] {font-size: 1rem !important; font-weight: bold; color: #333 !important;}
    [data-testid="stMetricValue"] {font-size: 1.8rem !important; color: #004a2f !important; font-weight: bold !important;}

    @media print {
        header, [data-testid="stSidebar"], .stFileUploader, button, [data-testid="stDecoration"] {
            display: none !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def normalizar(texto):
    if pd.isna(texto): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').strip().upper()

# --- BARRA LATERAL ---
st.sidebar.image("https://www.eldoradobrasil.com.br/wp-content/themes/eldorado/img/logo-eldorado.png", width=150)
st.sidebar.title("Opções")

if st.sidebar.button("📄 Exportar para PDF"):
    st.components.v1.html(
        "<script>setTimeout(function() { window.print(); }, 2000);</script>",
        height=0,
    )
    st.sidebar.warning("Gerando PDF... Aguarde a janela de impressão.")

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("📂 Upload da Planilha", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="ALERTAS")
        cols_norm = {normalizar(c): c for c in df.columns}
        
        def encontrar_coluna(lista_opcoes):
            for opcao in lista_opcoes:
                norm_opcao = normalizar(opcao)
                if norm_opcao in cols_norm:
                    return cols_norm[norm_opcao]
            return None

        # Mapeamento Flexível de Colunas
        c_chapa = encontrar_coluna(["CHAPA", "MATRICULA", "ID"]) # <--- Nova coluna mapeada
        c_nome = encontrar_coluna(["NOME", "MOTORISTA"])
        c_data = encontrar_coluna(["DATA", "DATA DO ALARME"])
        c_ut = encontrar_coluna(["UNIDADE", "UT"])
        c_status = encontrar_coluna(["STATUS"])
        c_prazo = encontrar_coluna(["PRAZO", "FINALIZADA DENTRO DO PRAZO?"])
        c_tipo = encontrar_coluna(["TIPO", "TIPO DE ALERTA"])

        if not c_nome or not c_ut:
            st.error("⚠️ Colunas essenciais (NOME/UT) não encontradas.")
            st.stop()

        # Preparação dos Dados
        renomear = {c_nome: "NOME", c_ut: "UNIDADE"}
        if c_chapa: renomear[c_chapa] = "CHAPA"
        if c_data: renomear[c_data] = "DATA"
        if c_status: renomear[c_status] = "STATUS"
        if c_prazo: renomear[c_prazo] = "PRAZO"
        if c_tipo: renomear[c_tipo] = "TIPO"
        
        df_dash = df[list(renomear.keys())].copy().rename(columns=renomear)

        # --- FILTRO DE MOTORISTAS NÃO ENCONTRADOS ---
        if "CHAPA" in df_dash:
            # Remove se for "NÃO ENCONTRADO", se estiver vazio ou apenas espaços
            df_dash = df_dash[df_dash["CHAPA"].astype(str).str.upper().str.strip() != "NAO ENCONTRADO"]
            df_dash = df_dash[df_dash["CHAPA"].astype(str).str.upper().str.strip() != "NÃO ENCONTRADO"]
            df_dash = df_dash.dropna(subset=["CHAPA"])
        # --------------------------------------------
        
        if "DATA" in df_dash:
            df_dash["DATA"] = pd.to_datetime(df_dash["DATA"], errors="coerce")
        if "PRAZO" in df_dash:
            df_dash["PRAZO"] = df_dash["PRAZO"].astype(str).str.strip().str.capitalize().replace("Nao", "Não")

        # Filtros Sidebar
        uts_dispo = sorted([str(u) for u in df_dash["UNIDADE"].unique()])
        uts_sel = st.sidebar.multiselect("Filtrar Unidades", uts_dispo, default=uts_dispo)
        mask = df_dash["UNIDADE"].isin(uts_sel)
        
        if "DATA" in df_dash and not df_dash["DATA"].isnull().all():
            min_d, max_d = df_dash["DATA"].min().date(), df_dash["DATA"].max().date()
            periodo = st.sidebar.date_input("Período", [min_d, max_d])
            if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
                mask &= (df_dash["DATA"].dt.date >= periodo[0]) & (df_dash["DATA"].dt.date <= periodo[1])
        
        df_f = df_dash.loc[mask].copy()

        # --- CABEÇALHO E MÉTRICAS ---
        st.title("🌲 Gestão de Alertas | Eldorado Brasil")
        
        k1, k2, k3, k4 = st.columns(4)
        total = len(df_f)
        concluidas = len(df_f[df_f["STATUS"].isin(["Concluída", "Assinada"])]) if "STATUS" in df_f else 0
        eficiencia = f"{(concluidas/total*100):.1f}%" if total > 0 else "0%"
        no_prazo = len(df_f[df_f["PRAZO"] == "Sim"]) if "PRAZO" in df_f else 0

        k1.metric("Total de Alertas", total)
        k2.metric("Tratativas Finalizadas", concluidas)
        k3.metric("Taxa de Conclusão", eficiencia)
        k4.metric("Dentro do Prazo", no_prazo)

        st.markdown("---")

        # --- LAYOUT DE GRÁFICOS ---
        c1, c2, c3 = st.columns([1, 1, 1.2])

        with c1:
            st.subheader("🏆 Top 10 Motoristas")
            rank = df_f.groupby("NOME").size().reset_index(name="v").sort_values("v", ascending=True).tail(10)
            fig_mot = px.bar(rank, x="v", y="NOME", orientation='h', text_auto=True, height=300)
            fig_mot.update_traces(marker_color="#004a2f")
            fig_mot.update_layout(margin=dict(l=0, r=10, t=0, b=0), xaxis_visible=False, yaxis_title=None)
            st.plotly_chart(fig_mot, use_container_width=True, config={'displayModeBar': False})

            st.subheader("🏢 Alertas por Unidade")
            ut_res = df_f.groupby("UNIDADE").size().reset_index(name="v")
            fig_ut = px.bar(ut_res, x="UNIDADE", y="v", text_auto=True, height=220)
            fig_ut.update_traces(marker_color="#d4af37")
            fig_ut.update_layout(margin=dict(l=0, r=0, t=0, b=0), yaxis_visible=False)
            st.plotly_chart(fig_ut, use_container_width=True, config={'displayModeBar': False})

        with c2:
            st.subheader("📋 Status (Total)")
            if "STATUS" in df_f:
                fig_st = px.pie(df_f, names="STATUS", hole=0.5, height=260, 
                                color_discrete_sequence=["#004a2f", "#78be20", "#d62728"])
                fig_st.update_traces(textinfo='value', textfont_size=14)
                fig_st.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig_st, use_container_width=True)

            st.subheader("⏱️ No Prazo? (Total)")
            if "PRAZO" in df_f:
                df_pz = df_f[df_f["PRAZO"].isin(["Sim", "Não"])]
                fig_pz = px.pie(df_pz, names="PRAZO", hole=0.5, height=260, 
                                color_discrete_map={"Sim": "#004a2f", "Não": "#d4af37"})
                fig_pz.update_traces(textinfo='value', textfont_size=14)
                fig_pz.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig_pz, use_container_width=True)

        with c3:
            st.subheader("🚨 Tipos de Alerta")
            if "TIPO" in df_f:
                tp_res = df_f.groupby("TIPO").size().reset_index(name="v").sort_values("v", ascending=True).tail(15)
                fig_tp = px.bar(tp_res, x="v", y="TIPO", orientation='h', text_auto=True, height=540)
                fig_tp.update_traces(marker_color="#78be20")
                fig_tp.update_layout(margin=dict(l=0, r=10, t=0, b=0), xaxis_visible=False, yaxis_title=None)
                st.plotly_chart(fig_tp, use_container_width=True, config={'displayModeBar': False})

    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
    
