/*
    Fact Orders : Grain Commande.
    Centre de l'étoile Logistique (Layer 1).
*/

with orders as (
    select * from {{ ref('stg_orders') }}
),

payments as (
    select 
        order_id,
        sum(payment_value) as total_payment_value
    from {{ ref('stg_order_payments') }}
    group by 1
),

items as (
    select 
        order_id,
        sum(price) as total_price,
        sum(freight_value) as total_freight
    from {{ ref('stg_order_items') }}
    group by 1
),

final as (
    select
        o.order_id as order_key,
        o.customer_id as customer_key,
        strftime(o.order_purchase_timestamp, '%Y%m%d')::int as date_key,
        o.order_status,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        coalesce(i.total_price, 0) as total_items_price,
        coalesce(i.total_freight, 0) as total_freight,
        coalesce(p.total_payment_value, 0) as total_order_value,
        o.delivery_days,
        o.is_late
    from orders o
    left join payments p on o.order_id = p.order_id
    left join items i on o.order_id = i.order_id
)

select * from final
