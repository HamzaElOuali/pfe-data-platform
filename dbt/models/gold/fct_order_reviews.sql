/*
    Fact Order Reviews : Grain Avis.
    Centre de l'étoile Satisfaction (Layer 2).
*/

with reviews as (
    select * from {{ ref('stg_order_reviews') }}
),

orders as (
    select 
        order_id,
        order_purchase_timestamp
    from {{ ref('stg_orders') }}
),

final as (
    select
        r.review_id as review_key,
        r.order_id as order_key,
        strftime(o.order_purchase_timestamp, '%Y%m%d')::int as date_key,
        r.review_score,
        r.has_comment,
        r.review_creation_date,
        r.review_answer_timestamp,
        date_diff('hour', r.review_creation_date, r.review_answer_timestamp) as response_hours
    from reviews r
    left join orders o on r.order_id = o.order_id
)

select * from final
