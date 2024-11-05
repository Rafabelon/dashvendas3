import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv
import plotly.express as px
import plotly.figure_factory as ff
import plotly.colors
import datetime

# Configurações iniciais
st.set_page_config(page_title='Dashboard de Vendas', layout='wide')


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

# 5. Agenda Futura de Pagamento aos Clientes (Calendário)
st.header('Agenda Futura de Pagamento aos Clientes (Calendário)')

# Filtrar transações abertas ou em processamento
df_agenda = df_cliente[df_cliente['DINHEIRO_REPASSADO'].isin(['ABERTO', 'PROCESSANDO_REPASSE'])]

# Preparar os dados para o gráfico de Gantt
df_agenda_gantt = df_agenda[['FANTASIA_SUBADQUIRIDO', 'DATA_DA_TRANSACAO', 'DATA_DO_REPASSE', 'VALOR_DE_REPASSE']].copy()
df_agenda_gantt.rename(columns={
    'FANTASIA_SUBADQUIRIDO': 'Task',
    'DATA_DA_TRANSACAO': 'Start',
    'DATA_DO_REPASSE': 'Finish'
}, inplace=True)

# Criar uma coluna de descrição
df_agenda_gantt['Description'] = 'R$ ' + df_agenda_gantt['VALOR_DE_REPASSE'].round(2).astype(str)

# Verificar se há valores nulos nas datas
if df_agenda_gantt['Start'].isnull().any() or df_agenda_gantt['Finish'].isnull().any():
    st.warning('Existem registros com datas inválidas. Por favor, verifique os dados.')
    st.write('Dados com problemas:')
    st.dataframe(df_agenda_gantt[df_agenda_gantt['Start'].isnull() | df_agenda_gantt['Finish'].isnull()])
else:
    if df_agenda_gantt.empty:
        st.warning('Não há dados para exibir na Agenda de Repasse.')
    else:
        # Obter a lista de tarefas únicas e gerar as cores
        tasks = df_agenda_gantt['Task'].unique()
        num_tasks = len(tasks)

        # Gerar uma lista de cores suficiente para o número de tarefas
        colors_list = plotly.colors.qualitative.Plotly
        colors = colors_list * (num_tasks // len(colors_list) + 1)
        colors = colors[:num_tasks]

        # Criar o gráfico de Gantt
        fig_gantt = ff.create_gantt(
            df_agenda_gantt,
            index_col='Task',
            show_colorbar=True,
            group_tasks=True,
            showgrid_x=True,
            showgrid_y=True,
            title='Agenda de Repasse',
            colors=colors
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

# 6. Relatório Analítico por Cliente
st.header('Relatório Analítico por Cliente')
cliente_detalhe = st.selectbox('Selecione um Cliente para Detalhes', sorted(df['FANTASIA_SUBADQUIRIDO'].unique()))
df_cliente_detalhe = df[df['FANTASIA_SUBADQUIRIDO'] == cliente_detalhe]
st.write(f"Detalhes para o cliente: {cliente_detalhe}")
st.dataframe(df_cliente_detalhe)
