-- Oracle verification queries
-- Returns: entity_type, entity_key

SELECT 'table' AS entity_type, owner || '.' || table_name AS entity_key
FROM all_tables
WHERE owner NOT IN (
    'SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'WMSYS', 'XDB',
    'CTXSYS', 'MDSYS', 'ORDSYS', 'ORDDATA', 'LBACSYS', 'DVSYS',
    'OJVMSYS', 'OLAPSYS', 'SI_INFORMTN_SCHEMA'
)

UNION ALL

SELECT 'view', owner || '.' || view_name
FROM all_views
WHERE owner NOT IN (
    'SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'WMSYS', 'XDB',
    'CTXSYS', 'MDSYS', 'ORDSYS', 'ORDDATA', 'LBACSYS', 'DVSYS',
    'OJVMSYS', 'OLAPSYS', 'SI_INFORMTN_SCHEMA'
)

UNION ALL

SELECT 'column', owner || '.' || table_name || '.' || column_name
FROM all_tab_columns
WHERE owner NOT IN (
    'SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'WMSYS', 'XDB',
    'CTXSYS', 'MDSYS', 'ORDSYS', 'ORDDATA', 'LBACSYS', 'DVSYS',
    'OJVMSYS', 'OLAPSYS', 'SI_INFORMTN_SCHEMA'
)

UNION ALL

SELECT 'primary_key',
       cc.owner || '.' || cc.table_name || '|' || cols.column_name || '|' || cols.position
FROM all_constraints cc
JOIN all_cons_columns cols
  ON cc.owner = cols.owner
 AND cc.constraint_name = cols.constraint_name
WHERE cc.constraint_type = 'P'
  AND cc.owner NOT IN (
    'SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'WMSYS', 'XDB',
    'CTXSYS', 'MDSYS', 'ORDSYS', 'ORDDATA', 'LBACSYS', 'DVSYS',
    'OJVMSYS', 'OLAPSYS', 'SI_INFORMTN_SCHEMA'
)

UNION ALL

SELECT 'foreign_key',
       src.owner || '.' || src.table_name || '|' || src_cols.column_name || '|' ||
       tgt.owner || '.' || tgt.table_name || '|' || tgt_cols.column_name
FROM all_constraints src
JOIN all_cons_columns src_cols
  ON src.owner = src_cols.owner
 AND src.constraint_name = src_cols.constraint_name
JOIN all_constraints tgt
  ON src.r_constraint_name = tgt.constraint_name
 AND src.r_owner = tgt.owner
JOIN all_cons_columns tgt_cols
  ON tgt.owner = tgt_cols.owner
 AND tgt.constraint_name = tgt_cols.constraint_name
 AND src_cols.position = tgt_cols.position
WHERE src.constraint_type = 'R'
  AND src.owner NOT IN (
    'SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'WMSYS', 'XDB',
    'CTXSYS', 'MDSYS', 'ORDSYS', 'ORDDATA', 'LBACSYS', 'DVSYS',
    'OJVMSYS', 'OLAPSYS', 'SI_INFORMTN_SCHEMA'
)

UNION ALL

SELECT 'index', ui.table_owner || '.' || ui.table_name || '|' || ui.index_name
FROM all_indexes ui
WHERE ui.table_owner NOT IN (
    'SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'WMSYS', 'XDB',
    'CTXSYS', 'MDSYS', 'ORDSYS', 'ORDDATA', 'LBACSYS', 'DVSYS',
    'OJVMSYS', 'OLAPSYS', 'SI_INFORMTN_SCHEMA'
)
  AND ui.index_type != 'LOB'

UNION ALL

SELECT 'unique_constraint',
       cc.owner || '.' || cc.table_name || '|' ||
       COALESCE(cc.constraint_name, '') || '|' ||
       cols.column_name || '|' || cols.position
FROM all_constraints cc
JOIN all_cons_columns cols
  ON cc.owner = cols.owner
 AND cc.constraint_name = cols.constraint_name
WHERE cc.constraint_type = 'U'
  AND cc.owner NOT IN (
    'SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'WMSYS', 'XDB',
    'CTXSYS', 'MDSYS', 'ORDSYS', 'ORDDATA', 'LBACSYS', 'DVSYS',
    'OJVMSYS', 'OLAPSYS', 'SI_INFORMTN_SCHEMA'
)
