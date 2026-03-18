import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata

st.set_page_config(page_title="Dashboard de Alertas v2", layout="wide")
st.title("📊 Dashboard Unificado de Gerenciamento de Alertas")

uploaded_file = st.file_uploader("Faça upload da planilha Excel", type=["xlsx"])

def normalizar(texto):
    if pd.isna(texto): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').strip().upper()

if uploaded_file:
    try:
        # 1. Leitura do arquivo e identificação automática da aba
        excel_data = pd.ExcelFile(uploaded_file)
        aba_alerta = next((s for s in excel_data.sheet_names if s.upper() == "ALERTAS"), None)

        if not aba_alerta:
            st.error("A aba 'ALERTAS' não foi encontrada. Verifique o nome na planilha.")
            st.stop()

        df = pd.read_excel(uploaded_file, sheet_name=aba_alerta)

        # 2. Mapeamento Inteligente de Colunas
        map_real = {normalizar(col): col for col in df.columns}
        def get_col(keys):
            for k in keys:
                if normalizar(k) in map_real: return map_real[normalizar(k)]
            return None

        c_nome = get_col(["NOME", "MOTORISTA"])
        c_data = get_col(["DATA DO ALARME", "DATA"])
        c_ut = get_col(["UNIDADE", "UT"])
        c_status = get_col(["STATUS"])
        c_prazo = get_col(["FINALIZADA DENTRO DO PRAZO?", "PRAZO"])
        c_tipo = get_col(["TIPO DE ALERTA", "ALERTA"])

        # 3. Preparação da Base
        df_dash = df[[c_nome, c_data, c_ut]].copy()
        df_dash.columns = ["NOME", "DATA", "UNIDADE"]
        
        # Tratamento de colunas extras
        if c_status: df_dash["STATUS"] = df[c_status].astype(str).str.strip()
        if c_prazo: df_dash["PRAZO"] = df[c_prazo].astype(str).str.strip().str.capitalize()
        if c_tipo: df_dash["TIPO"] = df[c_tipo].astype(str).str.strip()

        df_dash["DATA"] = pd.to_datetime(df_dash["DATA"], errors="coerce")
        df_dash = df_dash.dropna(subset=["DATA", "NOME"])

        # --- BARRA LATERAL (FILTROS) ---
        st.sidebar.header("Configurações do Dashboard")
        
        # Filtro de Data
        min_d, max_d = df_dash["DATA"].min().date(), df_dash["DATA"].max().date()
        periodo = st.sidebar.date_input("Filtrar Período", [min_d, max_d])

        # Filtro Apenas UTs (limpa unidades administrativas ou afastados)
        uts_dispo = sorted([str(u) for u in df_dash["UNIDADE"].unique() if str(u).upper().startswith("UT")])
        uts_sel = st.sidebar.multiselect("Selecionar Unidades (UTs)", uts_dispo, default=uts_dispo)

        # Aplicar Filtros
        mask = df_dash["UNIDADE"].isin(uts_sel)
        if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
            mask &= (df_dash["DATA"].dt.date >= periodo[0]) & (df_dash["DATA"].dt.date <= periodo[1])
        
        df_f = df_dash.loc[mask].copy()

        if df_f.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
        else:
            # Função para formatar rótulos
            def style_fig(fig):
                fig.update_traces(textposition='outside', textangle=0, cliponaxis=False)
                return fig

            # --- LINHA 1: RANKING PRINCIPAL ---
            st.subheader("🏆 Top 15 Motoristas com mais Ocorrências")
            rank_mot = df_f.groupby("NOME").size().reset_index(name="Total").sort_values("Total", ascending=False).head(15)
            fig_mot = px.bar(rank_mot, x="Total", y="NOME", orientation='h', text_auto=True, 
                             color="Total", color_continuous_scale="Reds")
            fig_mot.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(style_fig(fig_mot), use_container_width=True)

            st.markdown("---")

            # --- LINHA 2: STATUS E PRAZO ---
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📋 Status das Tratativas")
                st_res = df_f.groupby("STATUS").size().reset_index(name="Qtd")
                fig_st = px.bar(st_res, x="STATUS", y="Qtd", color="STATUS", text_auto=True,
                                color_discrete_map={"Concluída": "#2ca02c", "Assinada": "#2ca02c", "Atrasada": "#d62728", "Em andamento": "#1f77b4"})
                st.plotly_chart(style_fig(fig_st), use_container_width=True)

            with col2:
                st.subheader("⏱️ Finalizadas Dentro do Prazo?")
                # Limpeza específica para o gráfico de prazo (apenas Sim/Não)
                df_pz = df_f[df_f["PRAZO"].isin(["Sim", "Não", "Nao"])].copy()
                df_pz["PRAZO"] = df_pz["PRAZO"].replace("Nao", "Não")
                if not df_pz.empty:
                    pz_res = df_pz.groupby("PRAZO").size().reset_index(name="Qtd")
                    fig_pz = px.bar(pz_res, x="PRAZO", y="Qtd", color="PRAZO", text_auto=True,
                                    color_discrete_map={"Sim": "#2ca02c", "Não": "#ff7f0e"})
                    st.plotly_chart(style_fig(fig_pz), use_container_width=True)
                else:
                    st.info("Dados de prazo não disponíveis para o filtro atual.")

            st.markdown("---")

            # --- LINHA 3: UNIDADES E TIPOS (VOLTARAM!) ---
            col3, col4 = st.columns(2)
            with col3:
                st.subheader("🏢 Alertas por Unidade Operacional")
                ut_res = df_f.groupby("UNIDADE").size().reset_index(name="Qtd").sort_values("Qtd", ascending=False)
                fig_ut = px.bar(ut_res, x="Qtd", y="UNIDADE", orientation='h', text_auto=True, color="UNIDADE")
                fig_ut.update_layout(showlegend=False)
                st.plotly_chart(style_fig(fig_ut), use_container_width=True)

            with col4:
                st.subheader("🚨 Tipos de Alerta Identificados")
                if "TIPO" in df_f.columns:
                    tp_res = df_f.groupby("TIPO").size().reset_index(name="Qtd").sort_values("Qtd", ascending=False).head(10)
                    fig_tp = px.bar(tp_res, x="Qtd", y="TIPO", orientation='h', text_auto=True, color_discrete_sequence=['#333'])
                    fig_tp.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(style_fig(fig_tp), use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
else:
    st.info("Aguardando o upload do arquivo Excel para gerar o dashboard.")