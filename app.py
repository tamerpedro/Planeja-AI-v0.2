import io
import json
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
from openai import APIStatusError, AuthenticationError, BadRequestError, OpenAI, RateLimitError


st.set_page_config(page_title="Planeja IA - DOD v0.3", page_icon="D", layout="wide")
st.title("Planeja IA - Minuta de DOD")
st.caption("Assistente para estruturar minutas de Documento de Oficializacao de Demanda da Dataprev.")

MOTIVOS = [
    "Termino do contrato vigente",
    "Obsolescencia da tecnologia",
    "Adequacao as boas praticas de mercado",
    "Exigencia legal ou normativa",
    "Solicitacao dos clientes",
    "Outros",
]

EIXOS = [
    "NEGOCIOS E DEMANDAS ESTRATEGICAS",
    "TECNOLOGIA",
    "SEGURANCA E PROTECAO DE DADOS",
    "GESTAO E GOVERNANCA",
    "PESSOAS",
]

DIRETRIZES_PDTIC = [
    "1. Garantir que a infraestrutura de TIC esteja alinhada as prioridades e metas estabelecidas pelo novo governo.",
    "2. Implementar solucoes tecnologicas inovadoras para atender as novas demandas.",
    "3. Aumentar a eficiencia operacional.",
    "4. Assegurar a protecao dos dados e informacoes estrategicas.",
    "5. Construir estrutura flexivel e agil para responder rapidamente aos desafios.",
    "6. Promover a inclusao digital e reduzir a exclusao digital no pais.",
]

PILARES_PDTIC = [
    "Inovacao",
    "Inteligencia Artificial",
    "Analytics",
    "Experiencia do Cliente",
    "Multinuvem Soberana",
    "Modernizacao",
    "Desenvolvimento de Software",
    "Governanca de Dados",
    "Modernizacao Continua",
    "Metodos e Melhores Praticas",
    "Tecnologias de Infraestrutura",
    "Eficiencia TI Corporativa",
    "Manutencao",
    "Data Center",
]

SERVICOS = ["Orientacao Tecnica", "Capacitacao Tecnica", "Suporte Tecnico"]

TIPOS_ANEXO = [
    "Modelo oficial de DOD",
    "Normativo interno aplicavel",
    "Legislacao aplicavel",
    "DOD anterior semelhante",
    "Especificacao tecnica previa do objeto",
    "Documento de exemplo",
    "Outro contexto de apoio",
]

ESTRUTURA_DOD = """
Documento de Oficializacao de Demanda
Participantes: Elaboracao e Aprovacao
Historico de revisoes do documento
1. IDENTIFICACAO DA AREA DEMANDANTE DA SOLUCAO
2. IDENTIFICACAO DA DEMANDA
2.1. CONTEXTO DE NEGOCIO
3. CONTEXTO DA DEMANDA
3.1. SITUACAO ATUAL
3.2. ESCOPO DA DEMANDA
3.3. MOTIVACAO DA DEMANDA
3.3.1. Assinalar motivacao
3.3.2. Riscos envolvidos caso a contratacao nao seja realizada
3.3.3. Resultados a serem alcancados
3.4. DATA PREVISTA PARA DISPONIBILIZACAO DA DEMANDA
3.5. FORNECEDOR(ES), SE HOUVER
3.6. DESCRICAO DOS OBJETOS E QUANTIDADES ENVOLVIDAS
3.6.1. Para contratos existentes
3.6.2. Para nova contratacao
3.7. SERVICOS ASSOCIADOS A DEMANDA
3.7.1. Servicos selecionados
3.7.2. Condicoes minimas obrigatorias
4. AREAS E PAPEIS ENVOLVIDOS
4.1. AREAS INTERNAS (DATAPREV)
4.2. CLIENTES EXTERNOS QUE FARAO USO DA SOLUCAO/SOFTWARE
5. INFORMACOES ADICIONAIS
6. NOTAS
7. ANEXOS
"""


def carregar_contexto() -> str:
    caminho = Path("contexto.md")
    return caminho.read_text(encoding="utf-8") if caminho.exists() else ""


def obter_secret_texto(nome: str, obrigatorio: bool = False) -> str:
    valor = str(st.secrets.get(nome, "") or "").strip()
    if obrigatorio and not valor:
        st.error(f"{nome} nao configurada nos Secrets do Streamlit Cloud.")
        st.stop()
    return valor


def obter_cliente_openai() -> OpenAI:
    return OpenAI(api_key=obter_secret_texto("OPENAI_API_KEY", obrigatorio=True))


def obter_modelo() -> str:
    return obter_secret_texto("OPENAI_MODEL") or "gpt-5.4-mini"


def obter_versao_openai_sdk() -> str:
    try:
        return version("openai")
    except PackageNotFoundError:
        return "nao identificada"


def obter_timestamp_brasilia() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat()


def mostrar_erro_openai(titulo: str, erro: Exception) -> None:
    request_id = getattr(erro, "request_id", "") or ""
    response = getattr(erro, "response", None)
    if not request_id and response is not None:
        request_id = response.headers.get("x-request-id", "")

    st.error(titulo)
    st.write(f"**Timestamp:** `{obter_timestamp_brasilia()}`")
    st.write("**Timezone:** `America/Sao_Paulo`")
    st.write(f"**OpenAI Python SDK:** `{obter_versao_openai_sdk()}`")
    st.write("**Endpoint:** `Responses API - client.responses.create`")
    if getattr(erro, "status_code", None):
        st.write(f"**Status code:** `{erro.status_code}`")
    if request_id:
        st.write(f"**x-request-id:** `{request_id}`")
    st.write("**Detalhes do erro:**")
    st.code(str(erro))
    st.stop()


def campo_texto(label: str, key: str, height: int = 110, placeholder: str = "") -> str:
    return st.text_area(label, key=key, height=height, placeholder=placeholder)


def limitar_texto(texto: str, limite: int = 12000) -> str:
    texto = texto.strip()
    if len(texto) <= limite:
        return texto
    return texto[:limite] + "\n\n[Texto truncado pelo app para preservar limite de contexto.]"


def extrair_texto_anexo(arquivo) -> str:
    nome = arquivo.name.lower()
    try:
        if nome.endswith(".pdf"):
            from pypdf import PdfReader

            leitor = PdfReader(io.BytesIO(arquivo.getvalue()))
            return "\n\n".join(p.extract_text() or "" for p in leitor.pages)

        if nome.endswith(".docx"):
            from docx import Document

            documento = Document(io.BytesIO(arquivo.getvalue()))
            paragrafos = [p.text for p in documento.paragraphs]
            tabelas = [
                " | ".join(c.text.strip() for c in linha.cells)
                for tabela in documento.tables
                for linha in tabela.rows
            ]
            return "\n".join(paragrafos + tabelas)

        return arquivo.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        return "[Arquivo binario sem extracao automatica. Descreva o conteudo no campo de observacoes.]"
    except Exception as erro:
        return f"[Nao foi possivel extrair o texto automaticamente: {erro}]"


def montar_anexos_contexto(arquivos) -> list[dict[str, str]]:
    anexos = []
    for indice, arquivo in enumerate(arquivos, start=1):
        with st.expander(f"Classificar anexo {indice}: {arquivo.name}", expanded=True):
            tipo = st.selectbox("Tipo de anexo", TIPOS_ANEXO, key=f"tipo_{indice}_{arquivo.name}")
            descricao = st.text_area(
                "Como este anexo deve orientar a minuta?",
                key=f"desc_{indice}_{arquivo.name}",
                height=90,
                placeholder="Ex.: DOD anterior para demanda semelhante; usar apenas como referencia.",
            )
            conteudo = limitar_texto(extrair_texto_anexo(arquivo))
            st.caption(f"Texto extraido: {len(conteudo)} caracteres")
        anexos.append({"arquivo": arquivo.name, "tipo": tipo, "descricao": descricao, "conteudo_extraido": conteudo})
    return anexos


def montar_prompt(dados: dict, contexto: str, anexos: list[dict[str, str]]) -> str:
    return f"""
Voce e um assistente especializado na elaboracao de minutas de Documento de Oficializacao de Demanda (DOD) para a Dataprev.

Objetivo: gerar uma minuta em texto, formal e semi estruturada, seguindo o mais fielmente possivel a estrutura do modelo oficial de DOD da Dataprev.

Ordem de prioridade dos contextos:
1. Modelo oficial de DOD da Dataprev e estrutura obrigatoria informada abaixo.
2. Normativos internos aplicaveis fornecidos no contexto ou anexos.
3. Legislacao aplicavel fornecida no contexto ou anexos.
4. DODs anteriores semelhantes, apenas como referencia de estilo, estrutura e nivel de detalhe.
5. Especificacoes tecnicas e demais anexos fornecidos pelo usuario.

Regras:
- Nao invente normas, valores, numeros de processo, areas, matriculas, fornecedores, prazos, quantitativos ou fatos nao fornecidos.
- Quando faltar informacao obrigatoria, use <<preencher>>.
- Use "Nao se aplica" somente quando os dados indicarem isso.
- Nao antecipe estrategia de contratacao, salvo se o usuario declarar expressamente.
- Remova orientacoes internas do modelo. A saida deve ser a minuta, nao instrucoes.
- Mantenha titulos e numeracao do DOD.
- Use "(X)" nas opcoes selecionadas e "( )" nas opcoes nao selecionadas.

Estrutura oficial:
{ESTRUTURA_DOD}

Contexto do repositorio:
{contexto or "Nenhum contexto adicional no repositorio."}

Dados estruturados:
{json.dumps(dados, ensure_ascii=False, indent=2)}

Anexos:
{json.dumps(anexos, ensure_ascii=False, indent=2)}

Saida esperada: gere apenas a minuta do DOD em Markdown, com tabelas quando fizer sentido.
"""


with st.sidebar:
    contexto_repo = carregar_contexto()
    st.header("Configuracao")
    st.write("**OPENAI_API_KEY:**", "configurada" if st.secrets.get("OPENAI_API_KEY") else "nao configurada")
    st.write("**OPENAI_MODEL:**", obter_modelo())
    st.write("**OpenAI Python SDK:**", obter_versao_openai_sdk())
    st.write("**OPENAI_ORG_ID:** nao utilizado")
    with st.expander("Contexto do repositorio"):
        st.markdown(contexto_repo or "Nenhum contexto encontrado.")

st.subheader("1. Identificacao")
c1, c2 = st.columns(2)
with c1:
    titulo_dod = st.text_input("Titulo do DOD")
    identificador = st.text_input("Identificador interno (opcional)")
    unidade_demandante = st.text_area("Unidade demandante", height=90, placeholder="Diretoria / Superintendencia / Departamento / Divisao / Setor")
    responsavel_demanda = st.text_input("Responsavel pela Unidade Demandante")
    matricula_responsavel = st.text_input("Matricula do responsavel")
with c2:
    elaboradores = st.text_area("Elaboracao: nomes, lotacoes e matriculas", height=120)
    aprovadores = st.text_area("Aprovacao: nome, cargo/area e matricula", height=120)
    pontos_focais = st.text_area("Pontos focais", height=100, placeholder="Nome completo, lotacao, cargo e matricula")

st.subheader("2. Identificacao da demanda")
c1, c2 = st.columns(2)
with c1:
    nome_projeto = st.text_input("Nome do projeto")
    eixos = st.multiselect("Eixos e objetivos estrategicos", EIXOS)
    diretrizes = st.multiselect("Diretrizes do PDTIC", DIRETRIZES_PDTIC)
with c2:
    pilares = st.multiselect("Pilares tecnologicos do PDTIC", PILARES_PDTIC)
    contexto_negocio = campo_texto("2.1 Contexto de negocio", "contexto_negocio", placeholder="Circunstancias, fatos de origem e beneficios esperados.")

st.subheader("3. Contexto da demanda")
situacao_atual = campo_texto("3.1 Situacao atual", "situacao_atual", placeholder="Como a necessidade e atendida hoje.")
escopo_demanda = campo_texto("3.2 Escopo da demanda", "escopo_demanda", 140, "Necessidades funcionais, limitacoes, clientes e ambiente de uso.")

c1, c2 = st.columns(2)
with c1:
    motivacoes = st.multiselect("3.3.1 Motivacao da demanda", MOTIVOS)
    motivacao_outros = st.text_input("Se marcou 'Outros', cite quais")
    riscos = campo_texto("3.3.2 Riscos se a contratacao nao for realizada", "riscos")
    resultados = campo_texto("3.3.3 Resultados a serem alcancados", "resultados")
with c2:
    data_disponibilizacao = st.text_input("3.4 Data prevista para disponibilizacao", placeholder="Ex.: A partir de dd/mm/aaaa, em virtude de...")
    fornecedores = campo_texto("3.5 Fornecedor(es), se houver", "fornecedores", placeholder="Fornecedor, contato, e-mail e telefone.")

st.subheader("3.6 Objetos e quantidades")
tipo_contratacao = st.radio("Tipo de demanda para dimensionamento", ["Nova contratacao", "Contrato existente", "Ainda nao definido"], horizontal=True)
objetos_quantidades = campo_texto("Descricao dos objetos e quantidades envolvidas", "objetos_quantidades", 130, "Itens, quantidades, acessos, usuarios, volume ou memoria de calculo.")
justificativa_quantidades = campo_texto("Justificativa das quantidades ou dados de dimensionamento", "justificativa_quantidades")

st.subheader("3.7 Servicos associados")
servicos = st.multiselect("Servicos que devem ser contemplados", SERVICOS)
c1, c2, c3 = st.columns(3)
with c1:
    orientacao_tecnica = campo_texto("Orientacao Tecnica", "orientacao_tecnica", placeholder="Horas e justificativa.")
with c2:
    capacitacao_tecnica = campo_texto("Capacitacao Tecnica", "capacitacao_tecnica", placeholder="Treinandos, areas e justificativa.")
with c3:
    suporte_tecnico = campo_texto("Suporte Tecnico", "suporte_tecnico", placeholder="Modalidade 24x7 ou 8x5 e justificativa.")

st.subheader("4. Areas e papeis envolvidos")
matriz_responsabilidades = st.text_area(
    "4.1 Areas internas e matriz de responsabilidades",
    height=150,
    placeholder="Gestor do Produto/Servico/Solucao: ...\nGestor Tecnico do Contrato: ...\nUsuarios: ...\nInstalacao, Operacao e Sustentacao: ...",
)
clientes_externos = campo_texto("4.2 Clientes externos beneficiados ou usuarios da solucao", "clientes_externos")

st.subheader("5. Informacoes adicionais, notas e anexos")
informacoes_adicionais = campo_texto("5. Informacoes adicionais", "informacoes_adicionais")
notas = campo_texto("6. Notas explicativas ou referencias", "notas")
arquivos = st.file_uploader("7. Anexos de contexto", accept_multiple_files=True, type=["pdf", "txt", "md", "csv", "json", "docx"])
anexos_contexto = montar_anexos_contexto(arquivos)

dados_dod = {
    "titulo_dod": titulo_dod,
    "identificador": identificador,
    "unidade_demandante": unidade_demandante,
    "responsavel_demanda": responsavel_demanda,
    "matricula_responsavel": matricula_responsavel,
    "elaboradores": elaboradores,
    "aprovadores": aprovadores,
    "pontos_focais": pontos_focais,
    "nome_projeto": nome_projeto,
    "eixos_estrategicos": eixos,
    "diretrizes_pdtic": diretrizes,
    "pilares_pdtic": pilares,
    "contexto_negocio": contexto_negocio,
    "situacao_atual": situacao_atual,
    "escopo_demanda": escopo_demanda,
    "motivacoes": motivacoes,
    "motivacao_outros": motivacao_outros,
    "riscos": riscos,
    "resultados": resultados,
    "data_disponibilizacao": data_disponibilizacao,
    "fornecedores": fornecedores,
    "tipo_contratacao": tipo_contratacao,
    "objetos_quantidades": objetos_quantidades,
    "justificativa_quantidades": justificativa_quantidades,
    "servicos_associados": servicos,
    "orientacao_tecnica": orientacao_tecnica,
    "capacitacao_tecnica": capacitacao_tecnica,
    "suporte_tecnico": suporte_tecnico,
    "matriz_responsabilidades": matriz_responsabilidades,
    "clientes_externos": clientes_externos,
    "informacoes_adicionais": informacoes_adicionais,
    "notas": notas,
}

campos_minimos = {
    "Titulo do DOD": titulo_dod,
    "Unidade demandante": unidade_demandante,
    "Responsavel pela demanda": responsavel_demanda,
    "Nome do projeto": nome_projeto,
    "Contexto de negocio": contexto_negocio,
    "Situacao atual": situacao_atual,
    "Escopo da demanda": escopo_demanda,
    "Motivacao da demanda": ", ".join(motivacoes),
    "Riscos": riscos,
    "Resultados": resultados,
    "Objetos e quantidades": objetos_quantidades,
}
pendentes = [nome for nome, valor in campos_minimos.items() if not str(valor).strip()]
if pendentes:
    with st.expander("Campos recomendados ainda nao preenchidos"):
        st.write("\n".join(f"- {campo}" for campo in pendentes))

if st.button("Gerar minuta de DOD", type="primary"):
    if not any(str(valor).strip() for valor in dados_dod.values()):
        st.warning("Preencha ao menos os dados principais da demanda antes de gerar a minuta.")
        st.stop()

    with st.spinner("Gerando minuta..."):
        try:
            resposta = obter_cliente_openai().responses.create(
                model=obter_modelo(),
                input=montar_prompt(dados_dod, contexto_repo, anexos_contexto),
                max_output_tokens=5000,
            )
            texto_resposta = resposta.output_text
        except RateLimitError as erro:
            mostrar_erro_openai("Erro 429 retornado pela OpenAI API. Pode ser limite de uso, quota ou billing_not_active.", erro)
        except AuthenticationError as erro:
            mostrar_erro_openai("Erro de autenticacao. Verifique a OPENAI_API_KEY nos Secrets do Streamlit.", erro)
        except BadRequestError as erro:
            mostrar_erro_openai("Requisicao invalida. Verifique se o modelo configurado existe e esta disponivel para sua conta.", erro)
        except APIStatusError as erro:
            mostrar_erro_openai("Erro retornado pela OpenAI API.", erro)
        except Exception as erro:
            st.error("Erro inesperado ao chamar a OpenAI API.")
            st.write(f"**Timestamp:** `{obter_timestamp_brasilia()}`")
            st.write(f"**OpenAI Python SDK:** `{obter_versao_openai_sdk()}`")
            st.code(str(erro))
            st.stop()

    st.subheader("Minuta gerada")
    st.markdown(texto_resposta)
    st.download_button("Baixar minuta em Markdown", data=texto_resposta, file_name="minuta_dod.md", mime="text/markdown")
