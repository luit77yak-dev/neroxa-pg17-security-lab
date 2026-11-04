# NEROXA — Bootstrap em quarentena V3 (03/11/2026)

Ensaio único em GitHub Actions **público**, no repositório de laboratório não conectado à Vercel.

- Base: Master PR #51, SHA `b8a2087ad96dde4f90c04a7c10c31281d663e9f8`.
- Catálogo histórico: SHA256 `e7ed111d73ec8d63b514db8c39059d6b87ae97be74d54e0d682d38bc0e4cf858`.
- Supabase remoto `nvbmzdgfretwnkdfqcap`: referência nominal somente; **não conectar, não gravar**.
- Reconstrói a captura do Master offline; **não publica** migração.
- Retira comandos históricos de default grants e insere REVOKE sobre todos os objetos capturados, na mesma transação.
- Antes de serviços, aplica preflight conservador do Master: 28 GiB livres, 6 GiB RAM, Docker não-vfs e executor público.
- Em Supabase PG17 local sem link, tenta instalação somente da quarentena com provas negativas de EXECUTE e SELECT, duas RPCs por telefone bloqueadas.
- Os 33 SQLs da PR #51 passam por verificação de hashes e ordem **sem instalação**.
- Não corrige P0 histórico F01 nem demonstra que consumidores F02 externos estão desativados.
- Zero segredos e dados reais; não executar uma segunda vez sem nova deliberação.
- Limpeza dos containers e rede específicos do run obrigatória; não há upload de artefatos.

**NO-GO hospedado** independentemente do resultado deste ensaio.