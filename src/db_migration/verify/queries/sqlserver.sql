-- SQL Server verification queries
-- Returns: entity_type, entity_key

SELECT 'table' AS entity_type, s.name + '.' + t.name AS entity_key
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE s.name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')

UNION ALL

SELECT 'view', s.name + '.' + v.name
FROM sys.views v
JOIN sys.schemas s ON v.schema_id = s.schema_id
WHERE s.name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')

UNION ALL

SELECT 'column', s.name + '.' + o.name + '.' + c.name
FROM sys.columns c
JOIN sys.objects o ON c.object_id = o.object_id
JOIN sys.schemas s ON o.schema_id = s.schema_id
WHERE o.type IN ('U', 'V')
  AND s.name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')

UNION ALL

SELECT 'primary_key',
       s.name + '.' + t.name + '|' + col.name + '|' + CAST(ic.key_ordinal AS VARCHAR(10))
FROM sys.indexes i
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns col ON ic.object_id = col.object_id AND ic.column_id = col.column_id
JOIN sys.tables t ON i.object_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE i.is_primary_key = 1
  AND s.name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')

UNION ALL

SELECT 'foreign_key',
       ps.name + '.' + pt.name + '|' + pc.name + '|' +
       rs.name + '.' + rt.name + '|' + rc.name
FROM sys.foreign_key_columns fkc
JOIN sys.tables pt ON fkc.parent_object_id = pt.object_id
JOIN sys.schemas ps ON pt.schema_id = ps.schema_id
JOIN sys.columns pc ON fkc.parent_object_id = pc.object_id AND fkc.parent_column_id = pc.column_id
JOIN sys.tables rt ON fkc.referenced_object_id = rt.object_id
JOIN sys.schemas rs ON rt.schema_id = rs.schema_id
JOIN sys.columns rc ON fkc.referenced_object_id = rc.object_id AND fkc.referenced_column_id = rc.column_id
WHERE ps.name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')

UNION ALL

SELECT 'index', s.name + '.' + t.name + '|' + i.name
FROM sys.indexes i
JOIN sys.tables t ON i.object_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE i.is_primary_key = 0
  AND i.is_hypothetical = 0
  AND i.name IS NOT NULL
  AND s.name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')

UNION ALL

SELECT 'unique_constraint',
       s.name + '.' + t.name + '|' +
       COALESCE(i.name, '') + '|' +
       col.name + '|' + CAST(ic.key_ordinal AS VARCHAR(10))
FROM sys.indexes i
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns col ON ic.object_id = col.object_id AND ic.column_id = col.column_id
JOIN sys.tables t ON i.object_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE i.is_unique = 1
  AND i.is_primary_key = 0
  AND s.name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')
