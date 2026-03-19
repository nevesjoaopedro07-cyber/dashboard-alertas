import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import unicodedata

# 1. Configuração de tela e Estilo Eldorado
st.set_page_config(page_title="Dashboard Eldorado", layout="wide", initial_sidebar_state="expanded")

# --- CSS UNIFICADO E CORRIGIDO ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    h1 {color: #004a2f; font-size: 1.8rem !important; font-weight: bold;}
    
    /* Estilo das Métricas - CORREÇÃO DE VISIBILIDADE */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #004a2f;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    /* Título principal da métrica (ex: Total de Alertas) */
    [data-testid="stMetricLabel"] {
        font-size: 1rem !important; 
        font-weight: bold; 
        color: #333333 !important; /* Cinza Escuro para visibilidade */
    }
    /* Valor da métrica (ex: 227) */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important; 
        color: #004a2f !important; 
        font-weight: bold !important;
    }
    /* Texto de ajuda/subrótulo abaixo da métrica */
    [data-testid="stMetricHelpText"] p {
        color: #666666 !important; /* Cinza médio para visibilidade */
    }

    /* Botões LARGOS e ROBUSTOS (Design Mantido) */
    .stHorizontalBlock {
        display: flex !important;
        flex-direction: row !important;
        overflow-x: auto !important; 
        gap: 15px !important;
        padding-bottom: 10px;
    }
    div.stButton > button {
        background-color: #ffffff;
        color: #004a2f;
        border: none;
        border-bottom: 6px solid #78be20;
        border-radius: 12px;
        min-width: 200px !important; 
        height: 90px !important;
        box-shadow: 3px 3px 10px rgba(0,0,0,0.1);
        transition: 0.3s;
    }
    div.stButton > button p {
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }

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

# --- CONTROLE DE NAVEGAÇÃO ---
if 'pagina' not in st.session_state:
    st.session_state.pagina = 'dashboard_principal'

# --- SIDEBAR FIXA ---
st.sidebar.image("https://www.eldoradobrasil.com.br/wp-content/themes/eldorado/img/logo-eldorado.png", width=150)
st.sidebar.title("Menu")

if st.sidebar.button("📊 Dashboard Geral"):
    st.session_state.pagina = 'dashboard_principal'

if st.sidebar.button("📑 Fechamento das UTs"):
    st.session_state.pagina = 'fechamento_uts'

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("📂 Upload da Planilha", type=["xlsx"])

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file, sheet_name="ALERTAS")
        cols_norm = {normalizar(c): c for c in df_raw.columns}
        
        def encontrar_coluna(lista_opcoes):
            for opcao in lista_opcoes:
                norm_opcao = normalizar(opcao)
                if norm_opcao in cols_norm: return cols_norm[norm_opcao]
            return None

        # Mapeamento
        c_chapa = encontrar_coluna(["CHAPA", "MATRICULA", "ID"])
        c_nome = encontrar_coluna(["NOME", "MOTORISTA"])
        c_data = encontrar_coluna(["DATA", "DATA DO ALARME"])
        c_ut = encontrar_coluna(["UNIDADE", "UT"])
        c_status = encontrar_coluna(["STATUS"])
        c_prazo = encontrar_coluna(["PRAZO", "FINALIZADA DENTRO DO PRAZO?"])
        c_tipo = encontrar_coluna(["TIPO", "TIPO DE ALERTA"])

        # Limpeza Inicial
        df = df_raw.copy()
        if c_chapa:
            df = df[~df[c_chapa].astype(str).str.upper().str.contains("NAO ENCONTRADO|NÃO ENCONTRADO", na=True)]
        
        # FILTRO DE DATA
        if c_data:
            df[c_data] = pd.to_datetime(df[c_data], errors="coerce")
            df = df.dropna(subset=[c_data])
            st.sidebar.subheader("📅 Período")
            min_d, max_d = df[c_data].min().date(), df[c_data].max().date()
            periodo = st.sidebar.date_input("Intervalo", [min_d, max_d])
            if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
                df = df[(df[c_data].dt.date >= periodo[0]) & (df[c_data].dt.date <= periodo[1])]

        # ==========================================
        # TELA 1: DASHBOARD GERAL
        # ==========================================
        if st.session_state.pagina == 'dashboard_principal':
            st.title("🌲 Gestão de Alertas | Dashboard Geral")
            
            uts_dispo = sorted([str(u) for u in df[c_ut].unique()])
            uts_sel = st.sidebar.multiselect("Filtrar Unidades", uts_dispo, default=uts_dispo)
            df_f = df[df[c_ut].isin(uts_sel)].copy()
            
            # Métricas
            k1, k2, k3, k4 = st.columns(4)
            total = len(df_f)
            concluidas = len(df_f[df_f[c_status].isin(["Concluída", "Assinada"])]) if c_status else 0
            eficiencia = f"{(concluidas/total*100):.1f}%" if total > 0 else "0%"
            
            # Correção No Prazo
            df_prazo_clean = df_f[df_f[c_prazo].astype(str).str.capitalize().isin(["Sim", "Não"])] if c_prazo else pd.DataFrame()
            no_prazo = len(df_prazo_clean[df_prazo_clean[c_prazo].astype(str).str.capitalize() == "Sim"])

            k1.metric("Total de Alertas", total, help="Todos os alertas no período")
            k2.metric("Tratativas Finalizadas", concluidas, help="Status Concluída ou Assinada")
            k3.metric("Taxa de Conclusão", eficiencia, help="Percentual de tratativas finalizadas")
            k4.metric("Dentro do Prazo", no_prazo, help="Alertas com Prazo = Sim")

            st.markdown("---")
            c1, c2, c3 = st.columns([1, 1, 1.2])

            with c1:
                st.subheader("🏆 Top 10 Motoristas")
                rank = df_f.groupby(c_nome).size().reset_index(name="v").sort_values("v", ascending=True).tail(10)
                fig_mot = px.bar(rank, x="v", y=c_nome, orientation='h', text_auto=True, height=300)
                fig_mot.update_traces(marker_color="#004a2f")
                fig_mot.update_layout(margin=dict(l=0, r=10, t=0, b=0), xaxis_visible=False, yaxis_title=None)
                st.plotly_chart(fig_mot, use_container_width=True)

                st.subheader("📈 Acumulado por Mês")
                df_mes = df_f.copy()
                df_mes['PERIODO'] = df_mes[c_data].dt.to_period('M')
                resumo_mes = df_mes.groupby('PERIODO').size().reset_index(name='v').sort_values('PERIODO')
                resumo_mes['MES_ANO'] = resumo_mes['PERIODO'].dt.strftime('%m/%y')
                fig_mes = px.bar(resumo_mes, x="MES_ANO", y="v", text="v", height=220)
                fig_mes.update_traces(marker_color="#d4af37", textposition="inside", textangle=0, textfont=dict(color="white", size=14))
                fig_mes.update_layout(margin=dict(l=0, r=0, t=25, b=0), yaxis_visible=False, xaxis_title=None, xaxis=dict(type='category'))
                st.plotly_chart(fig_mes, use_container_width=True)

            with c2:
                # --- CORREÇÃO 2: GRÁFICO DE STATUS COM NÚMEROS (NÃO PERCENTUAL) ---
                st.subheader("📋 Status (Total)")
                fig_st = px.pie(df_f, names=c_status, hole=0.5, height=260, 
                                color_discrete_sequence=["#004a2f", "#78be20", "#d62728"])
                # Mudança de 'percent' para 'value'
                fig_st.update_traces(textinfo='value', textfont_size=14) 
                fig_st.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig_st, use_container_width=True)

                st.subheader("⏱️ No Prazo? (Total)")
                fig_pz = px.pie(df_prazo_clean, names=c_prazo, hole=0.5, height=260, color_discrete_map={"Sim": "#004a2f", "Não": "#d4af37"})
                fig_pz.update_traces(textinfo='value')
                fig_pz.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig_pz, use_container_width=True)

            with c3:
                st.subheader("🚨 Tipos de Alerta")
                tp_res = df_f.groupby(c_tipo).size().reset_index(name="v").sort_values("v", ascending=True).tail(15)
                fig_tp = px.bar(tp_res, x="v", y=c_tipo, orientation='h', text_auto=True, height=540)
                fig_tp.update_traces(marker_color="#78be20")
                fig_tp.update_layout(margin=dict(l=0, r=10, t=0, b=0), xaxis_visible=False, yaxis_title=None)
                st.plotly_chart(fig_tp, use_container_width=True)

        # ==========================================
        # TELA 2: FECHAMENTO DAS UTs
        # ==========================================
        elif st.session_state.pagina == 'fechamento_uts':
            st.title("📍 Fechamento por Unidade")
            
            uts = sorted(df[c_ut].unique())
            if 'ut_selecionada' not in st.session_state: st.session_state.ut_selecionada = "TODAS"

            # Botões das UTs
            col_btns = st.columns(len(uts) + 1)
            with col_btns[0]:
                if st.button("🌎 TODAS"): st.session_state.ut_selecionada = "TODAS"
            for i, ut in enumerate(uts):
                qtd_ut = len(df[df[c_ut] == ut])
                with col_btns[i+1]:
                    if st.button(f"{ut}\n{qtd_ut}"): st.session_state.ut_selecionada = ut

            st.markdown("---")

            # --- CORREÇÃO 3: GRÁFICO MISTO COM BARRA E LINHA DE PORCENTAGEM ---
            if st.session_state.ut_selecionada == "TODAS":
                c_left, c_right = st.columns(2)
                
                with c_left:
                    st.subheader("Acumulado por Unidade")
                    df_ut_sum = df.groupby(c_ut).size().reset_index(name="Qtd").sort_values("Qtd", ascending=False)
                    total_geral = df_ut_sum["Qtd"].sum()
                    df_ut_sum["Porcentagem"] = (df_ut_sum["Qtd"] / total_geral * 100).round(1)

                    # Criação do gráfico misto usando go.Figure
                    fig_ut_misto = go.Figure()

                    # Trace 0: Barras (Quantidade)
                    fig_ut_misto.add_trace(go.Bar(
                        x=df_ut_sum[c_ut], 
                        y=df_ut_sum["Qtd"], 
                        name="Quantidade",
                        text=df_ut_sum["Qtd"], 
                        textposition='outside', 
                        marker_color="#004a2f"
                    ))

                    # Trace 1: Linha (Porcentagem)
                    fig_ut_misto.add_trace(go.Scatter(
                        x=df_ut_sum[c_ut], 
                        y=df_ut_sum["Porcentagem"], 
                        name="Porcentagem",
                        mode='lines+markers+text',
                        text=df_ut_sum["Porcentagem"].astype(str) + '%',
                        textposition='top center',
                        line=dict(color="#78be20", width=3),
                        marker=dict(size=10),
                        yaxis="y2" # Usa o segundo eixo Y
                    ))

                    # Configuração do Layout (dois eixos Y)
                    fig_ut_misto.update_layout(
                        height=500,
                        plot_bgcolor='rgba(0,0,0,0)',
                        yaxis=dict(title="Quantidade (Alertas)"),
                        yaxis2=dict(
                            title="Porcentagem (%)",
                            overlaying='y',
                            side='right',
                            showgrid=False,
                            range=[0, df_ut_sum["Porcentagem"].max() * 1.2] # Espaço extra no topo
                        ),
                        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
                    )
                    st.plotly_chart(fig_ut_misto, use_container_width=True)
                
                with c_right:
                    # Ranking Geral Mantido
                    resumo = df.groupby(c_tipo).size().reset_index(name="Qtd").sort_values("Qtd", ascending=True).tail(10)
                    fig_rank = go.Figure(go.Bar(y=resumo[c_tipo], x=resumo["Qtd"], orientation='h', text=resumo["Qtd"],
                                           textposition='inside', marker_color="#8ebf42"))
                    fig_rank.update_layout(title="Ranking de Alertas - Geral", height=550, plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_rank, use_container_width=True)
            
            else:
                # Visualização de UT individual (mantida conforme Código 2 original)
                df_filtrado = df[df[c_ut] == st.session_state.ut_selecionada]
                resumo = df_filtrado.groupby(c_tipo).size().reset_index(name="Qtd").sort_values("Qtd", ascending=True).tail(10)
                fig = go.Figure(go.Bar(y=resumo[c_tipo], x=resumo["Qtd"], orientation='h', text=resumo["Qtd"],
                                       textposition='inside', marker_color="#8ebf42"))
                fig.update_layout(title=f"Ranking de Alertas - {st.session_state.ut_selecionada}", height=550, plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
else:
    st.info("Aguardando upload da planilha...")
