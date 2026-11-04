<img src="../assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Administração Paulista" width="30%">

# FarmTech Neural Vision — documentação complementar da Entrega 1

## Objetivo e equipe

Detectar e localizar banana e milho em imagens por meio de bounding boxes com YOLOv5. Este documento resume o experimento; o [README](../README.md) apresenta o projeto e as instruções, e o [notebook](../EdemirSufiatti_rm571375_pbl_fase6.ipynb) contém a implementação e a análise completa.

- Edemir Sufiatti — RM571375
- Carlos Magnus Costa Amaral — RM573978
- Georgia Mendes Rocha — RM573281
- Marina Leme Soares — RM570461

## Dados e anotações

O dataset possui 80 imagens: 40 de banana (ID 0) e 40 de milho (ID 1). Cada classe tem 32 imagens de treino, 4 de validação e 4 de teste, com labels de mesmo nome-base das imagens. A rotulagem foi manual em MakeSense.ai, Object Detection, com exportação YOLO e coordenadas normalizadas.

Banana veio da pasta `images/banana fruit` do [Fruits Dataset (Images)](https://www.kaggle.com/datasets/shreyapmaher/fruits-dataset-images). As 40 imagens finais de milho, provenientes de Pixabay e Pexels, foram escolhidas manualmente, uma a uma, considerando qualidade visual, posição e ângulo, iluminação, ambiente, palha, diversidade, número de espigas, distância e enquadramento. Banana não teve o mesmo processo de seleção manual. A ferramenta e o formato de rotulagem foram iguais nas duas classes.

## Método e resultados

O notebook utiliza Google Colab, transfer learning/fine-tuning com `yolov5s.pt` e os scripts oficiais YOLOv5 `train.py` e `detect.py`. A revisão é fixada em `4add2aff`, com imagem 640, seed 0 e limiar de confiança 0.25 explicitados. Os experimentos originais foram executados em NVIDIA Tesla T4. O número de épocas foi a principal variável experimental planejada; a `seed=0` aumenta a reprodutibilidade, mas operações estocásticas e não determinísticas em GPU podem gerar pequenas variações entre execuções e impedem atribuir as diferenças exclusivamente a essa variável.

| Épocas | Precision | Recall | mAP50 | mAP50-95 | Tempo |
| --- | --- | --- | --- | --- | --- |
| 30 | 0.535 | 0.407 | 0.466 | 0.220 | 796 s (aproximadamente 13 min 16 s) |
| 60 | 0.811 | 0.511 | 0.567 | 0.319 | 1404 s (aproximadamente 23 min 24 s) |

As métricas correspondem à validação do `best.pt` na execução final apresentada no notebook, enquanto as losses são do último epoch. Nesta execução, o `best.pt` de `exp60` foi selecionado pelas melhores métricas globais de Precision, Recall, mAP50 e mAP50-95, com aproximadamente 76% mais tempo de treinamento. A melhora foi impulsionada principalmente pelo milho: banana apresentou melhores métricas com 30 épocas, e milho com 60. Mais épocas não garantem melhor modelo, e losses menores não comprovam isoladamente melhor generalização. No teste qualitativo, houve alguma detecção em 4/8 imagens com 30 épocas (sem detecção em banana_01, banana_02, milho_03 e milho_04) e 7/8 com 60 (sem detecção somente em banana_01). Essa cobertura não representa acurácia, não substitui Precision, Recall ou mAP nem comprova isoladamente a correção das detecções. Os resultados são persistidos no Google Drive; os detalhes por classe e losses estão no notebook.

## Limitações e próximos passos

O conjunto é pequeno e restrito a duas classes, com 32 imagens de treino, 4 de validação e 4 de teste por classe. O número reduzido de instâncias de validação torna as métricas sensíveis a poucas detecções corretas ou incorretas. O treino tem 43 instâncias de banana e 101 de milho. Há heterogeneidade das imagens, processos de curadoria diferentes e inconsistências conhecidas nas anotações de banana. O resultado por classe não foi uniforme. Esses fatores podem estar associados às diferenças observadas e constituem hipóteses plausíveis, mas os dados atuais não permitem estabelecer relação causal. Um dataset maior e mais homogêneo é necessário para conclusões mais robustas.

Propõe-se aplicar à banana a curadoria manual utilizada no milho, revisar e padronizar as bounding boxes, ampliar o dataset, incluindo as instâncias de banana e os conjuntos de validação e teste, e repetir o treinamento com arquitetura, hiperparâmetros e épocas controlados, para verificar se suas métricas melhoram, sem antecipar esse resultado.

**Registro histórico de fechamento da Entrega 1.** O parágrafo seguinte preserva o estado documentado originalmente e não constitui uma lista de pendências atuais. O vídeo e seu link já estão apresentados no [README](../README.md); a evolução posterior está no [CHANGELOG](../CHANGELOG.md).

A execução funcional integral foi concluída e validada no Google Colab, incluindo dataset, GPU Tesla T4, `data.yaml`, treinamentos de 30 e 60 épocas, persistência no Drive e inferência sobre as 8 imagens de teste. Os outputs reais de treinamento, validação, inferência e gráficos já foram incorporados ao notebook principal revisado, preservando os Markdown. As evidências visuais foram conferidas e incorporadas: 10 prints estão organizados em `assets/evidencias/`, e 4 exemplos representativos estão no README. A comparação 30 × 60, a análise banana × milho e as instruções de reprodução no Colab estão atualizadas. Permanecem pendentes o vídeo final de até 5 minutos no YouTube, não listado, seu link no README, a auditoria final do repositório, a higiene final/Git, commit e push e o envio da entrega. Segundo a orientação recebida pelo grupo, a tutoria corrigiu a exigência de repositório público do enunciado; ela não é tratada como requisito obrigatório.
