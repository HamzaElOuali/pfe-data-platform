{% macro clean_string(column_name) %}
    upper(trim(regexp_replace({{ column_name }}, '[^a-zA-Z0-9 ]', '', 'g')))
{% endmacro %}
