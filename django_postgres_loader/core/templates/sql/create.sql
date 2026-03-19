CREATE TEMPORARY TABLE "{{ temp_table_name }}" (
    {% for col, dtype in field_definitions %}
    "{{ col }}" {{ dtype }}{% if not loop.last %},{% endif %}

    {% endfor %}
);
