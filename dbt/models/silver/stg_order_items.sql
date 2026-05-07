with source as (
    select * from {{ source('bronze', 'order_items') }}
),

renamed as (
    select
        order_id,
        order_item_id::integer as order_item_id,
        product_id,
        sha256(seller_id) as seller_id,
        shipping_limit_date::timestamp as shipping_limit_date,
        price::float as price,
        freight_value::float as freight_value,
        -- Calcul de la valeur totale
        (price::float + freight_value::float) as total_value,
        _ingested_at,
        _batch_id
    from source
    where order_id is not null
      and product_id is not null
      -- Règle métier : prix et fret doivent être positifs
      and price::float >= 0
      and freight_value::float >= 0
)

select * from renamed
{{ deduplicate('order_id || order_item_id') }}
