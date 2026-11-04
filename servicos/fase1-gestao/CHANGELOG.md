# Histórico de alterações — FarmTech Solutions

## Em auditoria — 31/10/2026
Status: alterações locais, ainda não publicadas como nova versão.

**Responsável pela auditoria e evolução técnica:** Georgia Mendes Rocha.

**Desenvolvimento original:** Edemir Sufiatti.

**Período da auditoria:** outubro de 2026.

### Correções e melhorias
- F1-01: correção das áreas de polígonos regulares de 5 a 8 lados.
- F1-02: aceitação de vírgula e ponto nas medidas decimais.
- F1-03: correção dos totais de insumos pela área do talhão e melhoria da precisão decimal.
- F1-04: preservação dos lados e das medidas originais na exportação e importação CSV.
- F1-05: correção do caminho dos módulos R no app.R.
- F1-07: substituição de "melhor custo-benefício" por "menor custo estimado".
- F1-09: correção da conversão de kg/ha para g/m.
- F1-11: criação dos testes automatizados de geometria e insumos.
- F1-08/F1-12: atualização da documentação e da estrutura do repositório.

### Validações
- CRUD: operações testadas.
- Persistência CSV: exportação e recuperação testadas.
- Integração Python–R: testada.
- Consultas meteorológicas: testadas.
- Testes automatizados: 16 executados, 16 aprovados.

### Limitações conhecidas
- A distribuição física das linhas de plantio permanece aproximada.
- A comparação financeira não avalia eficácia agronômica.

### Pendências
- Finalizar a auditoria de integração e documentação.
- Criar a matriz de rastreabilidade.
- Revisar o estado do Git antes de registrar os commits.
