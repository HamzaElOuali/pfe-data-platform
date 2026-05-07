/*
    Fact Order Items : Grain Article.
    Centre de l'étoile Ventes.
*/

with items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select 
        order_id,
        order_purchase_timestamp
    from {{ ref('stg_orders') }}
),

final as (
    select
        -- Utilisation d'un surrogate key pour l'unicité de la ligne d'article
        {{ dbt_utils.generate_surrogate_key(['items.order_id', 'items.order_item_id']) }} as order_item_key,
        items.order_id as order_key,
        items.order_item_id,
        items.product_id as product_key,
        items.seller_id as seller_key,
        strftime(orders.order_purchase_timestamp, '%Y%m%d')::int as date_key,
        items.price,
        items.freight_value,
        items.total_value as total_item_value
    from items
    left join orders on items.order_id = orders.order_id
)

select * from final
