-- Foreign key lineage: upstream (other tables reference this table)
-- Replace 'customers' with target table name

SELECT
    fk.name AS fk_name,
    ds.name AS source_schema,
    st.name AS source_table,
    fk.source_column,
    dt.name AS target_schema,
    tt.name AS target_table,
    fk.target_column
FROM db_foreign_key fk
JOIN db_table st ON st.id = fk.source_table_id
JOIN db_schema ds ON ds.id = st.schema_id
JOIN db_table tt ON tt.id = fk.target_table_id
JOIN db_schema dt ON dt.id = tt.schema_id
WHERE tt.name = 'customers'
  AND tt.export_run_id = (SELECT MAX(id) FROM export_run);
