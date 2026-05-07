{{ config(materialized='view') }}

with orders as (
    select * from {{ ref('fct_orders') }}
),
customers as (
    select * from {{ ref('dim_customers') }}
),
dates as (
    select * from {{ ref('dim_date') }}
)

select
    -- Commande
    o.order_key,
    o.order_status,
    
    -- Métriques Logistiques
    o.delivery_days as actual_delivery_days,
    o.is_late as delivery_status_late,
    o.total_order_value,
    
    -- Client (Destination)
    c.customer_city,
    c.customer_state,
    
    -- Temps
    d.date_actual as purchase_date,
    d.month_name as purchase_month,
    d.date_year as purchase_year

from orders o
left join customers c on o.customer_key = c.customer_key
left join dates d on o.date_key = d.date_key
