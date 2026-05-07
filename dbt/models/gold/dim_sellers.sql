/*
    Dimension Sellers : Référentiel vendeurs enrichi de la géolocalisation.
*/

with sellers as (
    select * from {{ ref('stg_sellers') }}
),

geo_aggregated as (
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
        s.seller_id as seller_key,
        s.seller_zip_code_prefix,
        coalesce(g.geo_city, s.seller_city) as seller_city,
        coalesce(g.geo_state, s.seller_state) as seller_state,
        g.latitude,
        g.longitude
    from sellers s
    left join geo_aggregated g 
        on s.seller_zip_code_prefix = g.geolocation_zip_code_prefix
)

select * from final
