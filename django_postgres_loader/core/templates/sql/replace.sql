INSERT INTO "{{ model_table_name }}" (
    {% for col in columns %}
    "{{ col }}"{% if not loop.last %},{% endif %}

    {% endfor %}
)
SELECT
    {% for col in columns %}
    "{{ col }}"{% if not loop.last %},{% endif %}

    {% endfor %}
FROM
    "{{ temp_table_name }}"
;
