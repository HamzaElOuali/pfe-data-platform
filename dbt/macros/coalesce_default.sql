{% macro coalesce_default(column_name, default_value="'unknown'") %}
    coalesce({{ column_name }}, {{ default_value }})
{% endmacro %}
