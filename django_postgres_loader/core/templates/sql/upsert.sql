MERGE INTO "{{ model_table_name }}" AS target
USING "{{ temp_table_name }}" AS source
ON {% for col in join_columns %}target."{{ col }}" = source."{{ col }}"{% if not loop.last %} AND {% endif %}{% endfor %}

WHEN MATCHED THEN
    UPDATE SET
        {% for col in non_join_columns %}
        "{{ col }}" = source."{{ col }}"{% if not loop.last %},{% endif %}

        {% endfor %}
WHEN NOT MATCHED THEN
    INSERT ({% for col in all_columns %}"{{ col }}"{% if not loop.last %}, {% endif %}{% endfor %})
    VALUES ({% for col in all_columns %}source."{{ col }}"{% if not loop.last %}, {% endif %}{% endfor %})
;
