# NEROXA — F01 Prova 1 | Gate do fundador (04/11/2026)

**Aprovação especializada independente: não obrigatória.** O fundador `luit77yak-dev` toma a decisão nominal, limitada ao SHA, à tentativa e ao escopo da prova. Esse controle substitui a exigência administrativa de especialista, **não** os controles técnicos nem a evidência de segurança.

## Arquitetura
- Runner: GitHub Actions do repositório de laboratório `luit77yak-dev/neroxa-pg17-security-lab`, sem vínculo Vercel identificado.
- Fonte Master F01 congelada: `0e98cda5dce5e84f7019e6d97d69b1aa1ee6f023`.
- Workflow candidato: `.github/workflows/neroxa-f01-founder.yml` — exclusivamente `workflow_dispatch`; execução autorizada só depois que o workflow estiver na branch padrão do LAB, com `founder_approval=F01_ONE_DISPOSABLE_RUN`, SHA do LAB idêntico a `GITHUB_SHA` e SHA do Master idêntico ao original.
- `github.actor` e `github.triggering_actor` devem ser `luit77yak-dev`; `GITHUB_RUN_ATTEMPT=1`; leitura GitHub para comprovar apenas uma run do workflow; concorrência serial; nenhuma credencial de produção; código Master apenas leitura; sem push/deploy.
- A execução histórica Master demonstra parte do isolamento, mas a Prova 1 focal presente **ainda não executou**.

## Riscos objetivos a aceitar
| Risco | Gravidade | Estado/limite |
|---|---|---|
| SQL em ambiente errado | CRÍTICO | Somente PostgreSQL descartável, sem variáveis/endereços de produção; validar identidade antes de dados |
| Saída indevida de rede | ALTA | GH-LAB-05 prévio teve isolamento de namespace BLOQUEADO; **não há prova suficiente** de isolamento de rede do futuro harness |
| Falso PASS | ALTA | Exigir logs de 15 observações, ator/contexto, mutações e digest; PASS focal não libera F01 completa |
| Execução duplicada | ALTA | Gate de uma run/uma tentativa, sem rerun; conta de runs pode travar após falha parcial (fail-closed) |
| Alteração no código do launcher | ALTA | Main do LAB tem regras de deleção e non-fast-forward, **não** revisão independente obrigatória; congelar SHA do LAB e revisar diff antes da autorização |
| Vazamento de secrets | CRÍTICO | Nenhum segredo real no LAB; GitHub token somente leitura; logs sanitizados; risco residual de código não revisado |
| Falha de limpeza | ALTA | Cleanup no job, mas cancelamento abrupto não comprova cleanup independente; usar runner efêmero, validar ausência de recursos |
| Custo/recursos | MÉDIA | Runner padrão público; preflight exigirá espaço/CPU/RAM atual e custos antes de iniciar serviços; sem upgrade/pagamento |
| F02/SEC18 ainda vulneráveis | ALTA | Nenhuma prova F01 isolada libera tracking público, consumidores legados, SEC18 ou comercial |

## Leituras verificadas
- GitHub histórico F01: `40211924855` e `40212763636`, com contenção Realtime parcial e F01 ainda aberta.
- GH-LAB-05 29/out: ~91,9 GB disco, ~15,8 GB RAM, 4 CPUs; preflight FALHOU/BLOQUEOU na prova de isolamento de rede. Não presumir capacidade atual permanente.
- Branch de LAB main: regras de proteção contra exclusão e non-fast-forward, **sem revisor obrigatório**.
- Vercel do Master está vinculada ao GitHub, por isso o launcher foi isolado em repo separado. Não alterar projeto Vercel.

## Gate para decisão do fundador
1. Revisão estática real do YAML e commit exato do LAB, com confirmação de que não há triggers além de `workflow_dispatch`.
2. Prova suficiente de isolamento/egress ou política explícita de risco residual delimitado, sem acesso a dados/endereços reais; bloquear se risco não puder ser limitado.
3. Confirmar orçamento, preflight, identidade dos 15 testes, origem/digest SQL e fixture A1/A2/C sintética.
4. Aprovação **expressa para uma tentativa**, informando SHA do LAB e SHA do Master; não usar aprovação genérica `ok`.

**Estados atuais:** `LAB_LAUNCHER = DRAFT`, `NATIVE_EXECUTION = NOT_APPROVED`, `F01 = NO_GO`, `F02 = NO_GO`, `SEC18 = BLOCKED`, `COMMERCIAL = NO_GO`. Nenhum merge ou workflow nativo por esta preparação.
