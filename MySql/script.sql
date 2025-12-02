

CREATE OR REPLACE VIEW berka_warehouse.v_account_activity AS
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
FROM dim_account a
LEFT JOIN fact_account_transactions t 
    ON a.account_id = t.account_id;

CREATE OR REPLACE VIEW berka_warehouse.v_loan_risk_analysis AS
SELECT
    l.loan_id,
    l.account_id,
    l.amount AS loan_amount,
    l.duration,
    l.status,
    l.status_label,
    l.is_risky,
    l.loan_start_date,
    a.owner_client_id,
    d.district_id,
    d.region,
    d.district_name,
    d.average_salary,
    d.unemployment_rate_96
FROM dim_loan l
JOIN dim_account a ON l.account_id = a.account_id
JOIN dim_district d ON a.district_id = d.district_id;

CREATE OR REPLACE VIEW berka_warehouse.v_customer_behavior AS
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
FROM dim_client c
JOIN dim_account a ON c.client_id = a.owner_client_id
JOIN fact_transactions t ON a.account_id = t.account_id;

CREATE OR REPLACE VIEW berka_warehouse.v_fraude_analisis AS
SELECT
    -- Campos clave de Transacciones (t)
    t.trans_id,
    t.account_id,
    t.trans_amount,
    t.is_amount_outlier,
    t.final_balance,        

    -- Campos clave de Cuentas (a)
    a.has_negative_balance,
    a.frequency,
    a.account_age_years     

FROM
    berka_warehouse.v_customer_behavior t  -- Transacciones
INNER JOIN
    berka_warehouse.v_account_activity a   -- Cuentas
    ON t.account_id = a.account_id;