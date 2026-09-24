import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

st.set_page_config(page_title="Petrol Transportes", layout="wide", page_icon="🚛")

COLUNAS_PROGRAMACOES = [
    "usuario_lancamento",
    "data_programacao",
    "numero_pedido",
    "cliente",
    "rota",
    "motorista",
    "placa",
    "tipo_produto",
    "valor_frete",
    "valor_diaria",
    "status",
    "observacoes",
]

COLUNAS_PRECOS = [
    "origem",
    "destino",
    "produto",
    "valor_litro",
    "observacao",
    "data_atualizacao",
    "atualizado_por",
    "chave_rota",
]


@st.cache_resource
def init_supabase() -> Client | None:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        return None

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


supabase = init_supabase()


def get_programacoes_df() -> pd.DataFrame:
    if supabase is not None:
        try:
            res = supabase.table("programacoes").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                return df
        except Exception:
            st.warning("Não foi possível carregar os dados do Supabase. Usando modo de demonstração.")

    demo_data = st.session_state.get("programacoes_demo", [])
    if demo_data:
        return pd.DataFrame(demo_data)

    return pd.DataFrame(columns=COLUNAS_PROGRAMACOES)


def salvar_programacao(dados: dict) -> bool:
    if supabase is not None:
        try:
            supabase.table("programacoes").insert(dados).execute()
            return True
        except Exception as exc:
            st.error(f"Erro ao salvar no Supabase: {exc}")
            return False

    demo_data = st.session_state.get("programacoes_demo", [])
    demo_data.append(dados)
    st.session_state["programacoes_demo"] = demo_data
    return True


def get_precos_df() -> pd.DataFrame:
    if supabase is not None:
        try:
            res = supabase.table("precos_rotas").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                return df
        except Exception:
            st.warning("Não foi possível carregar a tabela de preços do Supabase. Usando modo de demonstração.")

    demo_data = st.session_state.get("precos_demo")
    if demo_data is None:
        demo_data = [
            {
                "origem": "Baguaçu",
                "destino": "Stock (GASOIL)",
                "produto": "Gás S10",
                "valor_litro": 0.40,
                "observacao": "Atualizado 11/09",
                "data_atualizacao": "2026-09-11",
                "atualizado_por": "Operador",
                "chave_rota": "Baguaçu x Stock (GASOIL)"
            },
            {
                "origem": "Santos",
                "destino": "Stock (GASOIL)",
                "produto": "Etanol",
                "valor_litro": 0.15,
                "observacao": "Em revisão",
                "data_atualizacao": "2026-09-12",
                "atualizado_por": "Operador",
                "chave_rota": "Santos x Stock (GASOIL)"
            }
        ]
        st.session_state["precos_demo"] = demo_data

    return pd.DataFrame(demo_data)


def salvar_preco(dados: dict) -> bool:
    if supabase is not None:
        try:
            supabase.table("precos_rotas").insert(dados).execute()
            return True
        except Exception as exc:
            st.error(f"Erro ao salvar preço no Supabase: {exc}")
            return False

    demo_data = st.session_state.get("precos_demo", [])
    demo_data.append(dados)
    st.session_state["precos_demo"] = demo_data
    return True


st.sidebar.title("🚛 Petrol Transportes")
if supabase is None:
    st.sidebar.caption("Modo: demonstração / sem conexão com backend")
else:
    st.sidebar.caption("Modo: conectado ao Supabase")

usuario_atual = st.sidebar.text_input("Seu Nome / Usuário", value="Operador")

menu = st.sidebar.radio("Navegação", [
    "📝 Lançar Pedidos",
    "📊 Programação & Relatórios",
    "💰 Faturamento & Projeções",
    "� Tabela de Preços",
    "�🚛 Frota & Motoristas"
])

if supabase is None:
    st.info("Aguardando configuração das chaves do Supabase. Enquanto isso, o sistema está em modo de demonstração para carregar as telas e testar o fluxo.")

# --- TELA 1: LANÇAR PEDIDOS ---
if menu == "📝 Lançar Pedidos":
    st.title("📝 Lançamento de Pedidos")
    st.caption(f"Registrando como: **{usuario_atual}**")

    with st.form("form_pedido", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            data_prog = st.date_input("Data da Programação", datetime.date.today())
            no_pedido = st.text_input("Nº do Pedido / Carga")
            cliente = st.text_input("Cliente")
        with col2:
            rota = st.text_input("Rota (Origem x Destino)")
            motorista = st.text_input("Nome do Motorista")
            placa = st.text_input("Placa / Conjunto")
        with col3:
            tipo_produto = st.selectbox("Tipo de Produto", ["Combustível", "Etanol", "Diesel", "Gasolina", "Outros"])
            valor_frete = st.number_input("Valor do Frete / Faturamento (R$)", min_value=0.0, step=100.0)
            valor_diaria = st.number_input("Valor da Diária (R$)", min_value=0.0, step=50.0)

        status = st.selectbox("Status", ["Programado", "Em Trânsito", "Concluído", "Cancelado"])
        obs = st.text_area("Observações")

        btn_salvar = st.form_submit_button("💾 Salvar Pedido")

        if btn_salvar:
            if not no_pedido or not motorista or not placa:
                st.warning("Preencha ao menos Pedido, Motorista e Placa!")
            else:
                novo_dado = {
                    "usuario_lancamento": usuario_atual,
                    "data_programacao": str(data_prog),
                    "numero_pedido": no_pedido,
                    "cliente": cliente,
                    "rota": rota,
                    "motorista": motorista,
                    "placa": placa,
                    "tipo_produto": tipo_produto,
                    "valor_frete": valor_frete,
                    "valor_diaria": valor_diaria,
                    "status": status,
                    "observacoes": obs
                }

                salvo = salvar_programacao(novo_dado)
                if salvo:
                    st.success("✅ Pedido registrado com sucesso!")

# --- TELA 2: PROGRAMAÇÃO & RELATÓRIOS ---
elif menu == "📊 Programação & Relatórios":
    st.title("📊 Programação e Filtros de Cargas")

    df = get_programacoes_df()
    if not df.empty:
        st.subheader("🔍 Filtros de Busca")
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)

        with f_col1:
            motoristas = ["Todos"] + list(df["motorista"].dropna().unique())
            f_motorista = st.selectbox("Motorista", motoristas)
        with f_col2:
            placas = ["Todas"] + list(df["placa"].dropna().unique())
            f_placa = st.selectbox("Placa", placas)
        with f_col3:
            rotas = ["Todas"] + list(df["rota"].dropna().unique())
            f_rota = st.selectbox("Rota", rotas)
        with f_col4:
            produtos = ["Todos"] + list(df["tipo_produto"].dropna().unique())
            f_produto = st.selectbox("Tipo de Produto", produtos)

        df_filtrado = df.copy()
        if f_motorista != "Todos":
            df_filtrado = df_filtrado[df_filtrado["motorista"] == f_motorista]
        if f_placa != "Todas":
            df_filtrado = df_filtrado[df_filtrado["placa"] == f_placa]
        if f_rota != "Todas":
            df_filtrado = df_filtrado[df_filtrado["rota"] == f_rota]
        if f_produto != "Todos":
            df_filtrado = df_filtrado[df_filtrado["tipo_produto"] == f_produto]

        st.markdown("---")
        st.subheader("📋 Resumo das Programações")

        colunas_visiveis = [
            "data_programacao", "numero_pedido", "cliente", "rota",
            "motorista", "placa", "tipo_produto", "valor_frete",
            "status", "usuario_lancamento"
        ]
        st.dataframe(df_filtrado[colunas_visiveis], use_container_width=True)

        csv = df_filtrado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar Relatório (Excel / CSV)",
            data=csv,
            file_name=f"relatorio_programacao_{datetime.date.today()}.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhum pedido cadastrado ainda.")

# --- TELA 3: FATURAMENTO & PROJEÇÕES ---
elif menu == "💰 Faturamento & Projeções":
    st.title("💰 Projeção de Faturamento")

    df = get_programacoes_df()
    if not df.empty:
        df = df.copy()
        df["data_programacao"] = pd.to_datetime(df["data_programacao"], errors="coerce")
        df = df.dropna(subset=["data_programacao"]).copy()
        df["valor_frete"] = pd.to_numeric(df["valor_frete"], errors="coerce").fillna(0)

        hoje = pd.Timestamp(datetime.date.today())
        inicio_semana = hoje - pd.Timedelta(days=hoje.dayofweek)
        inicio_mes = hoje.replace(day=1)

        fat_dia = df[df["data_programacao"].dt.date == hoje.date()]["valor_frete"].sum()
        fat_semana = df[df["data_programacao"] >= inicio_semana]["valor_frete"].sum()
        fat_mes = df[df["data_programacao"] >= inicio_mes]["valor_frete"].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento de Hoje", f"R$ {fat_dia:,.2f}")
        m2.metric("Projeção / Semana", f"R$ {fat_semana:,.2f}")
        m3.metric("Projeção / Mês", f"R$ {fat_mes:,.2f}")

        st.markdown("---")
        st.subheader("📈 Faturamento por Período")
        fat_diario = df.groupby(df["data_programacao"].dt.date)["valor_frete"].sum().reset_index()
        fat_diario.columns = ["data_programacao", "valor_frete"]
        st.line_chart(fat_diario.set_index("data_programacao"))
    else:
        st.info("Sem dados financeiros para exibir.")

# --- TELA 4: TABELA DE PREÇOS POR ROTA ---
elif menu == "💵 Tabela de Preços":
    st.title("💵 Tabela de Rotas e Frete por Litro")
    st.caption("Controle dos valores por rota, produto, data da última atualização e quem alterou.")

    df_precos = get_precos_df()

    with st.form("form_preco_rota", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            origem = st.text_input("Origem")
            destino = st.text_input("Destino")
            produto = st.selectbox("Produto", ["Gás S10", "Etanol", "Diesel", "Gasolina", "Outros"])

        with col2:
            valor_litro = st.number_input("Valor por Litro (R$/L)", min_value=0.0, step=0.01, format="%.3f")
            data_atualizacao = st.date_input("Data da última atualização", datetime.date.today())
            atualizado_por = st.text_input("Atualizado por")

        with col3:
            observacao = st.text_area("Observação")

        if st.form_submit_button("💾 Salvar preço da rota"):
            if not origem or not destino or not atualizado_por:
                st.warning("Preencha origem, destino e quem atualizou o preço.")
            else:
                registro = {
                    "origem": origem,
                    "destino": destino,
                    "produto": produto,
                    "valor_litro": valor_litro,
                    "observacao": observacao,
                    "data_atualizacao": str(data_atualizacao),
                    "atualizado_por": atualizado_por,
                    "chave_rota": f"{origem} x {destino}"
                }
                if salvar_preco(registro):
                    st.success("✅ Preço da rota salvo com sucesso!")

    st.markdown("---")
    st.subheader("📋 Tabela atual de preços")

    if not df_precos.empty:
        df_precos = df_precos[COLUNAS_PRECOS].copy()
        df_precos["valor_litro"] = df_precos["valor_litro"].apply(lambda x: f"R$ {float(x):,.3f}" if pd.notna(x) else "R$ 0,000")
        st.dataframe(df_precos, use_container_width=True)
    else:
        st.info("Nenhuma rota cadastrada com preço.")

# --- TELA 5: FROTA & MOTORISTAS ---
elif menu == "🚛 Frota & Motoristas":
    st.title("🚛 Consulta de Motoristas e Conjuntos")

    df_frota = get_programacoes_df()[["motorista", "placa"]].drop_duplicates().copy()
    df_frota = df_frota.dropna(subset=["motorista", "placa"])

    if not df_frota.empty:
        busca = st.text_input("🔍 Buscar Motorista ou Placa")

        if busca:
            df_frota = df_frota[
                df_frota["motorista"].str.contains(busca, case=False, na=False) |
                df_frota["placa"].str.contains(busca, case=False, na=False)
            ]
        st.table(df_frota)
    else:
        st.info("Nenhum motorista ou veículo localizado.")