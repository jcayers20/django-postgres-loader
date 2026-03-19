COPY "{{ temp_table_name }}" (
    {% for col in columns %}
    "{{ col }}"{% if not loop.last %},{% endif %}

    {% endfor %}
) FROM STDIN WITH CSV HEADER
{% if delimiter %}DELIMITER '{{ delimiter }}'{% endif %}
{% if null_string is not none %}NULL '{{ null_string }}'{% endif %}
{% if quote_character %}QUOTE '{{ quote_character }}'{% endif %}
{% if force_not_null %}FORCE_NOT_NULL ({% for col in force_not_null %}"{{ col }}"{% if not loop.last %}, {% endif %}{% endfor %}){% endif %}
{% if force_null %}FORCE_NULL ({% for col in force_null %}"{{ col }}"{% if not loop.last %}, {% endif %}{% endfor %}){% endif %}
{% if encoding %}ENCODING '{{ encoding }}'{% endif %}
;
