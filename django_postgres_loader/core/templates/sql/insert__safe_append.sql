INSERT INTO "{model_table_name}" (
    {columns}
)
SELECT
    {columns}
FROM
    "{temp_table_name}"
ON CONFLICT ({conflict_target}) DO NOTHING
;
