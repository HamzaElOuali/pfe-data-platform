/*
    Dimension Customers : Référentiel client enrichi de la géolocalisation.
    Note : On dédoublonne la table geolocation par code postal (AVG) avant la jointure
    pour garantir qu'on conserve exactement 99 441 clients.
*/

with customers as (
    select * from {{ ref('stg_customers') }}
),

geo_aggregated as (
    -- On réduit 1M de lignes géo à ~19k codes postaux uniques
    select
        geolocation_zip_code_prefix,
        avg(geolocation_lat) as latitude,
        avg(geolocation_lng) as longitude,
        any_value(geolocation_city) as geo_city,
        any_value(geolocation_state) as geo_state
    from {{ ref('stg_geolocation') }}
    group by 1
),

final as (
    select
        c.customer_id as customer_key,
        c.customer_unique_id,
        c.customer_zip_code_prefix,
        -- Priorité aux noms de ville normalisés de la table géo
        coalesce(g.geo_city, c.customer_city) as customer_city,
        coalesce(g.geo_state, c.customer_state) as customer_state,
        g.latitude,
        g.longitude
    from customers c
    left join geo_aggregated g 
        on c.customer_zip_code_prefix = g.geolocation_zip_code_prefix
)

select * from final
