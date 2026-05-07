{{ config(materialized='view') }}

with reviews as (
    select * from {{ ref('fct_order_reviews') }}
),
orders as (
    select * from {{ ref('fct_orders') }}
),
customers as (
    select * from {{ ref('dim_customers') }}
)

select
    -- Review
    r.review_key,
    r.review_score,
    r.has_comment,
    
    -- Commande liée (pour voir si c'était en retard)
    o.order_status,
    o.delivery_days,
    o.is_late as was_delivered_late,
    
    -- Client
    c.customer_city,
    c.customer_state

from reviews r
left join orders o on r.order_key = o.order_key
left join customers c on o.customer_key = c.customer_key
