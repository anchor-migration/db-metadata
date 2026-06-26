-- MySQL verification queries (MySQL 5.7+: use CONCAT, not || which is logical OR by default)
-- Returns: entity_type, entity_key

SELECT 'table' AS entity_type, CONCAT(table_schema, '.', table_name) AS entity_key
FROM information_schema.tables
WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
  AND table_type = 'BASE TABLE'

UNION ALL

SELECT 'view', CONCAT(table_schema, '.', table_name)
FROM information_schema.tables
WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
  AND table_type = 'VIEW'

UNION ALL

SELECT 'column', CONCAT(table_schema, '.', table_name, '.', column_name)
FROM information_schema.columns
WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')

UNION ALL

SELECT 'primary_key',
       CONCAT(tc.table_schema, '.', tc.table_name, '|', kcu.column_name, '|', kcu.ordinal_position)
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
 AND tc.table_name = kcu.table_name
WHERE tc.constraint_type = 'PRIMARY KEY'
  AND tc.table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')

UNION ALL

SELECT 'foreign_key',
       CONCAT(
         kcu.table_schema, '.', kcu.table_name, '|', kcu.column_name, '|',
         kcu.referenced_table_schema, '.', kcu.referenced_table_name, '|', kcu.referenced_column_name
       )
FROM information_schema.key_column_usage kcu
WHERE kcu.referenced_table_name IS NOT NULL
  AND kcu.table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')

UNION ALL

SELECT 'index', CONCAT(table_schema, '.', table_name, '|', index_name)
FROM information_schema.statistics
WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
  AND index_name IS NOT NULL
  AND index_name <> 'PRIMARY'
GROUP BY table_schema, table_name, index_name

UNION ALL

SELECT 'unique_constraint',
       CONCAT(
         tc.table_schema, '.', tc.table_name, '|',
         COALESCE(tc.constraint_name, ''), '|',
         kcu.column_name, '|', kcu.ordinal_position
       )
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
 AND tc.table_name = kcu.table_name
WHERE tc.constraint_type = 'UNIQUE'
  AND tc.table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
