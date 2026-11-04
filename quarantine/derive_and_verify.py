#!/usr/bin/env python3
"""Offline derivation for ONE disposable PG17 rehearsal. NEVER hosted SQL."""
import hashlib, json, pathlib, subprocess, sys
M=pathlib.Path(sys.argv[1]).resolve()
O=pathlib.Path(sys.argv[2]).resolve()
PIN='b8a2087ad96dde4f90c04a7c10c31281d663e9f8'
CAT_SHA='e7ed111d73ec8d63b514db8c39059d6b87ae97be74d54e0d682d38bc0e4cf858'
FILES={
 'audits/ab-auth/master-catalog-20261009.json':'784e39fe61d4fa7e0a93545c9ca59e6f7f6f2595',
 'audits/ab-auth/source.json':'760b0f0de11f942763c42349b8380938eb0b5c0b',
 'tools/ab-auth/build_schema.py':'8252ed7787b2b699f272e0715b621bc24713b037'}
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(M),*args],text=True).strip()
assert git('rev-parse','HEAD')==PIN,'BLOCKED: wrong Master source commit'
for rel,expected in FILES.items():
 p=M/rel
 assert p.is_file() and not p.is_symlink(), 'BLOCKED: source not regular file '+rel
 assert git('hash-object',rel)==expected, 'BLOCKED: wrong blob '+rel
catpath=M/'audits/ab-auth/master-catalog-20261009.json'
raw=catpath.read_bytes()
assert sha(raw)==CAT_SHA,'BLOCKED: wrong catalog digest'
src=json.loads((M/'audits/ab-auth/source.json').read_text())
assert src['sha256']==CAT_SHA,'BLOCKED: wrong catalog witness'
j=json.loads(raw)
for name,n in {'relations':34,'functions':50,'policies':99,'columns':438,'types':10,'triggers':22}.items():
 assert len(j[name])==n, 'BLOCKED: unexpected catalog '+name
signatures={(x['name'],x['signature']) for x in j['functions']}
legacy={('get_public_order_status','p_order_id uuid, p_customer_phone text'),
 ('append_public_order_items_with_payment','p_order_id uuid, p_customer_phone text, p_items jsonb, p_payment_method text')}
assert legacy.issubset(signatures),'BLOCKED: legacy overload drift'
assert sum(r['kind']=='r' for r in j['relations'])==33
assert all(r['rls'] for r in j['relations'] if r['kind']=='r')
assert all('security_invoker=true' in r.get('options',[]) for r in j['relations'] if r['kind']=='v')
man=json.loads((M/'audits/02a5/hosted-release/MANIFEST.json').read_text())
assert man.get('target_project')=='iefaoaqzltvpfabyeelj','BLOCKED: changed historical release identity'
units=man['units']
assert len(units)==33,'BLOCKED: wrong number of hosted source units'
assert [u['order'] for u in units]==list(range(1,34))
for u in units:
 p=M/u['path']
 assert p.is_file() and sha(p.read_bytes())==u['sha256'], 'BLOCKED: hosted unit drift'
assert units[19]['source_sha256']=='648fcca5bdac67ba3879c0804189b204a53fc4f3b136646407b659ca5a62f23c','BLOCKED: P0 lineage unexpected'
O.mkdir(parents=True,exist_ok=False)
historical=O/'historical.inert.sql'
subprocess.run([sys.executable,str(M/'tools/ab-auth/build_schema.py'),str(historical)],cwd=M,check=True,
 stdout=subprocess.DEVNULL,timeout=60)
lines=historical.read_text().splitlines()
assert lines[0].strip()=='BEGIN;' and lines[-1].strip()=='COMMIT;','BLOCKED: outer transaction'
assert sum(x.strip()=='BEGIN;' for x in lines)==1 and sum(x.strip()=='COMMIT;' for x in lines)==1
filtered=[]; skipped=[]
for line in lines[:-1]:
 if line.lstrip().upper().startswith('ALTER DEFAULT PRIVILEGES '):
  skipped.append(sha(line.encode()));continue
 filtered.append(line)
Q="""
-- QUARANTINE ONLY. No hosted execution authorization.
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public, private FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public, private FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public, private FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL PRIVILEGES ON SCHEMA private FROM PUBLIC, anon, authenticated, service_role;
REVOKE CREATE ON SCHEMA public FROM PUBLIC, anon, authenticated;
DO $neroxa_check$
DECLARE bad integer;
BEGIN
 SELECT count(*) INTO bad FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname IN ('public','private')
 AND (has_function_privilege('anon',p.oid,'EXECUTE') OR has_function_privilege('authenticated',p.oid,'EXECUTE'));
 IF bad<>0 THEN RAISE EXCEPTION 'FUNCTION_GRANT_NOT_QUARANTINED: %',bad; END IF;
 SELECT count(*) INTO bad FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('public','private') AND c.relkind IN ('r','p','v','m','f')
 AND (has_table_privilege('anon',c.oid,'SELECT') OR has_table_privilege('authenticated',c.oid,'SELECT')
 OR has_table_privilege('anon',c.oid,'INSERT') OR has_table_privilege('authenticated',c.oid,'INSERT')
 OR has_table_privilege('anon',c.oid,'UPDATE') OR has_table_privilege('authenticated',c.oid,'UPDATE')
 OR has_table_privilege('anon',c.oid,'DELETE') OR has_table_privilege('authenticated',c.oid,'DELETE'));
 IF bad<>0 THEN RAISE EXCEPTION 'TABLE_GRANT_NOT_QUARANTINED: %',bad; END IF;
END $neroxa_check$;
"""
sql='-- INERT LOCAL CANDIDATE, NO HOSTED INSTALL\n'+'\n'.join(filtered)+'\n'+Q+'\nCOMMIT;\n'
assert all(not s.lstrip().upper().startswith('ALTER DEFAULT PRIVILEGES ') for s in sql.splitlines())
out=O/'BOOTSTRAP-QUARANTINED.NAO-APLICAR.sql'
out.write_text(sql)
report={'status':'STATIC_READY_NATIVE_NOT_YET_EXECUTED','master_sha':PIN,
 'historic_catalog_sha256':CAT_SHA,'quarantine_sql_sha256':sha(out.read_bytes()),
 'omitted_defaults':len(skipped),'units_51_hash_verified':33,
 'units_51_applied':0,'historic_P0_source_still_blocked':True,
 'hosted_target':'nvbmzdgfretwnkdfqcap','hosted_writes':0}
(O/'proof.json').write_text(json.dumps(report,indent=2)+'\n')
historical.unlink()
print('STATIC_DERIVATION='+json.dumps(report,sort_keys=True))
