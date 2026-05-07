/*
    Dimension Products : Catalogue enrichi avec traductions et volume.
*/

with products as (
    select * from {{ ref('stg_products') }}
),

translations as (
    select * from {{ ref('stg_category_translation') }}
),

final as (
    select
        p.product_id as product_key,
        p.product_category_name,
        coalesce(t.product_category_name_english, p.product_category_name, 'unknown') as category_name_en,
        p.product_weight_g,
        p.product_length_cm,
        p.product_height_cm,
        p.product_width_cm,
        (p.product_length_cm * p.product_height_cm * p.product_width_cm) as product_volume_cm3
    from products p
    left join translations t on p.product_category_name = t.product_category_name
)

select * from final
