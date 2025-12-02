-- ============================================================================
-- 🏦 SCRIPT DE ANÁLISIS DE NEGOCIO Y RIESGO - BERKA FINTECH 
-- OBJETIVO: Profundizar en el análisis del comportamiento del cliente y
--           la detección de riesgo/anomalías para la gerencia de una Fintech.
-- ============================================================================
-- ============================================================================
-- 1. CREACIÓN DE VISTAS (Optimización y Reutilización)
-- PROPÓSITO: Simplificar consultas complejas al pre-unir tablas clave.
-- ============================================================================

-- 1.1 Vista: v_customer_behavior (Comportamiento del cliente en transacciones)
-- UNE: Cliente (demografía) + Cuenta (antigüedad) + Transacciones (actividad).
CREATE OR REPLACE VIEW berkafintech_db.v_customer_behavior AS
SELECT
    c.client_id,
    c.age_segment,
    c.gender,
    a.account_id,
    a.frequency,
    t.trans_id,
    t.date AS trans_date,
    t.type AS trans_type,
    t.operation,
    t.amount AS trans_amount,
    t.final_balance,
    t.is_amount_outlier
FROM berkafintech_db.dim_client c
JOIN berkafintech_db.dim_account a ON c.client_id = a.owner_client_id 
JOIN berkafintech_db.fact_transactions t ON a.account_id = t.account_id
WITH NO DATA;

-- 1.2 Vista: v_loan_risk_analysis (Análisis de riesgo crediticio y contexto económico)
-- UNE: Préstamos (riesgo) + Cuenta + Distrito (contexto económico).
CREATE OR REPLACE VIEW berkafintech_db.v_loan_risk_analysis AS
SELECT
    l.loan_id,
    l.account_id,
    l.amount AS loan_amount,
    l.duration,
    l.status,
    l.status_label,
    l.is_risky,
    d.district_id,
    d.region,
    d.district_name,
    d.average_salary,
    d.unemployment_rate_96
FROM berkafintech_db.dim_loan l
JOIN berkafintech_db.dim_account a ON l.account_id = a.account_id
JOIN berkafintech_db.dim_district d ON a.district_id = d.district_id
WITH NO DATA;
-- ============================================================================
-- 1.3 Vista: v_account_activity (Métricas de actividad por cuenta)
-- UNE: dim_account (demografía del dueño, antigüedad) + 
--      fact_account_transactions (total transacciones, balance promedio, ratios).
-- ============================================================================
CREATE OR REPLACE VIEW berkafintech_db.v_account_activity AS
SELECT
    a.account_id,
    a.district_id,
    a.frequency,
    a.date AS account_start_date,
    a.account_age_years,
    a.account_age_segment,
    a.owner_client_id,
    t.total_transactions,
    t.total_income_amount,
    t.total_expense_amount,
    t.net_balance,
    t.income_to_expense_ratio,
    t.avg_transaction_amount,
    t.avg_balance,
    t.has_negative_balance,
    t.transactions_per_day
FROM berkafintech_db.dim_account a
-- Usamos LEFT JOIN para incluir cuentas que no tienen transacciones (Inactivas)
LEFT JOIN berkafintech_db.fact_account_transactions t 
    ON a.account_id = t.account_id;

-- ============================================================================
-- 2. ANÁLISIS DE RIESGO CREDITICIO Y CARTERA
-- ============================================================================

-- 2.1 Tasa de default por segmento de monto de préstamo
-- PROPÓSITO: Identificar si los préstamos grandes o pequeños tienen mayor propensión a fallar.
-- INSIGHT: Si la tasa de default es mayor en 'Large' o 'Very Large', el modelo de riesgo es débil para montos altos.
SELECT 
    loan_amount_segment,
    COUNT(*) AS total_prestamos,
    -- Contamos los préstamos que terminaron mal ('B' o 'D').
    SUM(CASE WHEN status IN ('B', 'D') THEN 1 ELSE 0 END) AS prestamos_default,
    ROUND(
        SUM(CASE WHEN status IN ('B', 'D') THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) AS tasa_default_porcentaje,
    ROUND(AVG(amount), 2) AS monto_promedio
FROM berkafintech_db.dim_loan
GROUP BY loan_amount_segment
ORDER BY tasa_default_porcentaje DESC;

-- 2.2 Perfil de clientes con préstamos riesgosos (Usando la Vista 1.2)
-- PROPÓSITO: Identificar qué segmento demográfico (edad/género) impulsa el riesgo.
-- INSIGHT: Crucial para focalizar campañas de recuperación o rechazar clientes con este perfil.
SELECT 
    c.gender,
    c.age_segment,
    COUNT(DISTINCT l.loan_id) AS total_prestamos_riesgosos,
    ROUND(AVG(l.amount), 2) AS monto_promedio_prestamo,
    ROUND(AVG(c.age_at_1998), 2) AS edad_promedio
FROM berkafintech_db.dim_client c
JOIN berkafintech_db.dim_account a ON c.client_id = a.owner_client_id
JOIN berkafintech_db.dim_loan l ON a.account_id = l.account_id
-- CORRECCIÓN APLICADA: Usamos 1 en lugar de TRUE, asumiendo el ETL escribe flags como INTEGER (1/0).
WHERE l.is_risky = 1
GROUP BY c.gender, c.age_segment
ORDER BY total_prestamos_riesgosos DESC;

-- 2.3 Correlación entre salario regional y riesgo de préstamo (Usando la Vista 1.2)
-- PROPÓSITO: Entender si la estabilidad económica del distrito es un buen predictor de morosidad.
-- INSIGHT: Si el salario promedio es bajo y la tasa de default es alta, el riesgo es sistémico en esa región.
SELECT
    region,
    ROUND(AVG(average_salary), 2) AS salario_promedio,
    COUNT(loan_id) AS total_prestamos,
    SUM(CASE WHEN status IN ('B', 'D') THEN 1 ELSE 0 END) AS total_defaults,
    ROUND(SUM(CASE WHEN status IN ('B', 'D') THEN 1 ELSE 0 END) * 100.0 / COUNT(loan_id), 2) AS tasa_default_pct
FROM berkafintech_db.v_loan_risk_analysis
GROUP BY region
HAVING COUNT(loan_id) > 10 -- Filtra regiones con pocos préstamos para estabilidad estadística
ORDER BY tasa_default_pct DESC;

-- ============================================================================
-- 3. ANÁLISIS DE COMPORTAMIENTO Y ENGAGEMENT
-- ============================================================================

-- 3.1 Patrones de transacciones por edad y género (Usando la Vista 1.1)
-- PROPÓSITO: Descubrir qué segmentos demográficos generan más ingresos (PRIJEM) o gastos (VYDAJ).
-- INSIGHT: Ayuda a dirigir ofertas de inversión o crédito.
SELECT
    age_segment,
    gender,
    trans_type AS tipo_transaccion,
    COUNT(trans_id) AS num_transacciones,
    ROUND(AVG(trans_amount), 2) AS monto_promedio
FROM berkafintech_db.v_customer_behavior
GROUP BY age_segment, gender, trans_type
ORDER BY num_transacciones DESC;

-- 3.2 Segmentación de clientes por actividad transaccional
-- PROPÓSITO: Clasificar el nivel de lealtad y potencial del cliente.
-- INSIGHT: Los clientes 'Inactiva' o 'Baja Actividad' son objetivos para campañas de reactivación.
SELECT 
    CASE 
        WHEN trans_count = 0 THEN 'Inactiva'
        WHEN trans_count < 10 THEN 'Baja Actividad'
        WHEN trans_count < 50 THEN 'Actividad Media'
        ELSE 'Alta Actividad'
    END AS segmento_actividad,
    COUNT(*) AS num_cuentas
FROM (
    -- Subconsulta para contar transacciones por cuenta
    SELECT 
        a.account_id,
        COUNT(t.trans_id) AS trans_count
    FROM berkafintech_db.dim_account a
    LEFT JOIN berkafintech_db.fact_transactions t ON a.account_id = t.account_id
    GROUP BY a.account_id
) subq
GROUP BY segmento_actividad
ORDER BY num_cuentas DESC;

-- 3.3 Tipos de transacciones por frecuencia de cuenta
-- PROPÓSITO: Relacionar el tipo de producto (frecuencia de extracto) con el comportamiento transaccional.
-- INSIGHT: Las cuentas con extractos más frecuentes ('WEEKLY') pueden ser las que usan más 'VYDAJ' (gastos).
SELECT 
    a.frequency AS tipo_cuenta,
    t.type AS tipo_transaccion,
    t.operation AS operacion,
    COUNT(*) AS num_transacciones,
    ROUND(SUM(t.amount), 2) AS volumen_total
FROM berkafintech_db.dim_account a
JOIN berkafintech_db.fact_transactions t ON a.account_id = t.account_id
GROUP BY a.frequency, t.type, t.operation
ORDER BY num_transacciones DESC;

-- ============================================================================
-- 4. DETECCIÓN DE FRAUDE Y ANOMALÍAS
-- ============================================================================

-- 4.1 Detección de Transacciones Anómalas (Outliers)
-- PROPÓSITO: Aislar transacciones que superan el percentil 95 (o similar) para auditoría manual (ALM/Fraude).
-- INSIGHT: Si hay un patrón de 'VYDAJ' (egreso) o 'PREJEM' (ingreso) anómalo con un mismo símbolo, puede ser una alerta.
SELECT 
    trans_id,
    account_id,
    trans_date,
    trans_type,
    operation,
    trans_amount,
    final_balance,
    CASE WHEN is_amount_outlier = 1 THEN '🚨 SOSPECHOSA' ELSE 'Normal' END AS flag_fraude
FROM berkafintech_db.v_customer_behavior
-- CORRECCIÓN APLICADA: Usamos 1 en lugar de TRUE
WHERE is_amount_outlier = 1
ORDER BY trans_amount DESC
LIMIT 100;

-- ============================================================================
-- 5. RESUMEN EJECUTIVO (KPIs)
-- ============================================================================
-- 5.1 Dashboard ejecutivo - Métricas clave
-- PROPÓSITO: Presentación de los KPIs de negocio más críticos en un formato de tabla simple (usado en QuickSight).
SELECT 
    'Total Clientes' AS metrica,
    CAST(COUNT(*) AS VARCHAR) AS valor
FROM berkafintech_db.dim_client
UNION ALL
SELECT 'Tasa de Morosidad (%)', 
       -- Se usa status_label para la etiqueta descriptiva si el ETL la saneó correctamente a STRING.
       CAST(ROUND(SUM(CASE WHEN status_label IN ('Contract finished, loan not paid', 'Contract running, client in debt') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS VARCHAR)
FROM berkafintech_db.dim_loan
UNION ALL
SELECT 'Volumen Total Préstamos', 
       CAST(ROUND(SUM(amount), 2) AS VARCHAR)
FROM berkafintech_db.dim_loan
UNION ALL
SELECT 'Tasa de Detección de Anomalías (Outliers) (%)', 
       -- CORRECCIÓN: Usamos 1 en lugar de TRUE
       CAST(ROUND(SUM(CASE WHEN is_amount_outlier = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS VARCHAR)
FROM berkafintech_db.fact_transactions
UNION ALL
SELECT 'Ratio de Apalancamiento (Clientes con Préstamo/Tarjeta) (%)',
       -- Mide el porcentaje de clientes que utilizan múltiples productos de alto valor.
       CAST(ROUND(SUM(CASE WHEN num_loans > 0 OR num_cards > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS VARCHAR)
FROM berkafintech_db.fact_account_summary;