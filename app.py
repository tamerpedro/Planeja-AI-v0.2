import streamlit as st
from openai import OpenAI
from pathlib import Path


st.set_page_config(
    page_title="Planeja IA - DOD v0.2",
    page_icon="📄",
    layout="wide",
)

st.title("Planeja IA - Gerador inicial de DOD")
st.caption("Protótipo v0.2 simplificado: contexto do repositório + prompt do usuário + OpenAI API.")


def carregar_contexto() -> str:
    caminho_contexto = Path("contexto.md")

    if not caminho_contexto.exists():
        return ""

    return caminho_contexto.read_text(encoding="utf-8")


def obter_cliente_openai() -> OpenAI:
    api_key = st.secrets.get("OPENAI_API_KEY")

    if not api_key:
        st.error("OPENAI_API_KEY não configurada nos Secrets do Streamlit Cloud.")
        st.stop()

    return OpenAI(api_key=api_key)


contexto = carregar_contexto()

with st.expander("Ver contexto carregado do repositório"):
    st.markdown(contexto if contexto else "Nenhum contexto encontrado.")

prompt_usuario = st.text_area(
    "Informe a demanda ou solicite a geração do DOD:",
    height=180,
    placeholder=(
        "Exemplo: Precisamos contratar notebooks corporativos para equipes em regime híbrido, "
        "com quantidade estimada de 500 unidades, por Ata de Registro de Preços..."
    ),
)

gerar = st.button("Gerar resposta com IA", type="primary")

if gerar:
    if not prompt_usuario.strip():
        st.warning("Informe uma demanda ou pergunta antes de gerar.")
        st.stop()

    client = obter_cliente_openai()

    prompt_final = f"""
Você é um assistente especializado em apoio à elaboração de Documento de Oficialização da Demanda.

Use obrigatoriamente o contexto abaixo como referência.

CONTEXTO:
{contexto}

SOLICITAÇÃO DO USUÁRIO:
{prompt_usuario}

TAREFA:
Gere uma resposta estruturada, formal e útil para apoiar a elaboração do DOD.
Quando o usuário pedir um DOD, respeite a estrutura indicada no contexto.
Não invente normas, números de processo, valores, áreas responsáveis ou informações institucionais não fornecidas.
Quando faltar informação, use marcadores como <<preencher>>.
"""

    with st.spinner("Gerando resposta..."):
        resposta = client.responses.create(
            model=st.secrets.get("OPENAI_MODEL", "gpt-5.5"),
            input=prompt_final,
        )

    st.subheader("Resposta gerada")
    st.markdown(resposta.output_text)

    st.download_button(
        label="Baixar resposta em Markdown",
        data=resposta.output_text,
        file_name="resposta_dod.md",
        mime="text/markdown",
    )
