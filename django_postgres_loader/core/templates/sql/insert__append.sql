INSERT INTO "{model_table_name}" (
    {columns}
)
SELECT
    {columns}
FROM
    "{temp_table_name}"
;
