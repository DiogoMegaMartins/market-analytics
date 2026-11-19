# Sprint 4.1.0 — Business Quality Engine v1

## Entrega

Implementado um motor determinístico e puro para avaliar Business Quality com cinco dimensões: Business Model Quality, Revenue Quality, Competitive Moat, Financial Resilience e Management & Capital Allocation. O motor recebe observações fornecidas por analista, cada uma com pontuação 0–100, referência de evidência, fundamentação e nível de confiança.

## Regras metodológicas

- Versão do motor: `business-quality-v1.0.0`.
- Pesos da rubrica são hipóteses iniciais, não calibradas nem validadas empiricamente.
- Cada dimensão tem critérios obrigatórios e opcionais. Critérios opcionais em falta reduzem a completude, mas não substituem nem penalizam a pontuação.
- A falta de qualquer critério obrigatório torna a dimensão `INSUFFICIENT_DATA`; não é atribuída pontuação zero.
- A pontuação global só existe quando as cinco dimensões podem ser calculadas. Não há redistribuição silenciosa de pesos entre dimensões.
- A confiança é independente da pontuação; a completude é a percentagem ponderada de critérios observados.
- Business Quality não incorpora preço, múltiplos, margem de segurança ou valor intrínseco.
- O motor não infere moat, qualidade da gestão ou qualidade de receita a partir de métricas financeiras isoladas. Exige evidência e fundamentação explícitas.

## Limites desta versão

Esta entrega implementa o catálogo e o cálculo determinístico, com testes unitários. Ainda não inclui persistência de avaliações, API de submissão, interface de revisão, workflow de aprovação, integração automática de evidência nem calibração por setor. As observações são entradas analíticas e não factos automaticamente verificados. A rubrica precisa de validação histórica, análise de sensibilidade e revisão setorial antes de uso decisório.
