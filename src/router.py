import re
import uuid
from typing import List
from src.schema import QueryAnalysis
from src.obs import log_event


def analyze_and_route(query: str, run_id: str = None, query_id: str = "q_0000") -> QueryAnalysis:
    """
    Roteador do Adaptive RAG que decide para onde buscar baseado no TIPO DE EVIDÊNCIA.
    Evita decidir apenas por palavras isoladas, diferenciando:
    - Normativa: Leis, editais, regras, comitês de ética, resoluções
    - Estruturada: Autores, afiliações, financiamentos, artigos específicos
    - Conversacional: Pareceres de revisão, decisões de pareceristas, notas confidenciais
    - Agregada: Métricas de citações, rankings de tópicos, tendências globais
    - Cross-Source: Perguntas compostas que exigem cruzar bases
    """
    q_lower = query.lower()
    target_bases: List[str] = []
    requires_cross_source = False
    intent = "busca_informacao"
    extracted_filters = {}

    # Extração simples de filtros temporais (anos de 2010 a 2026)
    anos = re.findall(r"\b(20[12][0-9])\b", query)
    if anos:
        extracted_filters["ano"] = anos[0]

    # Regras heurísticas de classificação por tipo de evidência
    is_normativa = any(w in q_lower for w in ["edital", "editais", "chamada", "resolução", "resolucao", "cns", "conep", "cep", "comitê de ética", "comite de etica", "dispensa", "tcle", "artigo 1", "elegibilidade", "submeter ao cep"])
    is_conversacional = any(w in q_lower for w in ["parecer", "pareceres", "parecerista", "revisor", "revisores", "revisão por pares", "revisao por pares", "peer review", "protocolo cep", "nota confidencial", "decisão editorial", "rejeição do protocolo"])
    is_agregada = any(w in q_lower for w in ["mais citado", "mais citados", "total de citações", "citacoes", "métrica", "metricas", "indicadores", "tópicos", "topicos", "ranking", "tendência", "subfield", "linha de", "enquadram", "enquadramento", "alinhad"])
    is_estruturada = any(w in q_lower for w in ["artigo", "artigos", "trabalho", "trabalhos", "publicado", "publicados", "publicação", "publicações", "publicacao", "publicacoes", "projeto", "projetos", "autor", "autores", "instituição", "instituicoes", "financiamento", "financiado", "grants", "faperj", "cnpq", "doi", "produção", "producao"])

    # 1. Detecção de Cross-Source
    if (is_normativa and is_estruturada) or (is_estruturada and is_agregada and any(k in q_lower for k in ["linha de", "enquadram", "produziram", "virou produção", "alinhad", "financiamento externo", "nos últimos"])) or ("virou produção" in q_lower):
        requires_cross_source = True
        intent = "consulta_cross_source"
        if is_normativa:
            target_bases.append("editais_normativo")
        target_bases.append("producao_estruturada")
        if is_agregada or "alinhad" in q_lower or "linha de" in q_lower:
            target_bases.append("metricas_agregada")

    # 2. Rotas Simples Específicas
    elif is_conversacional:
        target_bases.append("pareceres_conversacional")
        intent = "consulta_pareceres_peer_review"

    elif is_normativa:
        target_bases.append("editais_normativo")
        intent = "consulta_normativa_editais"

    elif is_agregada:
        target_bases.append("metricas_agregada")
        intent = "consulta_metricas_bibliometricas"

    elif is_estruturada:
        target_bases.append("producao_estruturada")
        intent = "consulta_metadados_publicacoes"

    else:
        # Fallback para busca geral
        target_bases = ["editais_normativo", "producao_estruturada", "metricas_agregada"]
        intent = "busca_aberta"

    # Remove duplicatas mantendo ordem
    target_bases = list(dict.fromkeys(target_bases))

    analysis = QueryAnalysis(
        query_id=query_id,
        original_query=query,
        intent=intent,
        extracted_filters=extracted_filters,
        target_bases=target_bases,
        requires_cross_source=requires_cross_source
    )

    if run_id:
        log_event(
            run_id=run_id,
            stage="roteamento",
            query_id=query_id,
            input_data=query,
            output_data=f"Bases: {target_bases} | Cross: {requires_cross_source} | Intent: {intent}",
            extra={"extracted_filters": extracted_filters, "target_bases": target_bases}
        )

    return analysis
