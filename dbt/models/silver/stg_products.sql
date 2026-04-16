with source as (
    select * from {{ source('bronze', 'products') }}
),

renamed as (
    select
        product_id,
        -- Valeur par défaut pour les catégories
        coalesce(product_category_name, 'unknown') as product_category_name,
        -- Casting des dimensions et poids
        product_name_lenght::integer as product_name_length,
        product_description_lenght::integer as product_description_length,
        product_photos_qty::integer as product_photos_qty,
        product_weight_g::float as product_weight_g,
        product_length_cm::float as product_length_cm,
        product_height_cm::float as product_height_cm,
        product_width_cm::float as product_width_cm,
        _ingested_at,
        _api_version
    from source
    where product_id is not null
)

select * from renamed
{{ deduplicate('product_id') }}
