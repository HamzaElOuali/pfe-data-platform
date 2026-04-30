with source as (
    select * from {{ source('bronze', 'products') }}
),

renamed as (
    select
        product_id,
        -- Utilisation des macros pour la normalisation
        {{ clean_string('product_category_name') }} as product_category_name,
        {{ coalesce_default('product_category_name', "'UNKNOWN'") }} as product_category_name_final,
        
        -- Casting et gestion des nulls pour les dimensions
        coalesce(product_name_lenght::integer, 0) as product_name_length,
        coalesce(product_description_lenght::integer, 0) as product_description_length,
        coalesce(product_photos_qty::integer, 0) as product_photos_qty,
        
        -- Imputation par défaut pour le poids et dimensions (évite les calculs impossibles plus tard)
        coalesce(product_weight_g::float, 0) as product_weight_g,
        coalesce(product_length_cm::float, 0) as product_length_cm,
        coalesce(product_height_cm::float, 0) as product_height_cm,
        coalesce(product_width_cm::float, 0) as product_width_cm,
        
        _ingested_at,
        _api_version
    from source
    where product_id is not null
)

select * from renamed
{{ deduplicate('product_id') }}
