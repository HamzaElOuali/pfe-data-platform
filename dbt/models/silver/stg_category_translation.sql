with source as (
    select * from {{ source('bronze', 'product_category_name_translation') }}
),

renamed as (
    select
        trim(product_category_name) as product_category_name,
        trim(product_category_name_english) as product_category_name_english,
        _ingested_at,
        _source_file
    from source
    -- Règle de rejet : pas de traduction si les deux colonnes sont vides
    where product_category_name is not null 
       or product_category_name_english is not null
)

select * from renamed
{{ deduplicate('product_category_name') }}
