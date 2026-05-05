import streamlit as st
from openai import OpenAI
from openai import RateLimitError, AuthenticationError, BadRequestError, APIStatusError
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from importlib.metadata import version, PackageNotFoundError


st.set_page_config(
    page_title="Planeja IA - DOD v0.2",
    page_icon="📄",
    layout="wide",
)

st.title("Planeja IA - Gerador inicial de DOD")
st.caption(
    "Protótipo v0.2 simplificado: contexto do repositório + prompt do usuário + OpenAI API."
)


def carregar_contexto() -> str:
    caminho_contexto = Path("contexto.md")

    if not caminho_contexto.exists():
        return ""

    return caminho_contexto.read_text(encoding="utf-8")


def obter_secret_texto(nome: str, obrigatorio: bool = False) -> str:
    valor = st.secrets.get(nome, "")

    if valor is None:
        valor = ""

    valor = str(valor).strip()

    if obrigatorio and not valor:
        st.error(f"{nome} não configurada nos Secrets do Streamlit Cloud.")
        st.stop()

    return valor


def obter_cliente_openai() -> OpenAI:
    """
    Usa apenas a project-scoped key sk-proj-...
    Não define organization/OPENAI_ORG_ID, conforme orientação do suporte da OpenAI.
    """
    api_key = obter_secret_texto("OPENAI_API_KEY", obrigatorio=True)
    return OpenAI(api_key=api_key)


def obter_modelo() -> str:
    return obter_secret_texto("OPENAI_MODEL", obrigatorio=False) or "gpt-5.4-mini"


def obter_versao_openai_sdk() -> str:
    try:
        return version("openai")
    except PackageNotFoundError:
        return "não identificada"


def obter_timestamp_brasilia() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat()


def extrair_request_id(erro: Exception) -> str:
    request_id = getattr(erro, "request_id", None)

    if request_id:
        return str(request_id)

    response = getattr(erro, "response", None)

    if response is not None:
        try:
            return response.headers.get("x-request-id", "")
        except Exception:
            return ""

    return ""


def mostrar_erro_openai(titulo: str, erro: Exception) -> None:
    request_id = extrair_request_id(erro)
    status_code = getattr(erro, "status_code", None)
    timestamp = obter_timestamp_brasilia()
    sdk_version = obter_versao_openai_sdk()

    st.error(titulo)

    st.write(f"**Timestamp:** `{timestamp}`")
    st.write(f"**Timezone:** `America/Sao_Paulo`")
    st.write(f"**OpenAI Python SDK:** `{sdk_version}`")
    st.write("**Endpoint:** `Responses API - client.responses.create`")

    if status_code:
        st.write(f"**Status code:** `{status_code}`")

    if request_id:
        st.write(f"**x-request-id:** `{request_id}`")

    st.write("**Detalhes do erro:**")
    st.code(str(erro))

    if "billing_not_active" in str(erro) or "Your account is not active" in str(erro):
        st.warning(
            "A OpenAI API retornou billing_not_active. "
            "Como esta aplicação usa uma project-scoped key sk-proj-..., "
            "não está sendo enviado OPENAI_ORG_ID nem OpenAI-Organization. "
            "Se o erro persistir, envie ao suporte da OpenAI o x-request-id, "
            "o timestamp, a versão do SDK e o endpoint exibidos acima."
        )

    st.stop()


contexto = carregar_contexto()

with st.expander("Ver contexto carregado do repositório"):
    st.markdown(contexto if contexto else "Nenhum contexto encontrado.")

with st.expander("Diagnóstico da configuração da OpenAI"):
    modelo_configurado = obter_modelo()
    sdk_version = obter_versao_openai_sdk()

    st.write(
        "**OPENAI_API_KEY:**",
        "configurada" if st.secrets.get("OPENAI_API_KEY") else "não configurada",
    )
    st.write("**OPENAI_MODEL:**", modelo_configurado)
    st.write("**OpenAI Python SDK:**", sdk_version)
    st.write("**Endpoint:** Responses API - `client.responses.create`")
    st.write("**OPENAI_ORG_ID:** não utilizado")

    st.info(
        "A API key completa não é exibida por segurança. "
        "Esta versão não envia override de organização. "
        "Se ocorrer billing_not_active, copie o x-request-id e o timestamp exibidos no erro."
    )

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
    modelo = obter_modelo()

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
        try:
            resposta = client.responses.create(
                model=modelo,
                input=prompt_final,
                max_output_tokens=1200,
            )

            texto_resposta = resposta.output_text

        except RateLimitError as erro:
            mostrar_erro_openai(
                "Erro 429 retornado pela OpenAI API. Pode ser limite de uso, quota ou billing_not_active.",
                erro,
            )

        except AuthenticationError as erro:
            mostrar_erro_openai(
                "Erro de autenticação. Verifique a OPENAI_API_KEY nos Secrets do Streamlit.",
                erro,
            )

        except BadRequestError as erro:
            mostrar_erro_openai(
                "Requisição inválida. Verifique se o modelo configurado existe e está disponível para sua conta.",
                erro,
            )

        except APIStatusError as erro:
            mostrar_erro_openai(
                "Erro retornado pela OpenAI API.",
                erro,
            )

        except Exception as erro:
            st.error("Erro inesperado ao chamar a OpenAI API.")
            st.write(f"**Timestamp:** `{obter_timestamp_brasilia()}`")
            st.write(f"**OpenAI Python SDK:** `{obter_versao_openai_sdk()}`")
            st.code(str(erro))
            st.stop()

    st.subheader("Resposta gerada")
    st.markdown(texto_resposta)

    st.download_button(
        label="Baixar resposta em Markdown",
        data=texto_resposta,
        file_name="resposta_dod.md",
        mime="text/markdown",
    )
