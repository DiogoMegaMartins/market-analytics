# Sprint 4.1.4 — Business Quality Historical Validation

## Objetivo

Disponibilizar um primeiro instrumento descritivo para estudar avaliações Business Quality aprovadas ao longo do tempo, cobertura por período, estabilidade de pontuação por empresa e consistência de rankings entre períodos.

## Implementação

- `backend/app/services/business_quality/historical_validation.py`
- Entrada explícita de avaliações com empresa, ID, data de referência, score, completude, confiança, versão metodológica e estado de aprovação.
- Exclusão transparente de avaliações não aprovadas e de avaliações sem score/completude inferior ao limiar configurado.
- Histórico por empresa: primeira/última pontuação, variação líquida e variação absoluta média entre observações.
- Consistência cross-sectional entre períodos através de Spearman com ranks médios para empates.
- Comparações de ranking bloqueadas quando as versões metodológicas diferem.
- Deteção de duplicados por empresa/período e validação de intervalos.

## Limites metodológicos

Este sprint não contém observações históricas reais de Microsoft, Coca-Cola, Costco, Caterpillar ou Exxon Mobil. Não foram inventados scores ou dados. O módulo é um harness que recebe avaliações aprovadas e verificáveis.

Os resultados são descritivos e não demonstram capacidade preditiva, alpha, causalidade ou superioridade de investimento. Não calcula retornos nem substitui um backtest point-in-time. A ausência de avaliações, amostras pequenas, diferenças de versão metodológica e alterações de cobertura podem distorcer comparações. A seleção de empresas deve preservar empresas deslistadas/adquiridas e a composição histórica do universo para mitigar survivorship bias.

A comparação de scores ao longo do tempo é deliberadamente omitida por empresa quando existe mistura de versões metodológicas. A correlação de rankings requer pelo menos três empresas comuns e variação não nula nos ranks.

## Validação

Testes unitários cobrem evolução temporal, correlação de rankings, exclusão de avaliações não aprovadas/incompletas, duplicados e incompatibilidade de versões.
