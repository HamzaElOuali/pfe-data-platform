{% macro deduplicate(primary_key, order_by='_ingested_at desc') %}
    -- Utilise QUALIFY de DuckDB pour filtrer les doublons sur place
    qualify row_number() over (partition by {{ primary_key }} order by {{ order_by }}) = 1
{% endmacro %}
