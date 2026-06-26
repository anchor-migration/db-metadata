-- Compare table counts across export runs (schema drift detection)

SELECT
    er.id AS export_run_id,
    er.exported_at,
    er.source_dialect,
    COUNT(t.id) AS table_count
FROM export_run er
LEFT JOIN db_table t ON t.export_run_id = er.id
GROUP BY er.id, er.exported_at, er.source_dialect
ORDER BY er.id;
