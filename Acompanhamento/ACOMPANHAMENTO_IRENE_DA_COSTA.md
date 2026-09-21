# Encontro 1 14/09/2026
    Hoje conversamos como ficaria a divisão das tarefas, escolhi o Marcos pra ser nosso líder do grupo, criei a pasta com o repositório do Grande Desafio IA Generativa RAG, criei um grupo de WhatsApp com os integrantes do grupo pra ter melhor conversa sobre o desenvolvimento, escolhi o cenário 3 e por hoje foi só isso.
# Resumo do dia em conjunto: o que a equipe entregou, o que travou, qual o próximo passo.

# Encontro 2 16/09/2026
Hoje foquei na estruturação da Etapa 1 do nosso projeto e deixei o pipeline de coleta e observabilidade totalmente operacional.

Criei a estrutura de código (`src/`)**: Organizei os módulos centrais da nossa arquitetura no VS Code:
    - Implementei o `src/fetch_corpus.py` com suporte aos subcomandos de CLI (`fetch`, `update`, `inventory`), garantindo a coleta idempotente e o versionamento em disco.
    - Montei o `src/obs.py` para garantir o logging estruturado em `.jsonl` e a medição de latência e consumo de tokens por etapa.
    - Defini os schemas em `src/schema.py` com Pydantic para validar metadados como sensibilidade, natureza das bases e respostas.
Ajustei o manifesto e rodei a coleta**: Corrigi a sintaxe YAML do `corpus_manifest.yaml` (ajustando os comentários com `#`), executei a coleta inicial via terminal e validei a geração automática dos artefatos em `data/inventory/v1.json` e no `CORPUS_INVENTORY.md`.

Sincronizei no GitHub**: Realizei o commit de todas as alterações da estrutura e dos inventários gerados e fiz o `git push` para o repositório.

Próximos passos:

- Avançar para a Etapa 2: implementar o fatiamento (chunking) dos textos e a geração de embeddings para o índice vetorial.

 # Encontro 3 - 18/09/2026

## O que eu fiz hoje:
- Selecionei e baixei os 3 artigos em PDF referentes ao Cenário 3 (Pesquisa Acadêmica / RAG).
- Coloquei os arquivos PDF dentro do diretório `data/raw/v1/editais_normativo/`.
- Configurei o arquivo `corpus_manifest.yaml` adicionando os nomes exatos dos 3 PDFs.
- Executei o comando no terminal para coletar o corpus e gerar o inventário (`data/inventory/v1.json` e `CORPUS_INVENTORY.md`).
- Fiz anotações no meu Notion pessoal.

## Próxima etapa:
- Iniciar a Etapa 2 do projeto: realizar o processamento e a divisão dos textos (chunking) dos arquivos PDF para a base de conhecimento RAG.

# Encontro 4 - 21/09/2026

## O que eu fiz hoje:
- Alinhamento e Pesquisa do Escopo: Realizei pesquisas para alinhar a estrutura do Cenário 3 (Inteligência sobre Pesquisa Acadêmica) ao problema real de cruzamento de dados de fomento.
- Mapeamento de Fontes Oficiais: Identifiquei e mapeei os repositórios oficiais de normas e editais de fomento (como FAPERJ e CNPq) para compor a base `editais_normativo`.
- Revisão da Arquitetura do Corpus: Planejei a substituição do corpus preliminar pelos documentos normativos corretos que serão consumidos na Etapa 1.
- Fiz anotações de pesquisas no Gemini no meu Notion pessoal.

## Próxima etapa:
- Baixar os editais reais em PDF (FAPERJ/CNPq) para a pasta `data/raw/v1/editais_normativo/`.
- Atualizar o manifesto (`corpus_manifest.yaml`) e rodar o script de coleta para consolidar o inventário v1 no VS Code.
