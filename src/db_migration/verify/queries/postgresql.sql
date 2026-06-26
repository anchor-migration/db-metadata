-- PostgreSQL verification queries
-- Returns: entity_type, entity_key (must match export key format)

SELECT 'table' AS entity_type, table_schema || '.' || table_name AS entity_key
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND table_type = 'BASE TABLE'

UNION ALL

SELECT 'view', table_schema || '.' || table_name
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND table_type = 'VIEW'

UNION ALL

SELECT 'column', table_schema || '.' || table_name || '.' || column_name
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')

UNION ALL

SELECT 'primary_key',
       tc.table_schema || '.' || tc.table_name || '|' || kcu.column_name || '|' || kcu.ordinal_position
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
  AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')

UNION ALL

SELECT 'foreign_key',
       tc.table_schema || '.' || tc.table_name || '|' || kcu.column_name || '|' ||
       ccu.table_schema || '.' || ccu.table_name || '|' || ccu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name
 AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')

UNION ALL

SELECT 'index', schemaname || '.' || tablename || '|' || indexname
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')

UNION ALL

SELECT 'unique_constraint',
       tc.table_schema || '.' || tc.table_name || '|' ||
       COALESCE(tc.constraint_name, '') || '|' ||
       kcu.column_name || '|' || kcu.ordinal_position
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'UNIQUE'
  AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
