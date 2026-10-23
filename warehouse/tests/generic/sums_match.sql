{# The model's column summed equals an expression over another model, to floating tolerance: a mart that
   dropped rows fails; a sum that differs by rounding noise does not. #}
{% test sums_match(model, column_name, compare_model, compare_expression) %}
with a as (select sum({{ column_name }}) as v from {{ model }}),
     b as (select {{ compare_expression }} as v from {{ compare_model }})
select a.v as model_sum, b.v as compare_sum
from a, b
where (a.v is null) <> (b.v is null)
   or abs(coalesce(a.v, 0) - coalesce(b.v, 0)) > 1e-6 * greatest(abs(coalesce(a.v, 0)), 1.0)
{% endtest %}
