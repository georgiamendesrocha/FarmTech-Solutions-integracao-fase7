# FIAP — Faculdade de Informática e Administração Paulista

<p align="center">
<a href="https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="FIAP — Faculdade de Informática e Administração Paulista" border="0" width="40%" height="40%"></a>
</p>

<br>

# FarmTech Solutions – Agricultura Digital

Projeto de gestão agrícola (Python + R) – atividade avaliativa FIAP.

Link video no yoytube - não listado  
https://youtu.be/zYY6PB0g4Ug

**Repositório original — Fase 1:** [https://github.com/EdeSufiatti/farmtech](https://github.com/EdeSufiatti/farmtech)

---

## Estrutura do projeto

Organização baseada no template FIAP, com as pastas `assets`, `config`, `document`, `src`, `.github` e `tests`. O código-fonte está em `src/`; os dados exportados ficam em `config/`; os testes automatizados estão em `tests/`. Na raiz, o arquivo `farm.py` funciona como atalho para executar a aplicação Python.

```
farmtech-fase1/
├── .github/
│   └── problem-report.md
├── .vscode/
│   └── settings.json
├── assets/
│   └── logo-fiap.png
├── config/
│   ├── dados_fazenda.csv
│   ├── insumos_por_talhao.csv
│   └── readme.md
├── document/
│   ├── instruoces-avaliacao-fase1
│   └── README.md
├── src/
│   ├── farm.py
│   ├── vetor_produtos.py
│   ├── analise_estatistica.R
│   ├── clima_meteorologico.R
│   ├── app.R
│   └── readme.md
├── tests/
│   ├── test_geometria.py
│   └── test_insumos.py
├── .gitattributes
├── .gitignore
├── farm.py
└── README.md
```

---

## Pré-requisitos

| Ferramenta | Versão mínima | Verificar |
|------------|---------------|-----------|
| Python | 3.8+ | `python --version` |
| pandas | qualquer | `pip install pandas` |
| R | 4.0+ | `Rscript --version` |

> Os pacotes R (`dplyr`, `httr`, `jsonlite`) podem ser instalados na primeira execução dos scripts.

---

## Como abrir o projeto

No VS Code ou Cursor: **File → Open Folder** → pasta do repositório. Use o terminal integrado na **raiz** do projeto.

---

## 1. Aplicação Python

### Executar (na raiz do repositório)

```powershell
python farm.py
```

(Equivale a executar `src/farm.py` com o `PYTHONPATH` correto.)

### Menu de opções

| Opção | Descrição |
|-------|-----------|
| 0 | Carregar dados de `config/dados_fazenda.csv` |
| 1 | Inserir dados (talhão, área, cultura, linhas) |
| 2 | Listar dados |
| 3 | Atualizar dados |
| 4 | Excluir dados |
| 5 | Exportar dataframe → `config/dados_fazenda.csv` |
| 6 | Calcular uso de produtos |
| 7 | Calcular insumos por talhão (por metro de linha) |
| 8 | Sistema de Análise R (`src/app.R`) |
| 9 | Sair |

> Use a opção **5** antes de rodar o R para atualizar o CSV.

### Cálculo das áreas dos talhões

O sistema utiliza as seguintes fórmulas:

- Círculo: área calculada pelo raio.
- Triângulo: fórmula de Heron, com validação dos lados.
- Quadrilátero: cálculo de área retangular (comprimento × largura).
- Pentágono, hexágono, heptágono e octógono: fórmulas de polígonos regulares.

Para polígonos de 5 a 8 lados, o sistema exige medidas iguais e pressupõe ângulos de um polígono regular.

As linhas de plantio são estimativas simplificadas. A extensão teórica é calculada dividindo a área do talhão pelo espaçamento, sem descontar áreas não cultivadas.

### Cálculo e comparação de insumos

O sistema calcula a quantidade total de insumos pela área do talhão, convertida em hectares, multiplicada pela dose recomendada por hectare.

- Quantidade total = área (ha) × dose por hectare.
- Custo por hectare = dose × preço unitário.
- Custo total = área (ha) × custo por hectare.
- Dose por metro de linha = estimativa baseada no espaçamento.

As quantidades são exibidas com quatro casas decimais e os valores monetários com duas.

A indicação "MENOR CUSTO ESTIMADO" representa exclusivamente uma comparação financeira entre produtos da mesma categoria. Não considera eficácia agronômica.

---

## 2. Sistema R — `src/app.R`

Pode ser aberto pela opção **8** do menu Python ou pelo terminal:

```powershell
& "C:\Program Files\R\R-4.5.3\bin\Rscript.exe" src\app.R
```

### Menu do `app.R`

| Opção | Módulo | Descrição |
|-------|--------|-----------|
| 1 | `analise_estatistica.R` | Estatísticas no CSV em `config/` |
| 2 | `clima_meteorologico.R` | Boletim meteorológico (Open-Meteo) |
| 3 | Sair | Volta ao menu Python |

---

## 3. Módulos R (em `src/`)

```powershell
& "C:\Program Files\R\R-4.5.3\bin\Rscript.exe" src\analise_estatistica.R
& "C:\Program Files\R\R-4.5.3\bin\Rscript.exe" src\clima_meteorologico.R
```

---

## R não está no PATH (Windows)

Para disponibilizar o Rscript temporariamente no PowerShell:

```powershell
$env:Path += ";C:\Program Files\R\R-4.5.3\bin"
Rscript --version
```

Essa configuração vale apenas para a sessão atual do PowerShell.
---

## Fluxo resumido

```
python farm.py
  ├─ Opção 5  → exporta config/dados_fazenda.csv
  ├─ Opção 8  → R (src/app.R)
  └─ Opção 9  → sair
```

---

---

## Testes automatizados

O projeto possui 16 testes automatizados, organizados na pasta `tests/`.

- `test_geometria.py`: 9 testes de cálculos geométricos e validação de medidas.
- `test_insumos.py`: 7 testes de conversão de unidades, quantidades, custos e classificação financeira.

### Como executar

Na raiz do repositório, execute:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

**Última validação:** 31/10/2026.

**Resultado:** 16 testes executados, 16 aprovados, nenhuma falha.

Os testes automatizados complementam os testes funcionais realizados nos menus Python e R.

## Referências

- [Open-Meteo API](https://open-meteo.com/)
- [CRAN](https://cran.r-project.org/)
- Enunciado: `document/instruoces-avaliacao-fase1`

## Créditos e contribuições

**Desenvolvimento original — Fase 1**
- Edemir Sufiatti — Desenvolvimento inicial do projeto FarmTech Solutions (18/03/2026).

**Auditoria técnica e evolução do projeto — Outubro/2026**
- Georgia Mendes Rocha — Auditoria do código, implementação de correções, validação dos cálculos geométricos e de insumos, testes de integração Python–R, criação de testes automatizados, revisão da documentação e organização da rastreabilidade.

**Validação técnica**
- 16 testes automatizados aprovados.
- Testes funcionais de CRUD, persistência CSV e integração Python–R realizados.

As alterações estão documentadas em `CHANGELOG.md` e `document/RASTREABILIDADE_F1.md`.
