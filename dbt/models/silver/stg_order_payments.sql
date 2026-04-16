with source as (
    select * from {{ source('bronze', 'order_payments') }}
),

renamed as (
    select
        order_id,
        payment_sequential::integer as payment_sequential,
        -- Normalisation du type de paiement
        lower(trim(payment_type)) as payment_type,
        payment_installments::integer as payment_installments,
        payment_value::float as payment_value,
        _ingested_at,
        _batch_id
    from source
    where order_id is not null
      -- Règle métier : valeur positive
      and payment_value::float >= 0
)

select * from renamed
{{ deduplicate('order_id || payment_sequential') }}
