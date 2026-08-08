{#
    Milestone 2.3 -- override dbt's default generate_schema_name.

    dbt's default behavior CONCATENATES a model's custom +schema with the
    connection's target schema (e.g. target=staging + custom=mart_cleaned_staging
    -> "staging_mart_cleaned_staging"). This caused a real bug in Milestone 2.2
    ("staging_staging" dataset created by accident) and would break Milestone
    2.3's separation between staging/ (dataset "staging") and mart_cleaned/
    (dataset "mart_cleaned_staging", set via +schema in dbt_project.yml).

    This override makes a custom schema used LITERALLY when set, ignoring the
    target's base dataset entirely -- matching how every model in this project
    actually expects schema/dataset names to work.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
