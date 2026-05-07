/*
    Dimension Date : Calendrier analytique couvrant la période 2016-2019.
*/

with date_series as (
    select 
        generate_series::date as date_day
    from generate_series(date '2016-01-01', date '2019-12-31', interval 1 day)
),

final as (
    select
        strftime(date_day, '%Y%m%d')::int as date_key,
        date_day as date_actual,
        extract('year' from date_day) as date_year,
        extract('month' from date_day) as date_month,
        strftime(date_day, '%B') as month_name,
        extract('day' from date_day) as date_day_of_month,
        extract('dayofweek' from date_day) as date_day_of_week,
        strftime(date_day, '%A') as day_name,
        extract('quarter' from date_day) as date_quarter,
        (extract('dayofweek' from date_day) in (0, 6)) as is_weekend,
        strftime(date_day, '%Y-%m') as year_month,
    from date_series
)

select * from final
