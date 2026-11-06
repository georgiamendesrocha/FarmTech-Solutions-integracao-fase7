# FarmTech Solutions — Fase 7 · Auditoria do Lote 1

Data: **06/11/2026**, America/Bahia. Branch: `feature/dashboard-fase7`.

**Recomendação: APTO PARA COMMIT do conjunto revisado.** Não há bloqueio técnico conhecido após as correções e a bateria final. O índice foi preservado; antes do commit, é necessário incluir as alterações e os arquivos novos descritos abaixo. Nenhum commit, push, merge, alteração remota, treinamento ou operação AWS foi executado.

## 1. Problemas encontrados e criticidade

| Criticidade | Problema comprovado | Resultado |
|---|---|---|
| Alta | O novo fluxo de inferência por upload verificava HEAD/pesos, mas não recusava alterações no código YOLO nem instalava a proteção de rede/processos do avaliador preservado. | Corrigido reutilizando as proteções existentes antes do carregamento do framework. |
| Média | Ctrl+C ou exceção durante a inicialização podia deixar o Streamlit sem controle do launcher. | Corrigido; o processo criado é encerrado antes da propagação da exceção. |
| Média | A configuração integrada podia manter a simulação habilitada e substituía um `DB_PATH` explicitamente informado. | Corrigido no launcher e na configuração do dashboard. |
| Média | Configuração YOLO inválida e imagem com dimensões excessivas podiam derrubar a página de visão computacional. | Rejeição controlada; regressões reproduziram as falhas antes da correção. |
| Baixa | A página de sensores comparava `indisponível` com o estado contratual `indisponivel`, exibindo “parada” em situação de erro. | Corrigida uma comparação; regressão confirma o aviso correto. |
| Baixa | Faltavam regras preventivas para credenciais/chaves e cache pytest no `.gitignore` raiz. | Adicionadas regras pontuais, preservando exemplos, datasets e backups. |
| Baixa | Testes ainda pressupunham navegação isolada, mensagens sem acentos, início automático da simulação e ausência de R. Sete páginas já haviam evoluído em relação ao manifesto histórico. README também descrevia funcionalidades anteriores. | Harness e expectativas atualizados; suplemento de hashes estritamente limitado às sete páginas; documentação operacional corrigida. |

Não foram identificadas credenciais concretas expostas na inspeção dos exemplos e na varredura sanitizada de 288 arquivos textuais elegíveis, até 6 MB por arquivo. Essa verificação não equivale a uma análise integral de todo o histórico Git ou dos arquivos binários. Nenhum segredo foi reproduzido.

Nenhum cache, log, ambiente virtual, segredo ou temporário indevidamente rastreado foi encontrado. Resíduos ignorados, backups e arquivos de finalidade histórica foram preservados.

## 2. Arquivos alterados neste lote

| Caminho | Motivo |
|---|---|
| `.gitignore` | Ignorar `.aws/`, `.ssh/`, `secrets.toml`, `credentials.json`, `*.pem`, `*.key` e `.pytest_cache/`. |
| `README.md` | Atualizar instruções de R, exportação CSV, Oracle e upload YOLO; separar validação histórica de testes atuais. |
| `iniciar.py` | Limpar o processo em falhas de startup, tratar indisponibilidade do navegador e respeitar `DB_PATH`. |
| `farmtech_integracao/demo.py` | Desabilitar simulação na abertura integrada e preservar banco explicitamente configurado. |
| `farmtech_integracao/workers/fase6_worker.py` | Validar código do checkout e bloquear rede/processos antes de importar o framework na inferência. |
| `servicos/fase4-regressao/src/frontend/pages/1_Sensores_IoT.py` | Corrigir o identificador do estado de indisponibilidade. |
| `servicos/fase4-regressao/src/frontend/pages/12_Visao_Computacional.py` | Tratar dimensões excessivas e configuração YOLO inválida. |
| `tests/integracao/test_launcher.py` — novo | Sete regressões do ambiente e ciclo de vida do launcher, com mocks. |
| `tests/integracao/test_dashboard.py` | Navegar pelo roteador real; testar as duas rejeições controladas da página YOLO. |
| `tests/integracao/test_demo_integrity.py` | Testar configuração explícita de banco e conferir os 203 arquivos com suplemento restrito de UI. |
| `tests/integracao/test_fase2.py` | Verificar disponibilidade com e sem R instalado, garantindo ausência de execução automática. |
| `tests/integracao/test_fase6.py` | Testar recusa de código YOLO alterado e instalação da proteção antes do framework. |
| `servicos/fase4-regressao/tests/test_frontend_safety.py` | Corrigir o smoke para registrar a navegação antes de alternar páginas. |
| `servicos/fase4-regressao/tests/test_recommendations_audit.py` | Normalizar apenas diacríticos nas comparações, mantendo as verificações de conteúdo e severidade. |
| `servicos/fase4-regressao/tests/test_scheduler_audit.py` | Isolar configuração, iniciar produtor apenas na fixture, capturar cartões e testar indisponibilidade. |
| `docs/integridade-ui-lote1.json` — novo | Registrar hashes das sete páginas F4 revisadas, sem alterar o manifesto histórico. |
| `docs/AUDITORIA_LOTE1.md` — novo | Registrar esta entrega consolidada. |

As demais alterações já existentes na abertura do lote foram revisadas e mantidas. Nenhuma funcionalidade recebeu refatoração ampla. Resultados de execução ficam nas áreas ignoradas `.runtime/validation/lote1-20261106/` e `.runtime/exports/fase2/`; fixtures R/C++ também permanecem nas áreas temporárias próprias dos testes.

Preservação conferida: os **196 arquivos fora do suplemento** continuam correspondendo ao manifesto original; as **sete páginas** correspondem ao suplemento, totalizando **203 verificações de hash**. `docs/integridade-int02.json` permanece intacto. O logo `assets/logo-fiap.png` e as **44 evidências** em `docs/evidencias/` mantêm os bytes observados no início da auditoria. Nenhum arquivo existente no inventário inicial foi removido pelo lote.

## 3. Testes executados e resultados

| Suíte final | Casos | Aprovados | Não executados | Falhas/erros |
|---|---:|---:|---:|---:|
| Integração: adaptadores, runtime, dashboard, integridade e launcher | 67 | 67 | 0 | 0 |
| Fase 1 | 16 | 16 | 0 | 0 |
| Fase 2 Python | 40 | 31 | 9 | 0 |
| Fase 4: seleção sem treinamento | 129 | 129 | 0 | 0 |
| **Total Python** | **252** | **243** | **9** | **0** |

Os nove casos não executados são cenários C++ sem compilador host disponível; não foram marcados como aprovados. As falhas iniciais de configuração e expectativas desatualizadas foram corrigidas e as suítes afetadas foram executadas novamente. A tabela registra as execuções finais, sem somar repetições.

Verificações adicionais efetivamente executadas:

- **R 4.5.3:** 16 grupos aprovados; análise de cópia do histórico com 153 registros e integração de três linhas sintéticas com interpolação conferida. A primeira tentativa encontrou um `LC_ALL=C.UTF-8` inválido no Windows; a repetição usou locale UTF-8 válido apenas no processo de teste, sem modificar a configuração global.
- **Sintaxe:** 125 arquivos Python, cinco notebooks como JSON, 95 células de código sem comandos mágicos e 15 arquivos JSON sem erros. Nenhuma célula de notebook foi executada.
- **Dashboard:** 13 telas renderizadas pelo AppTest com a navegação real; ações externas mockadas. Cálculos F1, consultas CSV, SQLite isolado, rollback e limites de subprocessos exercitados localmente.
- **HTTP real local:** `200 /_stcore/health` em `127.0.0.1`, sem abrir navegador; processo encerrado e porta sem aceitar conexões ao final.
- **Dependências:** Python F4 3.11.9 e F6 3.13.13 conferidos; `pip check` aprovado nos dois ambientes existentes. Nenhuma instalação ou atualização.
- **Git/higiene:** `git diff --check` e `git diff --cached --check` aprovados; nenhum conflito de índice ou marcador de conflito encontrado; nenhum rastreado conflita com as regras de ignore. Onze amostras privadas/cache ignoradas e quatro exemplos mantidos elegíveis.

A seleção F4 segue `F4_TESTS` de `scripts/validar_testes.py`. Logs e resumos finais por suíte estão em `.runtime/validation/lote1-20261106/`; a primeira execução F4 também foi preservada com prefixo `fase4-initial`.

## 4. Pendências e limites da validação

**Não há pendência técnica conhecida que impeça formar o commit revisado.** Antes de efetivá-lo, é necessário selecionar os arquivos e obter a aprovação exigida para o commit. O índice atual contém apenas as exclusões dos templates; um commit somente desse índice deixaria de fora as correções e evidências.

Incluir conjuntamente os arquivos novos necessários: `farmtech_integracao/fase2_r.py`, `scripts/validar_r_fase2.py`, as 44 evidências, o teste do launcher, o suplemento de integridade e este relatório, além das alterações rastreadas revisadas.

Permanecem **não executados neste lote**: treinamento/reprodução científica que ajusta estimadores; inferência ou avaliação YOLO real; Oracle real; consultas externas Open-Meteo/NOAA/INMET/IBGE; hardware, serial e Wokwi; inspeção visual em navegador e implantação externa. As verificações com mocks não comprovam conectividade, autenticação ou desempenho de inferência. A execução R exige um locale válido no ambiente que a hospedar.

## 5. Situação final do Git

- Branch: `feature/dashboard-fase7`, com **0 commits à frente e 0 atrás** da referência local `origin/feature/dashboard-fase7`; não houve fetch ou consulta remota.
- **156 exclusões já staged**, exclusivamente **78 em `1TIAO/` e 78 em `2TIAO/`**. São as remoções intencionais dos templates; as pastas não foram reintroduzidas.
- **28 arquivos rastreados modificados, ainda fora do staging.**
- **49 arquivos não rastreados**, incluindo as 44 evidências e os cinco arquivos novos de código, teste e documentação. Contagem por arquivo, mesmo quando `git status --short` agrupa diretórios.
- Nenhuma exclusão fora dos templates, conflito ou erro de whitespace. Índice preservado, sem commit, push ou merge.

## 6. Recomendação objetiva

**APTO PARA COMMIT do conjunto revisado**, após incluir os arquivos pertinentes no staging e receber aprovação para efetivar o commit. Os defeitos comprovados foram corrigidos, as suítes locais permitidas terminaram sem falhas e os artefatos históricos verificados foram preservados. Essa recomendação não declara aprovada a publicação externa nem os testes explicitamente não executados.
