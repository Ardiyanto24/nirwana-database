-- Milestone 4.2: AI Chatbot views -- domain `properties_ref`.
-- Source: mart_aggregated.dim_property (see
-- docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md §2.7).
-- dim_property sudah cukup untuk seluruh kebutuhan (metadata ringan, sudah
-- diaudit aman diteruskan apa adanya, M5.2) -- tidak perlu mart_cleaned.properties.

CREATE OR REPLACE VIEW chatbot_views.v_properties_ref AS
SELECT
    p.property_id,
    p.property_name,
    p.region,
    p.opening_date
FROM mart_aggregated.dim_property p;
