import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
import plotly.express as px
import plotly.figure_factory as ff
import plotly.colors
import datetime

# Configurações iniciais
st.set_page_config(page_title='Dashboard de Vendas', layout='wide')

def login(username, password):
    credentials = st.secrets["credentials"]
    return credentials.get(username) == password

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("Realize o Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Login"):
        if login(username, password):
            st.session_state["logged_in"] = True
            st.success("Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
else:
    
    # Obter as credenciais do banco de dados
    DB_USER = st.secrets["postgres"]["user"]
    DB_PASSWORD = st.secrets["postgres"]["password"]
    DB_HOST = st.secrets["postgres"]["host"]
    DB_PORT = st.secrets["postgres"]["port"]
    DB_NAME = st.secrets["postgres"]["dbname"]
    DB_SSLMODE = st.secrets["postgres"]["sslmode"]

    # Criar a string de conexão
    DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSLMODE}'

    # Criar a engine
    engine = create_engine(DATABASE_URL)

    # Carregar os dados
    @st.cache_data
    def load_data():
        query = 'SELECT * FROM vendas'
        df = pd.read_sql(query, engine)
        return df

    df = load_data()

    # Título do Dashboard
    st.title('Dashboard de Vendas de Cartão de Crédito')

    # Filtros
    st.sidebar.header('Filtros')

    # Converter colunas de data se necessário
    col_datas = ['DATA_DA_TRANSACAO', 'DATA_DO_REPASSE', 'DATA_DA_ANTECIPACAO']
    for col in col_datas:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Filtro de Data da Transação
    data_min = df['DATA_DA_TRANSACAO'].min().normalize()
    data_max = df['DATA_DA_TRANSACAO'].max().normalize()

    # Obter a data de hoje e normalizá-la
    data_hoje = pd.to_datetime('today').normalize()

    # Definir data_fim_padrao como a data mínima entre hoje e data_max
    data_fim_padrao = min(data_hoje, data_max)

    # Definir data_inicio_padrao como a data máxima entre data_fim_padrao - 6 dias e data_min
    data_inicio_padrao = max(data_fim_padrao - pd.Timedelta(days=6), data_min)

    # Data de 30 dias atrás
    data_30_dias_atras = data_hoje - pd.Timedelta(days=31)

    # Definir as datas padrão para os últimos 7 dias (ou o máximo disponível)
    data_selecionada = st.sidebar.date_input(
        'Data da Transação',
        [data_inicio_padrao.date(), data_fim_padrao.date()],
        min_value=data_min.date(),
        max_value=data_max.date()
    )

    # Se apenas uma data for selecionada, duplicamos ela
    if isinstance(data_selecionada, list) or isinstance(data_selecionada, tuple):
        if len(data_selecionada) == 1:
            data_inicio = pd.to_datetime(data_selecionada[0])
            data_fim = pd.to_datetime(data_selecionada[0])
        else:
            data_inicio = pd.to_datetime(data_selecionada[0])
            data_fim = pd.to_datetime(data_selecionada[1])
    else:
        data_inicio = pd.to_datetime(data_selecionada)
        data_fim = pd.to_datetime(data_selecionada)

    # Aplicar os filtros no DataFrame
    df_filtrado = df[
        (df['DATA_DA_TRANSACAO'] >= data_inicio) &
        (df['DATA_DA_TRANSACAO'] <= data_fim)
    ]

    #Aplicar filtro DataFrame 30 dias
    df_filtrado_30_dias = df[df['DATA_DA_TRANSACAO'] >= data_30_dias_atras]

    # Filtro de Cliente (Fantasia Subadquirido)
    clientes = df['FANTASIA_SUBADQUIRIDO'].unique()
    st.sidebar.write('Cliente')
    all_clientes = ['Todos'] + sorted(clientes)
    cliente_selecionado = st.sidebar.multiselect('Selecione o Cliente', all_clientes, default=['Todos'])

    # Filtrar o DataFrame com base no cliente selecionado
    if 'Todos' in cliente_selecionado:
        cliente_selecionado = list(clientes)
        df_cliente = df_filtrado.copy()
    else:
        df_cliente = df_filtrado[df_filtrado['FANTASIA_SUBADQUIRIDO'].isin(cliente_selecionado)]

    # Filtro de Projeto
    st.sidebar.write('Projeto')
    projetos_disponiveis = df_cliente['PROJETO_SUBADQUIRIDO'].unique()
    all_projetos = ['Todos'] + sorted(projetos_disponiveis)
    projeto_selecionado = st.sidebar.multiselect('Selecione o Projeto', all_projetos, default=['Todos'])

    # Filtrar o DataFrame com base no projeto selecionado
    if 'Todos' in projeto_selecionado:
        projeto_selecionado = projetos_disponiveis
    else:
        df_cliente = df_cliente[df_cliente['PROJETO_SUBADQUIRIDO'].isin(projeto_selecionado)]

    #Adiciona espaço no sidebar
    for _ in range(5):
        st.sidebar.write("")

    #botao de logout
    st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"logged_in": False}))

    # Cálculo dos Totalizadores
    total_valor_bruto_30_dias = df_filtrado_30_dias['VALOR_BRUTO_TRANSACIONADO'].sum()
    total_valor_bruto = df_cliente['VALOR_BRUTO_TRANSACIONADO'].sum()
    total_valor_repassado = df_cliente['VALOR_DE_REPASSE'].sum()

    # Exibir os Totalizadores no Dashboard
    st.markdown('## Resumo dos Valores')

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Total Valor Bruto Transacionado Periodo", value=f"R$ {total_valor_bruto:,.2f}")
    with col2:
        st.metric(label="Total Valor Repassado", value=f"R$ {total_valor_repassado:,.2f}")
    with col3:
        st.metric(label="Total Valor Bruto Últimos 30 Dias", value=f"R$ {total_valor_bruto_30_dias:,.2f}")

    # Análises e Visualizações
    # 1. Total Bruto Transacionado por Cliente
    st.header('Total Bruto Transacionado por Cliente')
    df_cliente_agg = df_cliente.groupby('FANTASIA_SUBADQUIRIDO')['VALOR_BRUTO_TRANSACIONADO'].sum().reset_index()
    fig1 = px.bar(df_cliente_agg, x='FANTASIA_SUBADQUIRIDO', y='VALOR_BRUTO_TRANSACIONADO', labels={
        'FANTASIA_SUBADQUIRIDO': 'Cliente',
        'VALOR_BRUTO_TRANSACIONADO': 'Valor Bruto Transacionado'
    })
    st.plotly_chart(fig1, use_container_width=True)

    # 2. Total Valor Bruto Transacionado por Bandeira
    st.header('Total Valor Bruto Transacionado por Bandeira')
    df_bandeira = df_cliente.groupby('BANDEIRA')['VALOR_BRUTO_TRANSACIONADO'].sum().reset_index()
    fig2 = px.pie(df_bandeira, names='BANDEIRA', values='VALOR_BRUTO_TRANSACIONADO')
    st.plotly_chart(fig2, use_container_width=True)

    # 3. Valor Bruto e Líquido Transacionado por Dia
    st.header('Valor Bruto e Líquido Transacionado por Dia')

    # Agrupar os dados por data
    df_valores_dia = df_cliente.groupby('DATA_DA_TRANSACAO').agg({
        'VALOR_BRUTO_TRANSACIONADO': 'sum',
        'VALOR_DE_REPASSE': 'sum'
    }).reset_index()

    # Ordenar os dados por data
    df_valores_dia = df_valores_dia.sort_values('DATA_DA_TRANSACAO')

    # Criar o gráfico
    fig_valores = px.line(df_valores_dia, x='DATA_DA_TRANSACAO', y=['VALOR_BRUTO_TRANSACIONADO', 'VALOR_DE_REPASSE'], labels={
        'value': 'Valor (R$)',
        'variable': 'Tipo de Valor',
        'DATA_DA_TRANSACAO': 'Data da Transação'
    })
    st.plotly_chart(fig_valores, use_container_width=True)

    # 4. Valor Pago vs Valor a Pagar
    st.header('Valor Pago vs Valor a Pagar')

    # Criar uma nova coluna indicando se o valor foi pago ou está a pagar
    df_cliente['STATUS_PAGAMENTO'] = df_cliente['DINHEIRO_REPASSADO'].apply(lambda x: 'Pago' if x == 'PAGO' else 'A Pagar')

    # Agrupar os dados por status de pagamento
    df_pagamento = df_cliente.groupby('STATUS_PAGAMENTO')['VALOR_DE_REPASSE'].sum().reset_index()

    # Criar o gráfico
    fig_pagamento = px.pie(df_pagamento, names='STATUS_PAGAMENTO', values='VALOR_DE_REPASSE', labels={
        'STATUS_PAGAMENTO': 'Status do Pagamento',
        'VALOR_DE_REPASSE': 'Valor de Repasse'
    })
    st.plotly_chart(fig_pagamento, use_container_width=True)

    
    #5. Processar a média do valor bruto transacionado por dia da semana
    st.header('Média do Valor Bruto Transacionado por Dia da Semana')

    # Converter a coluna de data e extrair o dia da semana
    df['DATA_DA_TRANSACAO'] = pd.to_datetime(df['DATA_DA_TRANSACAO'])
    df['DIA_DA_SEMANA'] = df['DATA_DA_TRANSACAO'].dt.day_name()

    # Lista de dias da semana na ordem desejada
    dias_ordenados = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Dicionário para armazenar as médias de cada dia da semana
    medias_por_dia = {'DIA_DA_SEMANA': [], 'VALOR_BRUTO_TRANSACIONADO': []}

    # Calcular a média do valor bruto total para cada dia da semana
    for dia in dias_ordenados:
        # Filtrar os dados para o dia específico
        df_dia = df[df['DIA_DA_SEMANA'] == dia]
        # Agrupar por data para obter o somatório das transações de cada dia específico
        df_dia_agrupado = df_dia.groupby('DATA_DA_TRANSACAO')['VALOR_BRUTO_TRANSACIONADO'].sum()
        # Calcular a média dos somatórios de cada dia específico
        media_dia = df_dia_agrupado.mean()
        # Adicionar o dia e a média calculada ao dicionário
        medias_por_dia['DIA_DA_SEMANA'].append(dia)
        medias_por_dia['VALOR_BRUTO_TRANSACIONADO'].append(media_dia)

    # Converter o dicionário para um DataFrame
    df_media_dia_semana = pd.DataFrame(medias_por_dia)

    # Formatar os valores médios para o formato de moeda
    df_media_dia_semana['VALOR_BRUTO_FORMATADO'] = df_media_dia_semana['VALOR_BRUTO_TRANSACIONADO'].apply(lambda x: f'R$ {x:,.2f}')

    # Definir cores para cada dia da semana
    cores_dias = {
        "Monday": "blue",
        "Tuesday": "green",
        "Wednesday": "orange",
        "Thursday": "purple",
        "Friday": "red",
        "Saturday": "brown",
        "Sunday": "pink"
    }

    # Criar o gráfico com Plotly
    fig_media_dia_semana = px.bar(
        df_media_dia_semana,
        x='DIA_DA_SEMANA',
        y='VALOR_BRUTO_TRANSACIONADO',
        labels={'DIA_DA_SEMANA': 'Dia da Semana', 'VALOR_BRUTO_TRANSACIONADO': 'Média do Valor Bruto (R$)'},
        title='Transacional Médio por dia de semana',
        color='DIA_DA_SEMANA',  # Adiciona a cor específica de cada dia
        color_discrete_map=cores_dias
    )

    # Adicionar rótulos individualmente com a média do valor bruto total e configurar o estilo do texto
    for i, valor_formatado in enumerate(df_media_dia_semana['VALOR_BRUTO_FORMATADO']):
        fig_media_dia_semana.data[i].text = valor_formatado
        fig_media_dia_semana.data[i].textfont = dict(
            family="Arial",
            size=13,
            color="black",
            weight="bold"
        )

    # Ajustar o tamanho do gráfico para garantir visibilidade
    fig_media_dia_semana.update_layout(
        height=600,  # Aumentando a altura para maior visibilidade
    )

    # Exibir o gráfico no Streamlit
    st.plotly_chart(fig_media_dia_semana, use_container_width=True)


    # 6. Relatório Analítico por Cliente
    st.header('Relatório Analítico por Cliente')
    cliente_detalhe = st.selectbox('Selecione um Cliente para Detalhes', sorted(df['FANTASIA_SUBADQUIRIDO'].unique()))
    df_cliente_detalhe = df[df['FANTASIA_SUBADQUIRIDO'] == cliente_detalhe]
    st.write(f"Detalhes para o cliente: {cliente_detalhe}")
    st.dataframe(df_cliente_detalhe)
