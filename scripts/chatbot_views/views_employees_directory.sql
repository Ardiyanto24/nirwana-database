-- Milestone 4.2: AI Chatbot views -- domain `employees_directory`.
-- Source: mart_aggregated.dim_employee (see
-- docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md §2.8).
-- full_name sudah diaudit PII M5.2 dan sengaja diteruskan apa adanya
-- (kebutuhan name-resolution eksplisit dari banyak persona chatbot).

CREATE OR REPLACE VIEW chatbot_views.v_employees_directory AS
SELECT
    e.employee_id,
    e.full_name,
    e.property_id,
    p.property_name,
    d.department_name,
    al.access_level_name
FROM mart_aggregated.dim_employee e
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = e.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = e.department_id
LEFT JOIN mart_aggregated.dim_access_level al ON al.access_level_id = e.access_level_id;
