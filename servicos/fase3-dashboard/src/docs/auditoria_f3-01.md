# Auditoria F3-01 — Fase 3

**Data:** 01/11/2026  
**Parecer:** aprovada para conclusão e integrada à estrutura da Fase 7, com as correções pontuais de segurança e execução registradas abaixo.

## 1. Origem, histórico e autoria

- Módulo de origem: [EdeSufiatti/FASE3_AT1_Farmtech_dashboard](https://github.com/EdeSufiatti/FASE3_AT1_Farmtech_dashboard), remoto `origin` correspondente ao repositório original.
- Revisão original auditada: `083825fb92f5fd655be5782e2a46fed33f963377` (19/05/2026). Confirmada no `origin/main` pelo Git remoto e pela página do commit no GitHub; coincide com o HEAD local de origem. O README identifica a versão documentada como **1.0.21**; não há tag Git de versão.
- Resultado acadêmico: **11/11**, conforme informado pela responsável pelo módulo.
- O arquivo local de feedback registra retorno do professor em **02/06/2026, às 12h03**. O professor elogia a organização profissional, o mapeamento dos requisitos, a documentação e as evidências Oracle, as seis páginas do dashboard e a amplitude do notebook de ML. A observação para entregas futuras é escolher um único formato/caminho de submissão.
- A nota 11/11 não foi encontrada em arquivo versionado; é preservada aqui como informação fornecida pela responsável. O feedback histórico não é confundido com os testes desta auditoria.
- Integrantes, créditos e materiais acadêmicos originais foram preservados. Os commits originais do projeto antecedem o feedback; esta auditoria não altera a autoria nem reescreve o histórico.

## 2. Entregas e rastreabilidade dos requisitos

O módulo contém API FastAPI para dados meteorológicos e persistência Oracle, dashboard Streamlit com seis páginas, consultas e DDL Oracle, relatório e instruções, evidências de importação, utilitário PDF e notebook de ML com datasets. O mapeamento original dos critérios está no [README](../../README.md); instruções e relatório técnico estão em [executar.md](./executar.md) e [relatorio.md](./relatorio.md).

As entregas obrigatórias de organização, documentação, consultas e evidências estão representadas nesses arquivos e em `assets/rel/`. As opções “Ir além” estão implementadas no dashboard e no notebook: análise IoT, previsão e recomendações climáticas, análise de culturas, comparação de modelos e exportação PDF.

A integração com a Fase 2 ocorre pelo contrato de sensores e pelo CSV `src/dados/historico_irrigacao.csv` (154 linhas), consumido como alternativa CSV e usado no fluxo IoT/ML; o DDL define a tabela `SENSORES_FARMTECH`. O dataset acadêmico de culturas tem 2.200 linhas. A Fase 2 permanece na sua pasta própria, sem cópia ou alteração nesta auditoria. A Fase 3 integra a estrutura `farmtech-integracao/servicos/fase3-dashboard`.

## 3. Histórico de testes e verificações atuais

**Evidência histórica — não repetida:** as capturas em `assets/rel/` documentam a importação Oracle e a consulta de contagem com **154 registros**. Elas comprovam o resultado naquela execução; não comprovam a disponibilidade atual do Oracle. O relatório original descreve o procedimento.

**Verificações atuais — 01/11/2026:**

- `git fsck` e `git diff --check` sem erros; 87 referências Markdown locais verificadas, nenhuma quebrada.
- Sintaxe válida nos 28 arquivos Python e nas 10 células de código do notebook; notebook JSON válido (formato 4.5).
- CSVs legíveis: 154 registros IoT e 2.200 registros de culturas. `python run.py --help` funcionou sem iniciar serviços.
- O exercício isolado do iniciador Jupyter foi validado sem iniciar um serviço real: gera token não vazio e limita o bind a loopback.
- SQL não foi executado; conexão ao Oracle, ingestão de dados e alterações do banco não fizeram parte das verificações atuais.
- Não há suíte de testes automatizados para este módulo. O interpretador disponível não resolve `fastapi`, `pydantic` e `fpdf`; por isso não foi validada a execução integral do aplicativo nem instaladas dependências.

## 4. Segurança de dados e credenciais

- A cópia contém 118 arquivos rastreados. Não há `.env` real no diretório nem arquivo `.env` no histórico Git verificado. O [`.gitignore`](../../.gitignore) ignora `.env`, ambientes virtuais e caches. [`config/.env.example`](../../config/.env.example) contém somente valores explicitamente fictícios.
- As configurações Oracle e scripts usam variáveis `ORACLE_*`; a busca heurística no conteúdo atual e no histórico local não encontrou credencial real, token, chave privada ou senha candidata. Os exemplos de senha detectados são placeholders. Nenhuma credencial foi exibida neste relatório; não há credencial identificada que exija revogação ou rotação.
- O README publica nomes e matrículas dos integrantes e nomes dos docentes, como créditos acadêmicos originais. As capturas Oracle também deixam visíveis o identificador do schema/conta acadêmica, o alias de conexão e um caminho local do Windows. São identificadores e metadados, não senhas; foram preservados para não alterar autoria ou evidências. A responsável deve tratá-los como dados pessoais já publicados e decidir eventual anonimização antes de outra divulgação, se isso não tiver sido autorizado.
- Os CSVs contêm campos de telemetria/agronomia; a varredura textual não confirmou e-mail, CPF ou telefone. As dez capturas Oracle foram inspecionadas visualmente; os demais arquivos de imagem foram inventariados como gráficos/demonstrações, sem OCR individual. Não há arquivos de log no módulo.
- O DDL em [`createtable.sql`](../sql/createtable.sql) contém `DROP TABLE SENSORES_FARMTECH CASCADE CONSTRAINTS`. É uma instrução destrutiva quando executada, mas não foi executada nem recomendada como teste.

## 5. Correções necessárias realizadas

1. Em [notebook_ml.py](../frontend/pages/notebook_ml.py), o iniciador Jupyter desativava autenticação. Agora usa token aleatório por execução, inclui-o apenas no URL de abertura e fixa o servidor em `127.0.0.1`. Nenhum token é salvo no repositório. O acesso continua limitado à máquina local; em computador compartilhado, outros processos/usuários locais ainda podem alcançar serviços em loopback.
2. Em [executar.md](./executar.md), o exemplo SQL*Plus passou a solicitar a senha no prompt, evitando senha na linha de comando/histórico, e o caminho de ativação foi atualizado para a localização consolidada do módulo.

As correções foram limitadas à autenticação local do Jupyter e às instruções de conexão e caminho de execução. Nenhum algoritmo ou dataset foi alterado.

## 6. Limitações e conclusão

A auditoria de credenciais foi uma busca local por padrões, não uma certificação forense; a inspeção de imagens focou as dez evidências Oracle e não usou OCR automatizado. Oracle e execução completa dependem das credenciais/rede e das dependências ausentes no ambiente atual.

## 7. Encerramento F3-02

O diretório `.git` interno da Fase 3 foi removido após confirmar que o commit original está disponível em `origin/main` e no GitHub. As alterações autorizadas da F3-01 e os arquivos do módulo foram preservados. A raiz `farmtech-integracao` não possui metadados Git no momento desta verificação; nenhum novo repositório foi inicializado. O conteúdo do módulo permanece organizado no local consolidado para versionamento pelo repositório principal.

**Fase 3 — auditoria concluída, módulo integrado à estrutura da Fase 7 e arquivos preparados para versionamento.**
