-- Grain per resolved_date (cost baru dianggap final setelah tiket resolved -- tiket
-- open/in-progress belum masuk hitungan cost, konsisten sifat cost yang belum final).
with agg as (
    select
        property_id,
        it.issue_type_id,
        resolved_date as period_date,
        sum(cost) as total_cost,
        sum(case when parts_replaced is not null then cost else 0 end) as cost_with_parts,
        sum(case when parts_replaced is null then cost else 0 end) as cost_without_parts
    from {{ ref('mart_cleaned__maintenance_tickets') }} as t
    left join {{ ref('dim_issue_type') }} as it
        on t.issue_type = it.issue_type_name
    where status = 'resolved' and resolved_date is not null
    group by 1, 2, 3
)

select
    cur.property_id,
    cur.issue_type_id,
    cur.period_date,
    cur.total_cost,
    cur.cost_with_parts,
    cur.cost_without_parts,
    cur.total_cost - mom.total_cost as mom_cost_growth,
    cur.total_cost - yoy.total_cost as yoy_cost_growth
from agg as cur
left join agg as mom
    on cur.property_id = mom.property_id and cur.issue_type_id = mom.issue_type_id
    and mom.period_date = date_sub(cur.period_date, interval 1 month)
left join agg as yoy
    on cur.property_id = yoy.property_id and cur.issue_type_id = yoy.issue_type_id
    and yoy.period_date = date_sub(cur.period_date, interval 1 year)
