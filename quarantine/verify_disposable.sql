-- Disposable PostgreSQL only, run after quarantine in SAME isolated stack.
DO $v$
DECLARE n integer;
BEGIN
 SELECT count(*) INTO n FROM pg_class c JOIN pg_namespace s ON s.oid=c.relnamespace
 WHERE s.nspname IN ('public','private') AND c.relkind IN ('r','v');
 IF n <> 34 THEN RAISE EXCEPTION 'EXPECTED_34_RELATIONS_FOUND_%',n; END IF;
 SELECT count(*) INTO n FROM pg_policies WHERE schemaname IN ('public','private');
 IF n <> 99 THEN RAISE EXCEPTION 'EXPECTED_99_POLICIES_FOUND_%',n; END IF;
 SELECT count(*) INTO n FROM pg_proc p JOIN pg_namespace s ON s.oid=p.pronamespace
 WHERE s.nspname IN ('public','private')
 AND (has_function_privilege('anon',p.oid,'EXECUTE') OR has_function_privilege('authenticated',p.oid,'EXECUTE'));
 IF n <> 0 THEN RAISE EXCEPTION 'EXECUTE_OPEN_FUNCTIONS_%',n; END IF;
 SELECT count(*) INTO n FROM pg_class c JOIN pg_namespace s ON s.oid=c.relnamespace
 WHERE s.nspname IN ('public','private') AND c.relkind IN ('r','p','v')
 AND (has_table_privilege('anon',c.oid,'SELECT') OR has_table_privilege('authenticated',c.oid,'SELECT'));
 IF n <> 0 THEN RAISE EXCEPTION 'SELECT_OPEN_RELATIONS_%',n; END IF;
 IF to_regprocedure('public.get_public_order_status(uuid,text)') IS NULL
 OR to_regprocedure('public.append_public_order_items_with_payment(uuid,text,jsonb,text)') IS NULL THEN
  RAISE EXCEPTION 'LEGACY_SIGNATURES_MISSING_UNEXPECTED'; END IF;
 IF has_function_privilege('anon','public.get_public_order_status(uuid,text)','EXECUTE')
 OR has_function_privilege('authenticated','public.get_public_order_status(uuid,text)','EXECUTE')
 OR has_function_privilege('anon','public.append_public_order_items_with_payment(uuid,text,jsonb,text)','EXECUTE')
 OR has_function_privilege('authenticated','public.append_public_order_items_with_payment(uuid,text,jsonb,text)','EXECUTE')
 THEN RAISE EXCEPTION 'LEGACY_RPC_EXECUTE_EXPOSED'; END IF;
END $v$;
SELECT 'PG17_DISPOSABLE_BOOTSTRAP_QUARANTINED_PASS' AS status;
