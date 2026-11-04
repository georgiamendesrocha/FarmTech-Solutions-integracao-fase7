# Changelog

Evolução técnica posterior à entrega originalmente avaliada pela FIAP, com estrutura baseada em [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Não são atribuídas versões sem um lançamento identificado. O histórico acadêmico original e os registros resumidos permanecem preservados no [README](README.md#histórico-de-lançamentos).

## 2026-11-03 — Validação funcional dos modelos preservados

Resultados das validações informadas para registro documental. As inferências não foram reexecutadas nesta atualização.

### CNN do zero

- Carregamento bem-sucedido de `entrega_2/modelos/cnn_do_zero_fase6.keras`, em Python 3.13.13, TensorFlow 2.21.0 e CPU.
- Acurácia de 75%, com 6 acertos em 8 imagens de teste.
- Tempo médio desta execução: 17,33 ms/imagem.
- Execução sem treinamento ou sobrescrita do modelo preservado.

### YOLOv5s customizada

- Carregamento bem-sucedido do checkpoint original de 60 épocas, `entrega_2/modelos/yolov5s_custom_exp60_best.pt`, com execução em CPU e sem novo treinamento.
- Revisão do código de carregamento: `4add2aff6e3d926586a3eab4659f3b498dd444a1`.
- SHA-256 do checkpoint: `93c086ad8e369cc295dced96b9d48db1524226207e82ab514148f02decad2f61`.
- Banana: Precision 66,67%, Recall 22,22% e F1 33,33%.
- Milho: Precision 50%, Recall 57,14% e F1 53,33%.
- Tempo médio desta execução: 244,48 ms/imagem.

### Interpretação e encerramento da preparação

Os tempos acima pertencem às novas execuções de validação e não substituem os registros históricos do notebook. As medições não constituem um benchmark uniforme entre arquiteturas. O carregamento e a avaliação dos modelos preservados foram validados nas condições informadas; isso não equivale à validação do ambiente integrado da Fase 7 nem à conclusão dessa integração.

## 2026-11-03 — Correções após a auditoria técnica

### Adicionado

- Procedimento independente [avaliar_cnn.py](entrega_2/avaliar_cnn.py) para carregar o modelo preservado e avaliar somente o teste, com o pré-processamento original, sem treinamento ou salvamento.
- Procedimento independente [avaliar_yolo.py](entrega_2/avaliar_yolo.py), com código e pesos locais, verificação de revisão e execução isolada por abordagem. A customizada mantém a referência de carregamento `4add2aff`; a padrão exige SHA completo explícito, sem seleção automática de revisão substituta.

### Corrigido

- Tempo total de inferência da CNN no Markdown da seção 6.5, alinhado à saída experimental preservada; a média já corrigida foi mantida.
- Identificação dos ambientes históricos: Python 3.14.4 para a YOLO padrão e Python 3.13.13 para CNN e carregamento complementar da customizada, sem tratar as execuções como um ambiente único.
- Distinção entre o metadado `git.commit=f9578796b8a64889aa9e66dc06914d19f40d338e` do checkpoint e a revisão `4add2aff` registrada no carregamento complementar. A relação com os logs originais permanece a esclarecer; não se presume alteração dos pesos.
- Proteção das células experimentais históricas do notebook, preservando código, saídas, contagens de execução e metadados. A consulta não reexecuta treinamento, inferência, carregamentos externos ou salvamento; a preparação ativa limita-se a consultar dependências instaladas.
- Descrição do escopo da medição de inferência da YOLO customizada, distinguindo leitura da imagem e carregamento dos pesos.
- Qualificação das pendências antigas do documento complementar da Entrega 1 como registros históricos; orientação do README para os novos procedimentos.

### Verificação

- Na etapa de correções descrita nesta entrada, as verificações foram limitadas à integridade JSON, sintaxe, referências e proteções dos novos fluxos. Não foram executados carregamentos funcionais, avaliações completas, instalações ou downloads naquela etapa. A validação funcional posterior dos modelos preservados está registrada na entrada acima.

## 2026-11-02 — Complementação técnica da Entrega 2 e higiene do repositório

Data de consolidação comprovada pelo README e pelas saídas de carregamento dos modelos no [notebook da Entrega 2](entrega_2/comparacao_yolo_cnn_fase6.ipynb). As subetapas sem data individual registrada foram reunidas nessa consolidação; não são apresentadas como parte da entrega originalmente avaliada.

### Adicionado

- Implementação e avaliação da YOLOv5s padrão, pré-treinada no COCO, distinguindo a comparação principal da exploração complementar com YOLOv5u.
- Implementação, treinamento, avaliação e preservação da CNN do zero em `entrega_2/modelos/cnn_do_zero_fase6.keras`, com TensorFlow/Keras.
- Avaliação quantitativa da YOLOv5s customizada no conjunto de teste, reutilizando o checkpoint de 60 épocas sem novo treinamento.
- [requirements.txt](requirements.txt) com dependências selecionadas a partir dos imports, do carregamento YOLOv5 e dos metadados do ambiente Windows/CPU com Python 3.13.13. Verificação não destrutiva dos requisitos declarados e de sua compatibilidade com o ambiente instalado.
- Este CHANGELOG para registrar a evolução técnica sem repetir os resultados e as análises dos notebooks.

### Alterado

- Recuperação dos checkpoints originais de 30 e 60 épocas e dos registros experimentais, conforme a seção 5.1 do notebook da Entrega 2.
- Renomeação organizacional do `best.pt` de 60 épocas para `entrega_2/modelos/yolov5s_custom_exp60_best.pt`, preservando seus pesos e sua arquitetura.
- Registro da verificação histórica de integridade por comparação SHA-256 com o arquivo original recuperado, conforme a seção 5.1. Para o modelo de 60 épocas, a correspondência foi confirmada entre o arquivo `best.pt` enviado separadamente e `runs/train/exp60/weights/best.pt` do ZIP original. SHA-256: `93c086ad8e369cc295dced96b9d48db1524226207e82ab514148f02decad2f61`.
- Consolidação da comparação crítica entre YOLOv5s padrão, YOLOv5s customizada e CNN, com distinção entre classificação e detecção e entre resultados de validação e de teste.
- Revisão do README para apresentar as entregas, identificar os artefatos e orientar a leitura das evidências, preservando autoria, resultados e histórico acadêmico.

### Corrigido

- Compatibilidade do checkpoint produzido em Linux com o carregamento em Windows/Python 3.13, por ajuste temporário das referências de caminhos no notebook.
- Carregamento complementar da YOLOv5s customizada com a revisão `4add2aff`, separado da versão do pacote Ultralytics instalada no ambiente.
- Regras do `.gitignore`: inclusão dos ambientes virtuais, caches, temporários e segredos locais; exceções específicas para os dois modelos treinados preservados.
- Remoção das exclusões genéricas de CSV, TSV e planilhas, evitando ocultar futuras evidências experimentais por extensão. Dataset, notebooks finais e evidências permanecem elegíveis ao versionamento.

## Melhorias planejadas — não executadas

- Como melhoria opcional, identificar o commit exato do carregamento histórico da YOLOv5s padrão e validar uma revisão fixa compatível. O procedimento exige revisão explícita e não utiliza a branch principal como escolha automática.
- Esclarecer a relação entre o commit embutido no checkpoint recuperado e as revisões registradas nos logs históricos, sem substituir evidências.
- Validar dependências e execução no ambiente integrado da Fase 7; os carregamentos e as avaliações locais da CNN e da YOLO customizada já estão registrados nesta data.
- Como melhoria opcional, realizar um benchmark uniforme. Sua ausência e a reprodução independente da YOLO padrão não constituem impedimentos automáticos à integração da YOLO customizada validada.
- Validar uma instalação limpa e a reprodução funcional do ambiente, incluindo dependências transitivas e seleção das distribuições CPU; o requirements atual não é um lockfile completo.
- Conferir as condições de redistribuição dos modelos e das imagens antes da distribuição integrada à FarmTech. A permissão no `.gitignore` não substitui essa conferência.
- Definir e validar a interface e o empacotamento do componente na Fase 7, mantendo o fluxo histórico do Colab separado do ambiente local da Entrega 2.
