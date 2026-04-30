with source as (
    select * from {{ source('bronze', 'order_reviews') }}
),

renamed as (
    select
        review_id,
        order_id,
        review_score::integer as review_score,
        -- Commentaires (Démasqués pour analyse NLP future)
        trim(review_comment_title) as review_comment_title,
        trim(review_comment_message) as review_comment_message,
        -- Flag pour savoir si un commentaire textuel existe
        (review_comment_message is not null and len(trim(review_comment_message)) > 0) as has_comment,
        -- Casting dates
        review_creation_date::timestamp as review_creation_date,
        review_answer_timestamp::timestamp as review_answer_timestamp,
        _ingested_at,
        _batch_id
    from source
    where review_id is not null
      and review_score::integer between 1 and 5
),

derived as (
    select
        *,
        -- Calcul du délai de réponse en heures
        date_diff('hour', review_creation_date, review_answer_timestamp) as response_hours
    from renamed
)

select * from derived
{{ deduplicate('review_id') }}
