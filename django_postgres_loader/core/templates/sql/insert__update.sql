WITH update_data AS (
    SELECT
        "{temp_table_name}".*
    FROM
        "{temp_table_name}"
        INNER JOIN "{model_table_name}" ON
            {update_join_conditions}
)

INSERT INTO "{model_table_name}" (
    {columns}
)
SELECT
    {columns}
FROM
    update_data
ON CONFLICT ({conflict_target}) DO UPDATE SET
    {update_operations}
;
