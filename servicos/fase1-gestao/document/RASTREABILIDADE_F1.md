# FarmTech Solutions — Matriz de Rastreabilidade da Fase 1

**Data da auditoria:** 31/10/2026  
**Situação:** Auditoria e correções locais, ainda sem lançamento de nova versão.

## Responsabilidades e contribuições

**Desenvolvimento original — Fase 1**
- Edemir Sufiatti — Implementação inicial do sistema.

**Auditoria e evolução técnica — Outubro/2026**
- Georgia Mendes Rocha — Revisão e correção do código Python e R, execução de testes funcionais, validação matemática, implementação de testes automatizados, revisão documental e organização da rastreabilidade.

**Evidências da contribuição**
- Correções identificadas pelos registros F1-01 a F1-13.
- 16 testes automatizados aprovados.
- Histórico técnico documentado no `CHANGELOG.md`.

**Observação:** a autoria dos commits será registrada separadamente no Git.

## Registro de auditoria

| ID | Item auditado | Correção ou verificação | Evidência | Situação |
|---|---|---|---|---|
| F1-01 | Cálculos geométricos | Fórmulas para polígonos regulares de 5 a 8 lados e validação das medidas | Testes manuais e 9 testes automatizados | Aprovado |
| F1-02 | Entradas numéricas | Aceitação de ponto e vírgula decimal nas medidas | Cadastro com 10,5 m | Aprovado no cenário testado |
| F1-03 | Linhas de plantio e insumos | Totais calculados pela área; precisão decimal; extensão linear teórica | Saída Python e CSV de insumos | Parcial — linhas estimadas |
| F1-04 | Persistência CSV | Inclusão de `lados` e `medidas` na exportação/importação | CSV inspecionado e recuperação testada | Aprovado |
| F1-05 | Scripts R | Análise estatística, meteorologia e correção do caminho em `app.R` | Execuções no PowerShell | Aprovado |
| F1-06 | CRUD | Inserção, listagem, atualização, exclusão e cancelamento | Testes pelo menu Python | Aprovado |
| F1-07 | Comparação de insumos | Precisão das quantidades e classificação como menor custo estimado | Opções 6 e 7 testadas | Aprovado |
| F1-08 | README | Atualização dos comandos, fórmulas e estrutura | Revisão documental | Em andamento |
| F1-09 | Unidades | Conversão de kg/ha para g/m e de L/ha para mL/m | Testes automatizados | Aprovado |
| F1-10 | Meteorologia | Consulta Open-Meteo e geocodificação de Irecê–BA | Execução do módulo meteorológico | Aprovado |
| F1-11 | Regressão | Criação de `test_geometria.py` e `test_insumos.py` | 16 testes executados; resultado OK | Aprovado |
| F1-12 | Integração final | Python, R, CSV, estrutura de pastas e `.gitignore` | Testes funcionais e inspeção do repositório | Parcial — Git pendente |
| F1-13 | Evidências e rastreabilidade | Registro de correções, testes e histórico | `CHANGELOG.md` e esta matriz | Em andamento |

## Limitações conhecidas

1. As linhas de plantio são estimativas, não uma representação geométrica exata do terreno.
2. A comparação dos produtos considera o custo estimado, não a eficácia agronômica.
3. A execução automatizada ainda não cobre todas as funcionalidades do CRUD e da integração com R.

## Evidências principais

- Testes automatizados: `python -m unittest discover -s tests -p "test_*.py" -v`
- Resultado registrado: 16 testes aprovados.
- Persistência: `config/dados_fazenda.csv`
- Cálculos de insumos: `config/insumos_por_talhao.csv`
- Scripts R: `src/analise_estatistica.R`, `src/clima_meteorologico.R` e `src/app.R`
- Histórico de correções: `CHANGELOG.md`

## Pendências antes do encerramento

- Documentar no README os testes automatizados e os registros de rastreabilidade.
- Verificar o estado do Git.
- Revisar as alterações antes de criar commits.
- Concluir a auditoria final e registrar as evidências da versão revisada.
