<div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">

  <div style="max-width: 70%;">
    <h1>Especificaciones del Modelo Analítico</h1>
    <h2><strong>Manual de Gobernanza y Metodología BI (Berka Fintech)</strong></h2>
    <p>
    Este documento define las especificaciones funcionales y técnicas del Modelo Analítico del proyecto Berka Fintech. Incluye la metodología BI aplicada, la estructura de los tableros, definición de métricas clave (KPIs), reglas de gobernanza, optimizaciones de rendimiento y la documentación de las vistas del data warehouse implementadas en MySQL RDS.
    </p>
  </div>

  <div>
    <img src="../img/logo-berka.png" alt="Logo Berka" width="180" style="border-radius: 8px;">
  </div>

</div>

---

## Nombres y Propósito de los Tableros

| Tablero | Propósito  | Visualizaciones Clave |
| :--- | :--- | :--- |
| **Resumen Ejecutivo** | Evaluar rápidamente el **Riesgo y la Salud Financiera** general de la cartera de préstamos. | Tasa de Incumplimiento, Tendencia de Riesgo, Flujo de Caja. |
| **Análisis de Clientes** | Entender la **Distribución Demográfica y Rentabilidad** de los clientes segmentados por edad y género. | Mapa de Calor, Actividad de Cuentas por Segmento. |
| **Análisis de Fraude** | **Detectar transacciones y cuentas atípicas** con alto potencial de riesgo/fraude. | Scatter Plot Anómalo, Top 20 Cuentas Anómalas. |

##  Diccionario de Métricas Clave (KPIs)

| Métrica | Definición de Negocio | Campo / Agregación (QuickSight) | Tipo de Dato |
| :--- | :--- | :--- | :--- |
| **Tasa de Incumplimiento** | Porcentaje de préstamos activos que han caído en estado de default (status 'B' o 'D') sobre el total de préstamos. | `SUM(is_default) / COUNT(loan_id)` | Porcentaje |
| **Puntuación de Riesgo Promedio** | Valor promedio de riesgo asignado a cada cliente o préstamo. | `AVG(risk_score)` | Decimal |
| **Capital en Incumplimiento** | Monto total de los préstamos cuyo estado es 'B' (default) o 'D' (cancelado sin pagar). | `SUM(ifelse({status} IN ('B', 'D'), {loan_amount}, 0))` | Moneda (€) |
| **Total Transacciones Anómalas** | Conteo total de transacciones marcadas como *outliers* por el modelo (anomalía de monto). | `SUM(ifelse({is_amount_outlier} = 1, 1, 0))` | Número Entero |

-----
## Metodología de Segmentación y Clasificación

Documentación de los campos calculados clave que se usan para filtros y clasificación.

| Campo Clasificado | Lógica de Negocio | Usado en... |
| :--- | :--- | :--- |
| **Flag\_Riesgo** (Alto/Medio/Bajo) | Clasificación basada en la actividad (anomalías) y la salud financiera (balance negativo). <br> `ALTO`: $\ge 3$ anomalías **Y** Balance Negativo. <br> `MEDIO`: $> 0$ anomalías **O** Balance Negativo. | Top 20 Cuentas Anómalas |
| **Frecuencia\_ES** | Traducción de la frecuencia de pago de la cuenta (Mensual, Semanal, Variable). | Análisis de Clientes |
| **Tipo\_Transaccion\_ES** | Traducción de si la transacción es `INGRESO`, `RETIRO` o `GASTO/PAGO`. | Resumen Ejecutivo |

-----

### Documentación Técnica MySQL: Rendimiento y Conexión

#### Estrategia de Índices Críticos

Para garantizar la baja latencia en QuickSight, especialmente al aplicar filtros globales, los siguientes índices son obligatorios:

| Tabla (Dimensión/Fact) | Campos Clave (Índice Compuesto) | Propósito de Rendimiento |
| :--- | :--- | :--- |
| `fact_transactions` | `(account_id, date)` | Optimiza la búsqueda rápida al aplicar los filtros globales de **Región** y **Rango de Fechas**. |
| `dim_account` | `(account_id, owner_client_id)` | Acelera las uniones (JOINs) en las vistas principales (`v_loan_risk_analysis`, `v_customer_behavior`). |

#### 4.2. Detalles de la Conexión RDS

| Parámetro | Valor | Notas |
| :--- | :--- | :--- |
| **Tipo de Conexión** | MySQL RDS | Se usa para evitar problemas de permisos con Athena. |
| **Modo de QuickSight** | SPICE (Recomendado) | Se recomienda el modo SPICE para **máximo rendimiento** y respuesta instantánea al filtrar. |
| **Credenciales** | Usuario `quicksight_readonly` | Uso de credenciales de solo lectura para seguridad. |

# Documentación SQL: Vistas del Warehouse (MySQL RDS)

## Nota de Arquitectura

Debido a **errores persistentes de permisos y conectividad con Amazon Athena** y la necesidad de una fuente de datos rápida y robusta para Amazon QuickSight, se optó por **recrear todas las vistas de pre-procesamiento directamente en el motor MySQL RDS**. Esta conexión garantiza la baja latencia requerida para la interacción dinámica del *dashboard*.

**Esquema utilizado:** `berka_warehouse` (o el esquema que se esté utilizando en el entorno RDS).

-----

## 1\. `v_account_activity` (Actividad Agregada por Cuenta)

**Propósito:** Combina los datos maestros de la cuenta con sus métricas transaccionales agregadas para tener una vista completa del estado del cliente (salud financiera, antigüedad, etc.). Esta vista alimenta el tablero de **Análisis de Clientes**.

```sql
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
```

-----

## 2\. `v_loan_risk_analysis` (Análisis de Riesgo de Préstamo)

**Propósito:** Combina información del préstamo, la cuenta y la región geográfica del cliente para calcular métricas de riesgo y tasas de incumplimiento. **Alimenta el tablero Resumen Ejecutivo**. Se actualizó para incluir `owner_client_id`.

```sql
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
```

-----

## 3\. `v_customer_behavior` (Comportamiento y Transacciones)

**Propósito:** Une los datos de transacciones de clientes con sus características demográficas (género, segmento de edad). Es la vista base para el análisis de transacciones y riesgo.

```sql
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
```

-----

## 4\.`v_fraude_analisis` (Vista Unificada para Fraude)

**Propósito:** Vista final que une las transacciones individuales (`v_customer_behavior`) con las métricas de salud de la cuenta (`v_account_activity`). **Es la fuente de datos exclusiva para el tablero Análisis de Fraude**, permitiendo la detección de anomalías y el cálculo de la `Flag_Riesgo`.

```sql
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
```

### Documentación de QuickSight: Gobernanza y UX

#### Reglas de Filtros Globales (Cross-Dataset Mapping)

Todos los filtros globales afectan a todos los *datasets* del *dashboard* a través de un mapeo explícito de campos, garantizando una experiencia de usuario coherente.

| Control de Filtro | Campo Principal del Control | Campos Mapeados Adicionales |
| :--- | :--- | :--- |
| **Rango de Fechas** | `trans_date` | `loan_start_date` (en `v_loan_risk_analysis`) |
| **Región** | `region` | `region` (Mapeado en todos los datasets) |
| **Segmento de Edad** | `age_segment` | `age_segment` (Mapeado en todos los datasets relevantes) |
| **Genero** | `gender` | `gender` (Mapeado en todos los datasets relevantes) |

#### Normas de Consistencia Visual y Formato

| Elemento | Norma Aplicada | Razón |
| :--- | :--- | :--- |
| **Convención de Idioma** | Todo en **Español**. | Reemplazo de términos checos (`VYDAJ`, `POPLATEK MESICNE`) por traducciones claras. |
| **Colores de Riesgo** | **Rojo** para Incumplimiento/Anomalía. **Azul** para Performance/Total. | Coherencia en la comunicación de riesgo financiero. |
| **Formato Numérico** | Porcentajes con dos decimales. Moneda con símbolo **€** y separador de miles. | Estándar ejecutivo para reportes financieros. |
| **KPI de Género** | Uso de **Subtítulo** (`(Masculino: 60% / Femenino: 40%)`) | Proporciona el contexto completo de la división de género en una sola tarjeta. |



