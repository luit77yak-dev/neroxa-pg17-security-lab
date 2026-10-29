# GH-LAB-05 — GitHub-hosted runner preflight (candidate, inactive)

## Scope and disposition

This is a static candidate for `luit77yak-dev/neroxa-pg17-security-lab`, based on the supplied administrative snapshot: `main` `9960eae76d1a58f3f96746e5fb6e3d72ad280d2f`, active ruleset ID `26091943`, and GitHub Actions disabled. It is not published and is not an active workflow. No Actions setting was changed; no workflow, PostgreSQL, Docker, or SQL was run here.

The proposed workflow is manual-only, restricted at runtime to `workflow_dispatch` on `refs/heads/main`, has one job on `ubuntu-24.04`, a 10-minute job timeout, no external Actions, no checkout, no secrets, and `contents: none` at workflow and job level; GitHub defines unspecified token scopes as `none` when a permission is specified. The concurrency group serializes matching runs but is **not** a one-time-use guarantee. A future run requires separate explicit authorization and a fresh preflight of repository state and history.

**This only checks runner viability. It does not initialize PostgreSQL, install packages, run SQL, or establish F01/F02/SEC-18. Lab readiness remains BLOCKED pending later authorization and a post-initialization disk check.**

## Frozen resource contract and runner profile

PG-NATIVE contract floors carried forward: at least 2 effective CPUs, at least 1 GiB available memory, at least 4 GiB free before preparation, and at least 3 GiB free after initialization. GitHub documents `ubuntu-24.04` standard runners as 4 CPUs/16 GB/14 GB SSD for public repositories and 2 CPUs/8 GB/14 GB SSD for private repositories. Both nominal CPU profiles meet the floor, but nominal disk is not actual free space and host RAM is not the job's cgroup availability. The workflow measures effective CPU, cgroup/host available memory, and free space on `/` and `RUNNER_TEMP` when it runs. It measures ≥3 GiB at the end of the preflight only; **that cannot substitute for ≥3 GiB after PostgreSQL initialization**, which this workflow deliberately does not perform.

Cost is not verified: GitHub says standard hosted runners are free and unlimited for public repositories; private repositories consume the account's included minutes and may incur per-minute charges after the allowance. The repository's current visibility, remaining allowance, and billing cutoff were not rechecked in this static mission. Before any dispatch, the founder must confirm a zero-incremental-cost path; otherwise BLOCKED. No run has consumed minutes.

## PostgreSQL 17 source and integrity procedure

The source lock pins PostgreSQL 17.11 to the official PostgreSQL source archive and SHA-256. A separately authorized future installation procedure must:

1. Fetch only the exact archive URL in `postgresql17-source-lock.json` over HTTPS.
2. Verify the archive against the pinned SHA-256 before extraction; fail closed on any mismatch or missing checksum tool.
3. Build/install into a fresh run-scoped directory, never the system PostgreSQL or a hosted Supabase endpoint.
4. Verify `postgres --version` exactly reports 17.11, record the archive digest and binary identity, then initialize only a disposable cluster with a private Unix socket and no TCP listener.
5. Measure free space again after initialization and require ≥3 GiB. A failure blocks the lab; it must not trigger a smaller database, cleanup bypass, or retry.

No archive is downloaded or verified and no PostgreSQL binary is installed by this candidate. Source provenance and digest are pinned for a later, separately authorized step. No frozen SQL or fixture is included in this preflight package.

## Proposed runtime checks

The inline probe checks repository/ref/event, first-attempt context, hosted Linux x64 identity and `/etc/os-release`, effective CPU and memory, free disk, expected runner utilities, and whether credential-like **environment names** are present (names are redacted; values are never expanded or logged). It requires readable cgroup-v2 CPU and memory controls; unknown cgroup limits fail closed. CPU, memory, disk and temporary-path checks must all pass before the run-specific directory is created; blocked or failed gates stop before any directory creation or privileged isolation probe. It then starts a bounded network namespace probe using `sudo -n unshare --net`, drops to numeric UID/GID 65534 with cleared groups/capabilities and `no_new_privs`, verifies a distinct network namespace with only loopback and no IPv4/IPv6 routes, and binds a Unix socket in a mode-0700 private directory. The probe reports only fixed status tokens. Any missing tool, permission denial, unexpected identity, insufficient resource, interface/route, capability, credential-like name, timeout, or cleanup failure exits nonzero.

Privilege boundary: `sudo`/`unshare` intentionally uses elevated runner privileges to create the isolated network namespace and provision the private socket directory. `setpriv` then drops the **test process** to UID/GID 65534 with no supplementary groups, no capabilities, and `no_new_privs`. This is not an unprivileged end-to-end operation: the workflow shell, resource checks, namespace setup, and cleanup are outside that reduced-privilege test process; selected setup/cleanup commands invoke `sudo`.

The job uses no `GITHUB_TOKEN` expression, no `id-token` permission, no `uses:` actions, and no service containers. Empty token permissions limit repository API authority; they do not prove that the runner host contains no platform-internal runtime material. The workflow's shell starts with `BASH_ENV=/dev/null`, `ENV=/dev/null`, and `bash --noprofile --norc`; the probe then uses `env -i` with an explicit non-secret metadata allowlist. The runner's own bootstrap occurs before workflow shell code and is outside this candidate's control.

## Cleanup model and limits

The network namespace is process-scoped and disappears when its process exits. A final `if: always()` step removes only the validated run-specific directory beneath `RUNNER_TEMP` and checks that it is absent. Cleanup is auditable in the job log, not by an independent external observer. A hard VM termination or platform cancellation can prevent the final step; ephemeral VM teardown is platform behavior, not proof from this script. There is no PostgreSQL service or persistent cluster to clean in this preflight.

## Decision criteria

- **PASS (preflight only):** every runtime check prints `PASS`, the cleanup audit prints `CLEANUP=PASS`, and the observed run is the authorized manual run on the expected repository/ref/runner. It does not authorize PostgreSQL installation or SQL.
- **FAIL:** a measured contradiction exists, such as wrong repository/ref/event, credential-like variable name, below-floor resources, unexpected interface/route, UID/capability violation, or incorrect socket mode. Stop; no retry in the same authorization.
- **BLOCKED:** a required fact cannot be measured, a required tool/cgroup control is missing, `sudo`/`unshare` is unavailable, a probe times out, or cleanup cannot be proven. Do not infer PASS and do not continue to database initialization.

## Static risk matrix

| Control | Candidate evidence | State before a future run | Residual / acceptance rule |
|---|---|---|---|
| Actions inactive | File kept outside `.github/workflows`; administrative snapshot says Actions disabled | PASS (static boundary) | No publication or re-enabling in this mission |
| Trigger and runner | `workflow_dispatch`, main-only guard, `ubuntu-24.04`, 10 min | PASS (static) | Runtime event/ref/runner identity must also pass |
| Permissions/dependencies | `contents: none` at workflow/job; no `uses`, checkout, services, secrets, install | PASS (static) | Repo/org policy and runner internals remain external |
| CPU and memory | cgroup-aware probe, floors 2 CPU / 1 GiB | BLOCKED (not executed) | Current VM values must meet floors |
| Disk | Pre-probe ≥4 GiB; post-probe ≥3 GiB | BLOCKED (not executed) | Post-PostgreSQL-init ≥3 GiB remains a later required check |
| PostgreSQL 17 integrity | Official 17.11 URL and SHA-256 lock | PASS (documented source lock) | Download/build/version not performed; later verification required |
| Cost | Standard runner selected; Actions currently reported disabled | BLOCKED (not checked live) | Repository visibility, included balance, and overage/budget behavior must be confirmed before any run |
| Network boundary | Probe checks new netns, loopback-only, empty IPv4/IPv6 routes | BLOCKED (not executed) | Hosted kernel must permit unshare; no egress proof until runtime probe |
| Test UID/capabilities | `setpriv` target UID/GID 65534, cleared groups/caps, no-new-privs | BLOCKED (not executed) | `/proc` values must demonstrate zero effective/permitted caps |
| Unix socket | Private directory, umask 0177, socket mode 0600 | BLOCKED (not executed) | Runtime bind and cleanup must pass |
| Credentials | No secret references; empty token scopes; name-only classifier | PASS (static design) | Inherited runner internals and org injection are not proven absent; any matching name blocks, values never logged |
| Cleanup | `if: always()` step, exact temp-child check, residue audit | PASS (static design) | Abrupt cancellation/VM loss cannot be attested by same-job cleanup |
| SQL/service safety | No SQL, PostgreSQL start/init, Docker, or service commands | PASS (static) | This is not ACL evidence or product homologation |

## Future execution procedure (requires a separate decision)

1. Confirm Actions is intentionally enabled for this isolated repository, branch protection/ruleset remains active, current `main` is the reviewed candidate, no unapproved secrets or variables are attached, and no prior diagnostic run exists. Do not use another repository or a non-main ref.
2. Review the candidate workflow and its hashes, then obtain explicit authorization for one manual `workflow_dispatch` run. Never use rerun/retry to bypass a failure.
3. Inspect the run's ref/SHA, event, attempt, runner image metadata, resource readings, namespace/socket/UID/capability statuses, and cleanup result. Any critical failure is FAIL/BLOCKED and stops there.
4. Do not interpret a successful preflight as PostgreSQL readiness. A later, separate authorization must cover the pinned PostgreSQL 17.11 download/build/initialization, the ≥3 GiB post-init check, and any SQL test. No SQL execution is included in this candidate.

## Static checks

The package test suite checks the workflow's manual-only/no-action/no-service boundaries, embedded Python syntax, resource thresholds, source lock and credential non-disclosure shape. YAML syntax was separately parsed during preparation; that parser is not a workflow dependency. Tests use synthetic inputs only. They do not run the probe, invoke `sudo`/`unshare`, contact a service, install anything, or execute SQL.

## Official references

- [GitHub-hosted runner profiles and billing distinction](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [GitHub Actions workflow syntax and `GITHUB_TOKEN` permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [PostgreSQL 17.11 release notes](https://www.postgresql.org/docs/release/17.11/)
- [Official PostgreSQL 17.11 source archive](https://ftp.postgresql.org/pub/source/v17.11/postgresql-17.11.tar.bz2)
- [Official PostgreSQL 17.11 SHA-256 file](https://ftp.postgresql.org/pub/source/v17.11/postgresql-17.11.tar.bz2.sha256)
