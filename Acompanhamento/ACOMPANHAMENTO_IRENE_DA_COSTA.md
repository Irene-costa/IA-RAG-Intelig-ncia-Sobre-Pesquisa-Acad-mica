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

# Encontro 5 - 23/09/2026

## O que eu fiz hoje:

- Testes de Ingestão e Processamento: Executei o script de ingestão (`python -m src.ingest`), gerando com sucesso 2145 chunks salvos em `data/chunks_v1.json`.
- Diagnóstico do Pipeline de Embeddings: Iniciei a execução da geração de embeddings (`src.pipeline`/`src.index`), identificando um travamento por timeout na conexão da API (`Connection error` / parada na requisição HTTP).
- Ajuste de Parâmetros de Execução: Mapeei a necessidade de otimizar o tamanho do lote (`BATCH_SIZE`) e o tempo de pausa (`RATE_LIMIT_PAUSE_SEC`) para evitar estouro de limite de requisições.

## Próxima etapa:

- Ajustar os parâmetros no arquivo de configuração (`config.py` / `.env`) reduzindo o lote para requisições menores.
- Rodar novamente o script de indexação e validar a suíte de testes com `python -m pytest`.

## Encontro 6 - 25/09/2026

### O que fiz hoje:

Concluí com sucesso a execução, teste, validação e expansão de corpus ponta a ponta de todos os módulos do projeto referentes ao Cenário 3 (Inteligência sobre Pesquisa Acadêmica - FAPERJ/CNPq).

### Atividades e Testes Realizados Hoje

1. Ajuste de Dependências e Ambiente
    - Resolvi a divergência de digitação do arquivo de dependências e validei a presença do requirements.txt na raiz do projeto.
2. Benchmark de Avaliação (eval.benchmark)
    - Executei o script de avaliação com as 20 perguntas do cenário acadêmico (eval.benchmark).
    - Observei a ativação automática do mecanismo de fallback léxico (BM25) devido ao timeout na API remota de embeddings, o que garantiu a conclusão total da avaliação.
    - Confirmei a geração dos resultados salvos em eval/benchmark_results.json.
3. **Interface de Linha de Comando (app.cli)
    - Testei de forma interativa a interface CLI (app.cli), validando a recuperação do contexto, a exibição das fontes e o tempo de resposta do pipeline.
    - Validei o funcionamento dos guardrails éticos/de dados sensíveis e encerrei a sessão normalmente.
4. Testes Unitários (unittest)
    - Rodei a bateria de testes automatizados com `python -m unittest discover tests.
    - Resultado: Obtive 100% de aprovação (`Ran 10 tests in 0.042s` -> OK).
5. **Pipeline de RAG (src.pipeline)
    - Executei o fluxo do pipeline (src.pipeline) para validar a ingestão e recuperação de trechos.
    - Verifiquei a correta citação e mapeamento das 6 fontes dos editais e normativos da FAPERJ e CNPq.
6. **Servidor Web (app.server)
    - Iniciei o servidor web do Adaptive RAG (app.server) e validei a disponibilização do serviço local na porta http://localhost:8000.
7. Descoberta e Ingestão Automática de Corpus (src.auto_discover_corpus)
    - Executei o script de descoberta automática python -m src.auto_discover_corpus --target 160 --auto-ingest.
    - Realizei a varredura e ingestão automática de novos documentos do Cenário 3 até atingir a meta estabelecida, atualizando a base local e os vetores de busca.
    8. Notion
    -Fiz anotações no Notion pessoal.

### Próximos Passos (Para o Próximo Encontro)

- Apresentar ao grupo os resultados obtidos no benchmark e a validação do pipeline com o corpus expandido.
- Discutir refinamentos nas métricas de avaliação do RAG e possíveis otimizações no tempo de resposta (latência) da recuperação vetorial.
- Integrar as contribuições individuais dos membros do grupo para a consolidação da entrega final.
- Atualizar a documentação geral do repositório conforme as orientações combinadas com a equipe.