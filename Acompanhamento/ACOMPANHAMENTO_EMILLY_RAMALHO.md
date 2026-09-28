# Encontro 1 14/09/2026
    
# Resumo do dia em conjunto: o que a equipe entregou, o que travou, qual o próximo passo.

* Foi feita a criação da organização no GitHub de Projeto de Inteligência sobre Pesquisa Acadêmica.
* Criação do Grupo do Whatsapp.
* Separação das funções ainda não foi realizada. 

# Encontro 2 16/09/2026

* Foi criado o arquivo `requirements.txt`, reunindo e organizando as dependências necessárias para o projeto.
* Foram adicionados os arquivos `fetch_corpus`, `obs` e `schema`, estruturando os componentes iniciais do projeto.
* No início do desenvolvimento, foi criado um repositório para centralizar o projeto e disponibilizá-lo aos integrantes da equipe. Posteriormente, optou-se pela criação de uma organização no GitHub para facilitar o gerenciamento e a colaboração entre os membros.
* Durante o dia, foi identificado um problema de acesso ao repositório, que apresentava a mensagem “Page Not Found” ao ser acessado.

# Encontro 4 21/09/26

* Fiz um levantamento de documentos relacionados à Inteligência Artificial e à pesquisa acadêmica, buscando materiais que pudessem contribuir para o enriquecimento da base utilizada no RAG.
* Após a pesquisa, selecionei os conteúdos pertinentes e realizei a organização dos arquivos na pasta `data/raw/v1/editais_normativo`, deixando os documentos estruturados para dar continuidade ao processo de alimentação da base.

# Encontro 5 23/09/26

* Foram realizadas algumas alterações e implementações no código, além de ajustes necessários no projeto.
* Realizei os testes dos arquivos e funcionalidades desenvolvidos.
* Instalei e configurei as dependências necessárias para executar o projeto corretamente no meu ambiente.
* Após os ajustes, refiz os testes e as funcionalidades apresentaram o comportamento esperado.
* Também identifiquei que a execução dos testes está ocorrendo de forma mais lenta, possivelmente devido à utilização simultânea do ambiente/vídeo da PUC-Rio por várias pessoas, o que pode estar gerando maior demanda de recursos e impactando o tempo de execução.

# Encontro 6 25/09/26

* Foram realizados testes nos componentes do projeto para validar o funcionamento e possibilitar o avanço para as próximas etapas.
* Durante os testes, ocorreram alguns casos de Request Timeout, principalmente durante a etapa de busca e avaliação das questões, devido à demora na resposta do servidor LLM remoto.
* Eu e Ellen também trabalhamos na criação de um automatizador para busca de arquivos, com o objetivo de facilitar a coleta dos materiais necessários.
* Após os testes, optamos por utilizar o automatizador desenvolvido pelo Marcos, que apresentou um funcionamento satisfatório e atendeu bem à necessidade do projeto.
* Com isso, foi possível validar as soluções e definir os componentes que serão utilizados para dar continuidade ao desenvolvimento.

# Encontro 7 28/09/26

* Instalei e corrigi as dependências necessárias para executar o Streamlit no ambiente.
* Executei a aplicação streamlit_app.py e validei o funcionamento da interface web localmente.
* Realizei testes funcionais na interface, verificando o comportamento da aplicação e o processamento das consultas.
* Testei a geração e recuperação das respostas, avaliando se o RAG estava retornando as informações de forma adequada.
* Pesquisei sobre bancos de dados vetoriais e sua utilização em aplicações RAG, buscando entender melhor o armazenamento, geração de embeddings e recuperação de informações por similaridade.
* A partir da pesquisa e das discussões realizadas com a equipe, entramos em consenso pela utilização do ChromaDB como banco de dados vetorial do projeto.


