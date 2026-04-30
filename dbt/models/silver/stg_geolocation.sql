with source as (
    select * from {{ source('bronze', 'geolocation') }}
),

renamed as (
    select
        geolocation_zip_code_prefix::integer as geolocation_zip_code_prefix,
        -- Formatage propre du code postal (5 chiffres)
        lpad(geolocation_zip_code_prefix::text, 5, '0') as zip_code_formatted,
        geolocation_lat::float as geolocation_lat,
        geolocation_lng::float as geolocation_lng,
        -- Utilisation de la macro de nettoyage standard
        {{ clean_string('geolocation_city') }} as geolocation_city,
        {{ clean_string('geolocation_state') }} as geolocation_state,
        _ingested_at,
        _source_file
    from source
    where geolocation_zip_code_prefix is not null
      -- Règle métier : Frontières du Brésil
      and geolocation_lat::float between -35 and 5
      and geolocation_lng::float between -75 and -34
)

select * from renamed
{{ deduplicate('geolocation_zip_code_prefix') }}
