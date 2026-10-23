{# The level monthly payment on a fully amortising loan: principal, annual rate in percent, term in years. Mirrors
   doorstep_finance.payment, and a test holds the two to the cent. #}
{% macro monthly_payment(principal, rate_pct, years) %}
    case
        when {{ rate_pct }} is null or {{ principal }} is null then null
        when {{ rate_pct }} = 0 then {{ principal }} / ({{ years }} * 12.0)
        else {{ principal }} * ({{ rate_pct }} / 1200.0) * power(1.0 + {{ rate_pct }} / 1200.0, {{ years }} * 12)
             / (power(1.0 + {{ rate_pct }} / 1200.0, {{ years }} * 12) - 1.0)
    end
{% endmacro %}
