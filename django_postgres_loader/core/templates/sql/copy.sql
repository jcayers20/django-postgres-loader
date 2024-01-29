COPY "{temp_table_name}" (
    {columns}
)
FROM STDIN
WITH CSV HEADER
    {header_options}
;
