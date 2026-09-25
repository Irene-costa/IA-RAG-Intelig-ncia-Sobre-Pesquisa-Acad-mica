import json
from pathlib import Path
from typing import List
from src.schema import DocumentChunk, ChunkMetadata, BaseNatureza, SensitivityLevel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "v1"
CHUNKS_FILE = DATA_DIR / "chunks_v1.json"


def chunk_text_by_paragraphs(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """Divide texto por quebras de parÃ¡grafos/artigos mantendo overlap."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = []
    current_len = 0

    for p in paragraphs:
        p_len = len(p)
        if current_len + p_len > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [current_chunk[-1]] if overlap > 0 else []
            current_len = len(current_chunk[0]) if current_chunk else 0

        current_chunk.append(p)
        current_len += p_len

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks if chunks else [text]


import pypdf

def ingest_editais_normativo() -> List[DocumentChunk]:
    """Processa documentos normativos e editais (TXT e PDF)."""
    chunks = []
    base_dir = RAW_DIR / "editais_normativo"
    if not base_dir.exists():
        return chunks

    for file_path in base_dir.glob("*.*"):
        if file_path.suffix.lower() == ".pdf":
            try:
                reader = pypdf.PdfReader(file_path)
                pages_text = [page.extract_text() for page in reader.pages if page.extract_text()]
                content = "\n\n".join(pages_text)
            except Exception as e:
                print(f"[!] Erro ao ler PDF {file_path.name}: {e}")
                continue
        else:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

        if not content.strip():
            continue

        sub_chunks = chunk_text_by_paragraphs(content, chunk_size=600, overlap=100)

        for idx, text in enumerate(sub_chunks):
            chunk_id = f"norm_{file_path.stem}_{idx:03d}"
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                doc_type=file_path.suffix.replace(".", "") or "txt",
                source_file=str(file_path.relative_to(DATA_DIR)),
                base_id="editais_normativo",
                natureza=BaseNatureza.NORMATIVA,
                sensitivity=SensitivityLevel.PUBLICO,
                campo_vigencia="2016-presente",
                extras={
                    "filename": file_path.name,
                    "orgao": "CNS/CONEP" if "cns" in file_path.name.lower() else "FAPERJ",
                    "chunk_index": idx
                }
            )
            chunks.append(DocumentChunk(chunk_id=chunk_id, content=text, metadata=metadata))

    return chunks


def ingest_producao_estruturada() -> List[DocumentChunk]:
    """Processa metadados estruturados de artigos do OpenAlex e corpus sintético."""
    chunks = []
    base_dir = RAW_DIR / "producao_estruturada"
    if not base_dir.exists():
        return chunks

    for file_path in base_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] Erro ao ler JSON {file_path.name}: {e}")
            continue

        if isinstance(data, dict) and "results" in data:
            results = data["results"]
        elif isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            results = [data]
        else:
            results = []

        origem = "sintetico" if "sintetico" in file_path.name else "openalex"

        for idx, item in enumerate(results):
            if not isinstance(item, dict):
                continue
            work_id = str(item.get("id", f"work_{file_path.stem}_{idx}")).split("/")[-1]
            title = item.get("title") or "Sem título"
            pub_year = item.get("publication_year")
            cited_by = item.get("cited_by_count", 0)
            doi = item.get("doi", "")

            authors_list = []
            institutions_list = []

            for authorship in item.get("authorships", []):
                if isinstance(authorship, dict):
                    author_name = authorship.get("author", {}).get("display_name")
                    if author_name:
                        authors_list.append(author_name)

                    for inst in authorship.get("institutions", []):
                        if isinstance(inst, dict):
                            inst_name = inst.get("display_name")
                            if inst_name and inst_name not in institutions_list:
                                institutions_list.append(inst_name)

            grants_list = []
            for grant in item.get("grants", []):
                if isinstance(grant, dict):
                    funder = grant.get("funder_display_name")
                    award = grant.get("award_id")
                    if funder:
                        grants_list.append(f"{funder} (Auxílio: {award})" if award else funder)

            if not grants_list:
                for funder in item.get("funders", []):
                    if isinstance(funder, dict):
                        funder_name = funder.get("display_name")
                        if funder_name:
                            grants_list.append(funder_name)

            abstract_idx = item.get("abstract_inverted_index")
            abstract_text = ""
            if abstract_idx and isinstance(abstract_idx, dict):
                word_pos = []
                for word, positions in abstract_idx.items():
                    if isinstance(positions, list):
                        for pos in positions:
                            word_pos.append((pos, word))
                word_pos.sort()
                abstract_text = " ".join(w for _, w in word_pos)

            content = (
                f"Título: {title}\n"
                f"Ano de Publicação: {pub_year}\n"
                f"Autores: {', '.join(authors_list[:5])}\n"
                f"Instituições: {', '.join(institutions_list[:3])}\n"
                f"Financiamento/Grants: "
                f"{', '.join(grants_list) if grants_list else 'Não declarado'}\n"
                f"Total de Citações: {cited_by}\n"
                f"DOI: {doi}\n"
                f"Resumo: {abstract_text[:600]}"
            )

            chunk_id = f"est_{work_id}"
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                doc_type="json",
                source_file=str(file_path.relative_to(DATA_DIR)),
                base_id="producao_estruturada",
                natureza=BaseNatureza.ESTRUTURADA,
                sensitivity=SensitivityLevel.PUBLICO,
                campo_vigencia=str(pub_year) if pub_year else None,
                extras={
                    "work_id": work_id,
                    "title": title,
                    "year": pub_year,
                    "cited_by_count": cited_by,
                    "authors": authors_list[:5],
                    "institutions": institutions_list[:3],
                    "has_funding": bool(grants_list),
                    "origem": origem,
                }
            )
    return chunks


def ingest_pareceres_conversacional() -> List[DocumentChunk]:
    """Processa pareceres e registros de revisão por pares."""
    chunks = []
    base_dir = RAW_DIR / "pareceres_conversacional"
    if not base_dir.exists():
        return chunks

    for file_path in base_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                pareceres = json.load(f)
        except Exception as e:
            print(f"[!] Erro ao ler JSON {file_path.name}: {e}")
            continue

        if not isinstance(pareceres, list):
            pareceres = [pareceres]

        for idx, p in enumerate(pareceres):
            if not isinstance(p, dict):
                continue
            proto_id = p.get("protocolo_id", f"proto_{file_path.stem}_{idx}")
            titulo = p.get("titulo_projeto", "")
            decisao = p.get("decisao", "")
            data_p = p.get("data_parecer", "")
            rodada = p.get("rodada", "")
            texto = p.get("parecer_texto", "")
            interno = p.get("comentario_interno_revisor", "")

            content = (
                f"Protocolo: {proto_id}\n"
                f"Projeto: {titulo}\n"
                f"Área: {p.get('area', '')}\n"
                f"Data: {data_p} ({rodada})\n"
                f"Decisão Editorial: {decisao}\n"
                f"Parecer Técnico: {texto}\n"
                f"Observação Interna: {interno}"
            )

            chunk_id = f"conv_{proto_id.replace('-', '_')}_{idx:02d}"
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                doc_type="json",
                source_file=str(file_path.relative_to(DATA_DIR)),
                base_id="pareceres_conversacional",
                natureza=BaseNatureza.CONVERSACIONAL,
                sensitivity=SensitivityLevel.INTERNO,
                campo_vigencia=data_p,
                extras={
                    "protocolo_id": proto_id,
                    "decisao": decisao,
                    "status_anonimato": p.get("status_anonimato", "duplo_cego"),
                    "rodada": rodada
                }
            )
            chunks.append(DocumentChunk(chunk_id=chunk_id, content=content, metadata=metadata))

    return chunks


def ingest_metricas_agregada() -> List[DocumentChunk]:
    """Processa tópicos e indicadores bibliométricos do OpenAlex."""
    chunks = []
    base_dir = RAW_DIR / "metricas_agregada"
    if not base_dir.exists():
        return chunks

    for file_path in base_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] Erro ao ler JSON {file_path.name}: {e}")
            continue

        if isinstance(data, dict) and "results" in data:
            results = data["results"]
        elif isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            results = [data]
        else:
            results = []

        for idx, topic in enumerate(results):
            if not isinstance(topic, dict):
                continue
            topic_id = str(topic.get("id", f"topic_{file_path.stem}_{idx}")).split("/")[-1]
            name = topic.get("display_name", "Tópico")
            works_count = topic.get("works_count", 0)
            cited_count = topic.get("cited_by_count", 0)
            subfield = topic.get("subfield", {}).get("display_name", "") if isinstance(topic.get("subfield"), dict) else ""
            field_name = topic.get("field", {}).get("display_name", "") if isinstance(topic.get("field"), dict) else ""
            domain = topic.get("domain", {}).get("display_name", "") if isinstance(topic.get("domain"), dict) else ""

            content = (
                f"Tópico de Pesquisa: {name}\n"
                f"Grande Área: {domain} -> {field_name} -> {subfield}\n"
                f"Total de Obras Indexadas: {works_count:,}\n"
                f"Total de Citações Acumuladas: {cited_count:,}\n"
                f"Impacto Médio de Citações por Obra: {(cited_count/works_count):.2f}" if works_count > 0 else "0"
            )

            chunk_id = f"agr_{topic_id}"
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                doc_type="json",
                source_file=str(file_path.relative_to(DATA_DIR)),
                base_id="metricas_agregada",
                natureza=BaseNatureza.AGREGADA,
                sensitivity=SensitivityLevel.PUBLICO,
                campo_vigencia="2024",
                extras={
                    "topic_id": topic_id,
                    "works_count": works_count,
                    "cited_by_count": cited_count,
                    "subfield": subfield,
                    "field": field_name,
                    "domain": domain
                }
            )
    return chunks


def run_ingest() -> List[DocumentChunk]:
    """Executa a ingestÃ£o completa de todas as bases e salva em data/chunks_v1.json."""
    all_chunks: List[DocumentChunk] = []
    
    all_chunks.extend(ingest_editais_normativo())
    all_chunks.extend(ingest_producao_estruturada())
    all_chunks.extend(ingest_pareceres_conversacional())
    all_chunks.extend(ingest_metricas_agregada())

    CHUNKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    serialized = [c.model_dump() for c in all_chunks]
    
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)

    print(f"[OK] IngestÃ£o concluÃ­da! Total de {len(all_chunks)} chunks gerados e salvos em {CHUNKS_FILE.relative_to(BASE_DIR)}")
    return all_chunks


if __name__ == "__main__":
    run_ingest()



