# FarmTech Solutions — Validação complementar C++ e YOLO

Data: **06/11/2026**, America/Bahia. Repositório: `farmtech-envio-fase7`. Branch: `feature/dashboard-fase7`.

**VALIDAÇÃO COMPLEMENTAR APROVADA.** Os nove cenários C++ foram compilados e executados, e os uploads reais de banana e milho passaram pela página de Visão Computacional, adaptador, worker e checkpoint original. Este documento complementa `AUDITORIA_LOTE1.md`, preservado como registro da rodada anterior.

## 1. C++ — compilador configurado e nove testes executados

A busca no PATH e em instalações usuais fora dele não encontrou GCC, Clang ou MSVC host utilizável. Os compiladores Xtensa/RISC-V/AVR existentes são destinados a outras arquiteturas. Foi instalado **GCC 16.2.0, MinGW-W64 x86_64 UCRT POSIX SEH, r3**, pelo pacote padrão `BrechtSanders.WinLibs.POSIX.UCRT`, versão **16.2.0-14.0.0-r3**.

Comando de instalação executado com êxito, no escopo do usuário:

```powershell
winget install --id BrechtSanders.WinLibs.POSIX.UCRT --exact --source winget --scope user --accept-package-agreements --accept-source-agreements --disable-interactivity
```

O `winget` verificou o hash do arquivo e concluiu com código **0**. A extração foi lenta, mas terminou normalmente. Não houve instalação adicional de MSYS2/MSVC nem solicitação de privilégio administrativo. O instalador registrou seus aliases no PATH do usuário; a tarefa não alterou manualmente o PATH da máquina.

Compilador instalado em:

```text
%LOCALAPPDATA%\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin\g++.exe
```

O harness passou a reconhecer esse local padrão mesmo quando o shell ainda conserva o PATH anterior. A descoberta automática foi comprovada em novo processo Python, com **`FARMTECH_CXX` ausente**.

O mecanismo original de `servicos/fase2-iot/tests/firmware_host_harness.py` extrai literalmente três funções e sete constantes de `servicos/fase2-iot/src/prog1.ino`, gera `firmware_rules.cpp` e compila um executável Windows. Não foi necessário alterar a lógica do firmware nem as condições esperadas dos testes.

Comando de compilação efetivamente utilizado, com os caminhos completos registrados em `cpp-results.json`:

```text
g++.exe -std=c++11 -O0 -Wall -Wextra firmware_rules.cpp -o firmware_rules.exe
```

Nesta execução, fonte gerada e executável ficaram em `servicos/fase2-iot/tests/.tmp_firmware_m6bfoshs/`.

| Cenário C++ executado | Resultado |
|---|---|
| `isolated_n_missing` | Aprovado |
| `same_values_n_present` | Aprovado |
| `corrected_ph_stays_ideal` | Aprovado |
| `ph_outside_npk_full` | Aprovado |
| `moisture_boundaries` | Aprovado |
| `invalid_humidity` | Aprovado |
| `ph_mapping_and_adjustments` | Aprovado |
| `invalid_ph` | Aprovado |
| `other_nutrients_missing` | Aprovado |

**Resultado: 9 executados, 9 aprovados, 0 reprovados, 0 erros e 0 skips**, em 2,109 segundos incluindo a preparação/compilação da classe de testes.

Reprodução somente desses nove casos, a partir da raiz:

```powershell
.\servicos\fase4-regressao\.venv-f402\Scripts\python.exe -X utf8 -B -m unittest discover -s servicos/fase2-iot/tests -p test_firmware_cpp.py -k FirmwareCppTests -v
```

O SHA-256 de `src/prog1.ino` permaneceu `6064b58fec80c405346d8cdd1ffc13b1d2d4c1b9caeaa6b33fd7506250ce6173`. A aprovação se refere às funções puras exercitadas no host; não representa compilação completa ESP32 nem teste de GPIO, Wokwi, serial ou hardware.

## 2. YOLO — inferência real de banana e milho

Foi reutilizado o ambiente `servicos/fase6-visao/.venv-fase6/Scripts/python.exe`, **Python 3.13.13**, com **PyTorch 2.15.0**, **torchvision 0.29.2** e **ultralytics 8.4.198** existentes. O `pip check` desse ambiente passou. Não houve instalação/atualização de pacotes Python, treinamento ou download/substituição de checkpoint.

Modelo utilizado: `servicos/fase6-visao/entrega_2/modelos/yolov5s_custom_exp60_best.pt`. O SHA-256 conferido antes e depois foi:

```text
93c086ad8e369cc295dced96b9d48db1524226207e82ab514148f02decad2f61
```

Checkout reutilizado: `C:/Users/Georgia/yolov5-validacao-fase6`, na revisão **`4add2aff6e3d926586a3eab4659f3b498dd444a1`**. HEAD e fontes/configurações foram conferidos antes e depois, sem alterações. O modelo carregou com sucesso em CPU, confirmou as classes **`0: banana`, `1: milho`** e executou a inferência com tamanho **640** e confiança mínima **0,25**.

| Imagem original de teste | Dimensões | Detecções retornadas | Carga do modelo (ms) | Inferência (ms) | Percurso do botão (ms) |
|---|---|---|---:|---:|---:|
| `banana/banana_01.jpg` | 450 × 600 | banana **26,21%**; milho **26,36%** | 14669,03 | 246,30 | 25360,77 |
| `milho/milho_02.jpg` | 3024 × 4032 | milho **60,46%**; milho **50,25%** | 15313,01 | 341,21 | 25808,96 |

O tempo de carga mede `torch.hub.load`, configuração e conferência das classes; não inclui o import inicial de PyTorch. O tempo de inferência inclui a chamada do modelo e obtenção das predições em CPU, sem aquecimento separado. O percurso completo do botão inclui inicialização do worker, imports e renderização. São medições desta execução, sem pretensão de benchmark.

**A detecção de milho na imagem de banana é um falso positivo**, e a detecção de banana tem confiança baixa. Isso evidencia limitação preditiva; não houve falha técnica no carregamento ou na comunicação. A validação de duas imagens não estabelece acurácia geral do modelo. Nenhum limiar ou peso foi alterado para melhorar os resultados.

O fluxo validado foi:

```text
Página 12 / botão Identificar banana ou milho
  → fase6.inferir_imagem
  → subprocesso worker Python 3.13.13
  → torch.hub.load local / checkpoint preservado
  → JSON com detecções, classes e tempos
  → imagem marcada e tabela na página
```

Nas duas imagens: **status `ok`, zero exceções de interface, zero erros de interface e uma tabela renderizada**. Como o AppTest não oferece upload nativo, apenas a entrega dos bytes ao `file_uploader` foi controlada. Página, botão, adaptador, subprocesso, PyTorch e modelo executaram de verdade; resultados e workers não foram mockados nessa validação.

Comando executado:

```powershell
.\servicos\fase4-regressao\.venv-f402\Scripts\python.exe -X utf8 -B scripts/validar_yolo_integrada.py --yolo-repo C:/Users/Georgia/yolov5-validacao-fase6 --inferencias
```

A tentativa inicial no sandbox foi recusada pelo Git devido à diferença de proprietário do checkout. A execução foi repetida com a autorização da ferramenta fora do sandbox, sob o usuário proprietário. Nenhuma exceção global `safe.directory` foi adicionada. As proteções existentes contra rede, instalação automática e subprocessos indevidos foram mantidas.

## 3. Correções e arquivos modificados

| Arquivo | Alteração necessária |
|---|---|
| `servicos/fase2-iot/tests/firmware_host_harness.py` | Descobrir o GCC no diretório padrão de pacotes WinGet quando o PATH do processo ainda não foi recarregado. |
| `farmtech_integracao/workers/fase6_worker.py` | Acrescentar confirmação de modelo carregado, classes e tempos separados de carga/inferência ao resultado do upload. |
| `scripts/validar_yolo_integrada.py` | Remover o acesso ao `text_input` que deixou de existir; configurar checkout pelo ambiente; acrescentar `--inferencias` e `--output`, com validação real dos dois uploads e conferência de preservação. |
| `tests/integracao/test_fase6.py` | Acrescentar regressão da telemetria e confirmar que inferência sem detecções também pode retornar sucesso técnico. |
| `docs/VALIDACAO_COMPLEMENTAR_CPP_YOLO.md` — novo | Registrar esta entrega única. |

Os **13 testes específicos F6 passaram** após a alteração do worker. Sintaxe dos arquivos Python modificados e `git diff --check` foram aprovados. Os 243 testes Python e 16 grupos R da auditoria anterior não foram repetidos como bateria; somente o módulo F6 afetado foi reexecutado, além dos nove C++ agora habilitados.

## 4. Dependências e evidências

A única dependência instalada foi o toolchain GCC/MinGW-w64 pelo WinGet. Os ambientes Python/YOLO existentes foram reutilizados. Não foram necessárias alterações de firmware, modelos ou página de produção.

Evidências locais preservadas em `.runtime/validation/complementar-20261106/`:

- `cpp-results.json`: versão, caminho, comando completo/cwd da compilação, hashes do firmware e resultado dos nove casos.
- `cpp-tests.log`, `cpp-compiler-version.txt`, `cpp-installation.json` e `cpp-winget.log`: execução e instalação concluídas.
- `yolo-integrada.json` e `yolo-integrada.log`: detecções, confidências, caixas, tempos, interface e hashes antes/depois.
- `baseline.json`: inventário de preservação no início deste lote; registros da primeira tentativa YOLO também foram mantidos.

## 5. Pendências reais

**Nenhuma das duas pendências solicitadas permaneceu.** Não há comando administrativo ou intervenção manual pendente. Nesta sessão Codex, executar o GCC instalado e consultar o checkout YOLO exigiu sair do sandbox devido às restrições de acesso/propriedade; os testes foram efetivamente concluídos nesse contexto autorizado.

Permanecem como limites de escopo a validação física ESP32 e a avaliação preditiva ampla do modelo, sem impedir a aprovação técnica solicitada. Não foi feita inspeção visual manual em navegador; a página foi exercitada pelo AppTest.

## 6. Conclusão

**VALIDAÇÃO COMPLEMENTAR APROVADA:** nove cenários C++ compilados/executados e aprovados; inferências reais de banana e milho integradas ao dashboard, com carregamento e comunicação comprovados. README definitivo, firmware histórico, notebooks, datasets, modelos, documentos anteriores, logo e evidências foram preservados. Nenhum commit, push, merge, alteração remota de repositório ou operação AWS foi executado.
