<div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
  <div style="flex: 1;">
    <h1>ANÁLISIS DE NEGOCIO Y RIESGO - BERKA FINTECH</h1>
    <h3>🔍 Análisis 1: Tasa de <i>Default</i> por Segmento de Monto de Préstamo</h3>
    <p>
      <strong>OBJETIVO:</strong> Profundizar en el análisis del comportamiento del cliente y la detección de riesgo/anomalías para la gerencia de una Fintech.
    </p>
  </div>
  <div style="flex-shrink: 0;">
    <img src="../img/logo-berka.png" alt="logo berka" width="200">
  </div>
</div>

### 1\. Contexto de la *Query*

  * **Nombre del Análisis:** Riesgo Crediticio por Segmento de Monto de Préstamo
  * **Propósito:** Identificar si la **tasa de *default* varía significativamente** entre los préstamos de monto pequeño, mediano, o grande.
  * **Código SQL (Resumido):**
    ```sql
    SELECT loan_amount_segment, COUNT(*), SUM(CASE WHEN status IN ('B', 'D') THEN 1 ELSE 0 END) AS prestamos_default, ROUND(tasa_default_porcentaje, 2)
    FROM berkafintech_db.dim_loan
    GROUP BY loan_amount_segment ORDER BY tasa_default_porcentaje DESC;
    ```
-----

### 2\. Resultados Obtenidos (Datos Clave)

| Segmento | Préstamos Totales | Préstamos en *Default* | **Tasa de *Default*** | Monto Promedio |
| :--- | :--- | :--- | :--- | :--- |
| **Very Large (300K+)** | 82 | 17 | **20.73%** | 382,724.34 |
| **Large (150K-300K)** | 205 | 28 | **13.66%** | 209,675.12 |
| **Medium (50K-150K)** | 269 | 26 | **9.67%** | 92,457.72 |
| **Small (\< 50K)** | 126 | 5 | **3.97%** | 31,935.05 |

-----

### 3\. Análisis e *Insight* Valioso

#### 🔑 *Insight* Clave

Existe una **correlación directa y muy fuerte entre el monto del préstamo y la tasa de *default***. El segmento de préstamos **'Very Large (300K+)'** presenta una tasa de *default* alarmantemente alta del **20.73%**, lo que es **cinco veces mayor** que la del segmento 'Small (\< 50K)' (3.97%).

#### 🚨 Implicaciones/Recomendaciones

  * **Validación del Modelo de Riesgo:** El modelo de riesgo crediticio actual parece ser **débil o insuficiente** para evaluar adecuadamente a los solicitantes de préstamos de **montos muy altos** (por encima de 300K).
  * **Acción Inmediata (Mitigación):** Se debe **suspender o aplicar criterios de aprobación mucho más estrictos** (o aumentar significativamente las tasas de interés para compensar el riesgo) para el segmento 'Very Large' hasta que se revalúe el modelo.
  * **Próximos Pasos (Investigación):** Es fundamental realizar una **investigación cualitativa** en los préstamos 'Very Large' que cayeron en *default* (status 'B' o 'D'). ¿Qué características (ingreso, antigüedad laboral, propósito del préstamo) tienen en común estos prestatarios fallidos que el modelo no capturó?

-----

## 🔬 Análisis 2: Perfil Demográfico de Clientes con Préstamos Riesgosos

### 1\. Contexto de la *Query*

  * **Nombre del Análisis:** Perfil Demográfico (Edad y Género) del Riesgo Crediticio.
  * **Propósito:** Identificar las combinaciones de **segmento de edad y género** que concentran el mayor número de préstamos considerados como riesgosos (*is\_risky = 1*).
  * **Código SQL (Resumido):**
    ```sql
    SELECT c.gender, c.age_segment, COUNT(DISTINCT l.loan_id) AS total_prestamos_riesgosos, ROUND(AVG(l.amount), 2) AS monto_promedio_prestamo
    FROM berkafintech_db.dim_client c JOIN ... JOIN berkafintech_db.dim_loan l ON a.account_id = l.account_id
    WHERE l.is_risky = 1
    GROUP BY c.gender, c.age_segment ORDER BY total_prestamos_riesgosos DESC;
    ```
-----

### 2\. Resultados Obtenidos (Datos Clave)

| Género | Segmento de Edad | **Total Préstamos Riesgosos** | Monto Promedio Préstamo | Edad Promedio |
| :--- | :--- | :--- | :--- | :--- |
| **F** | **45-54** | **11** | 190,759.64 | 50.73 |
| **F** | **18-24** | **10** | **289,954.80** | 21.50 |
| F | 25-34 | 9 | 262,146.67 | 30.11 |
| M | 35-44 | 9 | 222,177.33 | 38.89 |
| M | 45-54 | 8 | 154,734.00 | 48.38 |
| M | 55-64 | 8 | 153,859.50 | 60.50 |

-----

### 3\. Análisis e *Insight* Valioso

#### 🔑 *Insight* Clave

El **riesgo crediticio está fuertemente concentrado en el género femenino** en dos segmentos de edad muy distintos, pero con un enfoque de alto monto:

1.  **Riesgo por Volumen (F 45-54):** Este segmento tiene el mayor número de préstamos riesgosos (**11**).
2.  **Riesgo por Monto (F 18-24):** A pesar de tener un volumen ligeramente menor (**10**), las mujeres jóvenes (18-24) están obteniendo **préstamos riesgosos con el monto promedio más alto de todos los segmentos ($289,954.80$)**, lo que las convierte en el grupo de **mayor riesgo potencial por impacto financiero**.

#### 🎯 Implicaciones/Recomendaciones

  * **Revisión de Políticas de Préstamo (F 18-24):** El sistema está aprobando préstamos de montos "Large" (según el Análisis 1) a un segmento de clientes jóvenes que suele tener un historial crediticio o estabilidad de ingresos más limitado. Se debe **ajustar la matriz de aprobación** para mujeres de 18-24, limitando el monto máximo de préstamo o exigiendo garantías adicionales.
  * **Estrategia de Cobranza (F 45-54):** Dado el volumen significativo de riesgo en mujeres de 45-54 años, los equipos de cobranza deben **priorizar los esfuerzos de recuperación** en este segmento.
  * **Próximos Pasos (Investigación):** Cruzar este *insight* con el Análisis 1. ¿Estos préstamos riesgosos caen en el segmento 'Very Large (300K+)' o 'Large (150K-300K)'? ¿Qué variables (como el propósito del préstamo o el tipo de cuenta) contribuyen al alto riesgo en estos dos grupos demográficos femeninos específicos?

-----

## 🌎 Análisis 3: Correlación entre Salario Regional y Riesgo de Préstamo

### 1\. Contexto de la *Query*

  * **Nombre del Análisis:** Estabilidad Económica Distrital y Tasa de *Default*.
  * **Propósito:** Determinar si existe una **correlación sistémica** entre el salario promedio de una región (distrito) y el riesgo de *default* de los préstamos otorgados allí.
  * **Filtro:** Solo se consideraron regiones con más de 10 préstamos.
  * **Código SQL (Resumido):**
    ```sql
    SELECT region, ROUND(AVG(average_salary), 2) AS salario_promedio, COUNT(loan_id), ROUND(tasa_default_pct, 2)
    FROM berkafintech_db.v_loan_risk_analysis
    GROUP BY region HAVING COUNT(loan_id) > 10 ORDER BY tasa_default_pct DESC;
    ```
-----

### 2\. Resultados Obtenidos (Datos Clave)

| Región | **Salario Promedio** | Total Préstamos | Total *Defaults* | **Tasa de *Default* (%)** |
| :--- | :--- | :--- | :--- | :--- |
| **west Bohemia** | 8,995.42 | 57 | 9 | **15.79%** |
| **north Moravia** | 9,474.93 | 117 | 18 | **15.38%** |
| **south Bohemia** | 8,806.17 | 60 | 9 | **15.00%** |
| central Bohemia | 9,271.68 | 90 | 10 | 11.11% |
| **Prague** | **12,541.00** | 84 | 7 | **8.33%** |
| **north Bohemia** | 9,318.16 | 61 | 1 | **1.64%** |

-----

### 3\. Análisis e *Insight* Valioso

#### 🔑 *Insight* Clave

La hipótesis se confirma: existe una **correlación negativa** (a mayor salario, menor riesgo) para la mayoría de las regiones. Las tres regiones con el **riesgo más alto** ('west Bohemia', 'north Moravia', 'south Bohemia') tienen salarios promedio consistentemente bajos (entre 8,800 y 9,500) y tasas de *default* que casi duplican la tasa promedio (15%-16%).

La capital, **Prague**, con el salario promedio más alto (12,541), presenta una de las tasas de *default* más bajas (8.33%).

#### 🚨 Anomalía Clave

La región de **'north Bohemia'** es una **anomalía crítica**. Su salario promedio (9,318.16) es similar al de las regiones de alto riesgo, pero su tasa de *default* es extremadamente baja (**1.64%**). Esto sugiere que hay **factores no salariales** (quizás mayor estabilidad laboral, menor endeudamiento general, o un perfil de cliente diferente) que mitigan el riesgo en esta región, lo que debe ser investigado.

#### 🎯 Implicaciones/Recomendaciones

  * **Acción Inmediata (Riesgo Geográfico):** Aplicar un **aumento en la tasa de interés o una restricción en el LTV (Loan-to-Value)** para cualquier solicitante de **'west Bohemia', 'north Moravia', y 'south Bohemia'**. Estos distritos representan un riesgo sistémico.
  * **Oportunidad (Región 'Prague'):** La calidad de los préstamos en **'Prague'** es alta. Se puede considerar **aumentar el *target* de préstamos** en esta región o a clientes con un perfil salarial similar.
  * **Próximos Pasos (Investigación del Caso de Éxito):** Realizar un análisis de *clustering* para los clientes de **'north Bohemia'** que recibieron préstamos. El objetivo es **identificar el factor mitigante** que hace que esta región sea de bajo riesgo a pesar de su bajo salario, para luego intentar **replicar** ese criterio en la política de préstamos de otras regiones de bajo salario.

-----

## 📈 Análisis 4: Patrones de Transacciones por Edad y Género

### 1\. Contexto de la *Query*

  * **Nombre del Análisis:** Comportamiento de *Engagement* (Ingreso vs. Gasto) Demográfico.
  * **Propósito:** Identificar los segmentos demográficos que son más activos (**número de transacciones**) y el valor promedio de sus transacciones de **Ingreso (PRIJEM)** y **Gasto (VYDAJ)**.
  * **Tipos de Transacción:**
      * **VYDAJ:** Gasto/Egreso.
      * **PRIJEM:** Ingreso/Depósito.
      * **VYBER:** Retiro (generalmente en cajero).
  * **Código SQL (Resumido):**
    ```sql
    SELECT age_segment, gender, trans_type AS tipo_transaccion, COUNT(trans_id) AS num_transacciones, ROUND(AVG(trans_amount), 2) AS monto_promedio
    FROM berkafintech_db.v_customer_behavior
    GROUP BY age_segment, gender, trans_type ORDER BY num_transacciones DESC;
    ```
-----

### 2\. Resultados Obtenidos (Datos Clave)

| Segmento | Género | Tipo Transacción | **Num. Transacciones** | Monto Promedio |
| :--- | :--- | :--- | :--- | :--- |
| **25-34** | **F** | VYDAJ | **32,977** | 4,745.02 |
| **45-54** | **F** | VYDAJ | 31,961 | 5,063.81 |
| 45-54 | M | VYDAJ | 30,064 | 5,114.43 |
| 25-34 | F | PRIJEM | 20,154 | **8,948.93** |
| 45-54 | F | PRIJEM | 19,457 | **9,508.91** |
| 35-44 | M | PRIJEM | 18,154 | **9,581.47** |
| **18-24** | **M** | PRIJEM | 17,241 | **6,731.18** |
| **65+** | **M** | VYDAJ | 22,209 | **1,623.24** |
| **VYBER** (Retiros) | *(Todos)* | VYBER | *(Bajo)* | **\~12,500** |

-----

### 3\. Análisis e *Insight* Valioso

#### 🔑 *Insight* Clave

1.  **Motor de Transacciones (VYDAJ):** El segmento **Femenino 25-34** es el **más activo** en términos de volumen de transacciones salientes (32,977 VYDAJ), lo que indica un **alto *engagement*** con el sistema de pagos diario.
2.  **Valor de Ingresos (PRIJEM):** Los clientes **Hombres (35-44)** y **Mujeres (45-54)** son los que tienen el **monto promedio de ingreso (PRIJEM)** más alto (cercano a 9,500), lo que los posiciona como la **base de ingresos más estable y valiosa**.
3.  **Comportamiento del Adulto Mayor (65+):** Este segmento tiene un volumen alto de transacciones salientes (VYDAJ), pero con un **monto promedio extremadamente bajo (1,623)**, sugiriendo un patrón de **gastos frecuentes, pero de bajo valor**, probablemente asociados a la jubilación.

#### 🎯 Implicaciones/Recomendaciones

  * **Estrategia de Productos (F 25-34):** Dado su alto *engagement* transaccional, este grupo es ideal para la **venta cruzada (cross-selling) de productos relacionados con el gasto** diario (tarjetas de crédito con recompensas, herramientas de presupuesto).
  * **Foco en Inversión (M 35-44 y F 45-54):** Con el mayor ingreso promedio, este segmento es el *target* primario para la **oferta de productos de inversión, ahorro a largo plazo y gestión patrimonial**.
  * **Optimización de Retiros (VYBER):** El monto promedio de los retiros es alto (\~12,500). Esto sugiere que los clientes están esperando para retirar **grandes cantidades de efectivo**, lo cual puede indicar insatisfacción con los límites de retiro o una preferencia por el efectivo para ciertas compras. **Investigar el límite de retiro** actual de los clientes.

-----

## 📊 Análisis 5: Segmentación de Clientes por Actividad Transaccional

### 1\. Contexto de la *Query*

  * **Nombre del Análisis:** Niveles de Lealtad y Potencial del Cliente por Volumen Transaccional.
  * **Propósito:** Clasificar la **base de clientes** en segmentos de actividad (Alta, Media, Baja, Inactiva) basándose en el **número total de transacciones** por cuenta (*trans\_count*).
  * **Definición de Segmentos:**
      * **Inactiva:** 0 transacciones.
      * **Baja Actividad:** \< 10 transacciones.
      * **Actividad Media:** 10 a 49 transacciones.
      * **Alta Actividad:** $\ge 50$ transacciones.
  * **Código SQL (Resumido):**
    ```sql
    SELECT CASE WHEN trans_count = 0 THEN 'Inactiva' ... ELSE 'Alta Actividad' END AS segmento_actividad, COUNT(*) AS num_cuentas
    FROM (SELECT a.account_id, COUNT(t.trans_id) AS trans_count FROM dim_account a LEFT JOIN fact_transactions t ON a.account_id = t.account_id GROUP BY a.account_id) subq
    GROUP BY segmento_actividad ORDER BY num_cuentas DESC;
    ```
-----

### 2\. Resultados Obtenidos (Datos Clave)

| Segmento de Actividad | **Número de Cuentas** | Porcentaje Aproximado |
| :--- | :--- | :--- |
| **Alta Actividad** | **3,870** | $\approx 86.5\%$ |
| **Actividad Media** | 613 | $\approx 13.5\%$ |
| Baja Actividad | 17 | $< 0.5\%$ |
| **Inactiva** | 0 | $0\%$ |
| **TOTAL** | **4,500** | $100\%$ |

-----

### 3\. Análisis e *Insight* Valioso

#### 🔑 *Insight* Clave

La base de clientes de la institución es **extremadamente activa y comprometida**. La gran mayoría de las cuentas, **3,870 cuentas (alrededor del 86.5%)**, caen en el segmento de **'Alta Actividad'** (50 o más transacciones).

Un hallazgo crucial es la **ausencia de cuentas 'Inactivas'** (0 transacciones) y un número marginalmente pequeño de cuentas en **'Baja Actividad'** (solo 17 cuentas). Esto sugiere que la institución **logra rápidamente que las cuentas recién abiertas comiencen a transaccionar** o que el *dataset* solo incluye clientes que ya han establecido un patrón de uso.

#### 🎯 Implicaciones/Recomendaciones

  * **Estrategia de Crecimiento (Foco en *Uplifting*):** Dado que la inactividad no es un problema, la estrategia no debe ser de *reactivación*, sino de ***uplifting* (aumento de valor)**. El foco debe estar en mover las **613 cuentas de 'Actividad Media'** al segmento de 'Alta Actividad'. Esto se puede lograr incentivando transacciones más allá del umbral 50 (ej: con recompensas por el uso de tarjetas).
  * **Oportunidad de Venta Cruzada (Alta Actividad):** Los 3,870 clientes de 'Alta Actividad' son los **mejores candidatos para la venta cruzada (cross-selling)**, ya que su alto *engagement* indica lealtad. Se les deben ofrecer productos de mayor valor como préstamos (si su riesgo es bajo), seguros e inversiones.
  * **Mantenimiento (Baja Actividad):** Aunque son solo 17, estas cuentas de 'Baja Actividad' deben ser analizadas individualmente para entender por qué se detuvieron antes de las 10 transacciones. Podría ser un **problema de *onboarding***.

-----

### ✅ Resumen del *Pipeline* de *Insights*

Hemos documentado 5 *insights* valiosos, cubriendo:

1.  **Riesgo por Monto:** La debilidad del modelo para préstamos 'Very Large'.
2.  **Riesgo Demográfico:** La concentración de riesgo en mujeres jóvenes y de mediana edad.
3.  **Riesgo Geográfico:** La correlación entre bajo salario y *default*, y la anomalía de 'north Bohemia'.
4.  **Comportamiento de Gasto:** El alto *engagement* en mujeres 25-34 y el alto valor de ingreso en adultos.
5.  **Lealtad General:** La gran actividad y la baja inactividad de la base de clientes.

¡No hay problema\! La calidad de los *insights* es lo importante. Este último análisis que nos proporcionas es clave, ya que relaciona directamente la estructura de comisiones/frecuencia de extracto con el comportamiento transaccional del cliente.

Aquí tienes la documentación para el sexto análisis.

-----

## ⚙️ Análisis 6: Tipos de Transacciones por Frecuencia de Cuenta

### 1\. Contexto de la *Query*

  * **Nombre del Análisis:** Impacto del Tipo de Cuenta (Frecuencia de Extracto) en el Comportamiento Transaccional.
  * **Propósito:** Entender si las cuentas con extractos más frecuentes (**`POPLATEK TYDNE`** - Semanal) o basados en actividad (**`POPLATEK PO OBRATU`** - Por Giro/Volumen) demuestran un comportamiento diferente en comparación con el modelo estándar (**`POPLATEK MESICNE`** - Mensual).
  * **Definición de Columnas Clave:**
      * **`tipo_cuenta` (Frequency):** Determina la frecuencia del extracto/comisión.
      * **`tipo_transaccion` (Type):** `VYDAJ` (Gasto/Egreso), `PRIJEM` (Ingreso/Depósito), `VYBER` (Retiro de ATM).
      * **`operacion` (Operation):** Especifica la forma (Ej: `VYBER`=retiro de caja, `VYBER KARTOU`=retiro con tarjeta).
  * **Código SQL (Resumido):**
    ```sql
    SELECT a.frequency, t.type, t.operation, COUNT(*) AS num_transacciones, ROUND(SUM(t.amount), 2) AS volumen_total
    FROM berkafintech_db.dim_account a JOIN berkafintech_db.fact_transactions t ON a.account_id = t.account_id
    GROUP BY a.frequency, t.type, t.operation ORDER BY num_transacciones DESC;
    ```
-----

### 2\. Resultados Obtenidos (Datos Clave)

| Tipo Cuenta | Transacción | Operación | **Num. Transacciones** | Volumen Total (Ej: 8.9E8) |
| :--- | :--- | :--- | :--- | :--- |
| **POPLATEK MESICNE** | VYDAJ | VYBER | **191,805** | $\approx 898 \text{M}$ |
| POPLATEK MESICNE | VYDAJ | PREVOD NA UCET | 96,911 | $\approx 305 \text{M}$ |
| POPLATEK MESICNE | PRIJEM | UNKNOWN | 84,324 | $\approx 12 \text{M}$ |
| POPLATEK MESICNE | PRIJEM | VKLAD | 71,350 | $\approx 1,054 \text{M}$ |
| **POPLATEK TYDNE** | VYDAJ | VYBER | **12,518** | $\approx 118 \text{M}$ |
| POPLATEK TYDNE | PRIJEM | UNKNOWN | 5,227 | $\approx 1 \text{M}$ |
| **POPLATEK MESICNE** | VYDAJ | **VYBER KARTOU** | **3,804** | $\approx 8.5 \text{M}$ |
| **POPLATEK TYDNE** | VYDAJ | **VYBER KARTOU** | **143** | $\approx 0.4 \text{M}$ |

-----

### 3\. Análisis e *Insight* Valioso

#### 🔑 *Insight* Clave

1.  **Dominancia del Plan Mensual:** La inmensa mayoría de las transacciones, tanto de ingresos como de egresos, ocurren en cuentas de tipo **`POPLATEK MESICNE`** (Extracto Mensual). Este plan es, con diferencia, el principal motor de volumen y frecuencia transaccional.
2.  **El Plan Semanal (POPLATEK TYDNE):** A pesar de su intención de ser un plan para clientes de alta frecuencia, las cuentas **`POPLATEK TYDNE`** generan un **volumen de transacciones mucho menor** (Ej: 12,518 VYDAJ vs. 191,805 en Mensual). Esto sugiere que el plan Semanal **no está atrayendo al tipo de cliente de súper-alta frecuencia** para el que fue diseñado, o que su costo/estructura no es atractivo.
3.  **Bajo Uso de Tarjetas (VYBER KARTOU):** Los retiros realizados con tarjeta (`VYBER KARTOU`) son **muy marginales** en todos los tipos de cuenta (Ej: 3,804 y 143 transacciones) en comparación con el retiro directo (`VYBER`, 191,805 transacciones). Esto indica una **baja penetración o preferencia por el uso de la tarjeta de débito/crédito** para retiros.

#### 🎯 Implicaciones/Recomendaciones

  * **Reevaluación del Producto (POPLATEK TYDNE):** El plan Semanal no está cumpliendo su objetivo. Se debe **revisar el costo, la estructura de comisiones o los beneficios** de este tipo de cuenta para hacerla competitiva y justificar la frecuencia extra del extracto.
  * **Incentivos para Tarjetas:** Existe una **oportunidad significativa para aumentar el *engagement* y la digitalización** promoviendo el uso de tarjetas para retiros y compras. Podría ser mediante **reembolsos (cashback) o eliminación de comisiones** por `VYBER KARTOU` para alentar este comportamiento.
  * **Próximos Pasos:** Analizar la **rentabilidad promedio por cuenta** para los tres tipos de frecuencia. Si `POPLATEK MESICNE` domina la actividad pero `POPLATEK PO OBRATU` es más rentable, podría ser mejor enfocar la adquisición de nuevos clientes en este último plan.

-----

## 🛑 Análisis 7: Detección de Transacciones Anómalas (*Outliers*)

### 1\. Contexto de la *Query*

  * **Nombre del Análisis:** Detección de Transacciones Anómalas (Percentil 95+).
  * **Propósito:** Aislar las transacciones con **montos extremadamente altos** (aquellas que superan un umbral estadístico predefinido, como el percentil 95 o superior) para su **auditoría manual** y la detección de posibles patrones de fraude o lavado de dinero (AML).
  * **Filtro:** `is_amount_outlier = 1` (Transacciones etiquetadas como anómalas).
  * **Código SQL (Resumido):**
    ```sql
    SELECT trans_id, account_id, trans_type, operation, trans_amount, final_balance, '🚨 SOSPECHOSA' AS flag_fraude
    FROM berkafintech_db.v_customer_behavior
    WHERE is_amount_outlier = 1
    ORDER BY trans_amount DESC LIMIT 100;
    ```
-----

### 2\. Resultados Obtenidos (Patrones Clave en el Top 100)

El análisis del top 100 de las transacciones sospechosas revela dos patrones muy claros:

| Tipo de Patrón | Tipo Transacción | Operación | Frecuencia en Top 100 | Observaciones |
| :--- | :--- | :--- | :--- | :--- |
| **Patrón 1: Egreso de Riesgo** | `VYDAJ` (Gasto) | **`VYBER` (Retiro de Caja/ATM)** | Alto (Primeras 17 transacciones) | Montos muy altos (hasta 87,400). En algunos casos, el **saldo final es negativo** o cercano a cero, lo que implica sobregiro o vaciado de cuenta. |
| **Patrón 2: Ingreso Recurrente Anómalo** | `PRIJEM` (Ingreso) | **`PREVOD Z UCTU` (Transferencia)** | Dominante (Ej: Cuentas 2170, 1032, 5228) | Se observan **múltiples transacciones idénticas** (mismo monto) en la **misma cuenta (`account_id`)** a lo largo de **diferentes fechas** (mensualmente o semestralmente). |

-----

### 3\. Análisis e *Insight* Valioso

#### 🔑 *Insight* Clave

1.  **Riesgo de Egreso (Fraude/Vaciado):** Los *outliers* de egreso (`VYDAJ`/`VYBER`) son las transacciones de **mayor monto individual** y representan un riesgo de fraude o uso indebido, especialmente porque en varios casos el retiro deja la cuenta en **sobregiro ($ -11.0$ o $-929.1$)**.
2.  **Riesgo de Ingreso (AML/Lavado):** Un patrón más sutil, pero de alto riesgo, es la **recurrencia de ingresos grandes e idénticos** (`PRIJEM`/`PREVOD Z UCTU`) en las mismas cuentas (Ej: la cuenta 2170 recibió 74,770 en 6 fechas diferentes, la 1032 recibió 74,648 en 7 fechas). La naturaleza **repetitiva y exacta** de estos grandes ingresos a intervalos regulares (mensual, semestral) es una **alerta clásica de estructuración de transacciones (posible lavado de dinero o evasión)**.

#### 🎯 Implicaciones/Recomendaciones

  * **Acción Inmediata (Fraude/VYDAJ):** Investigar las cuentas con saldos negativos tras retiros anómalos. Implementar un **límite de retiro estricto** que evite sobregiros en estas operaciones.
  * **Acción Inmediata (AML/PRIJEM):** Crear una **regla de Monitoreo Transaccional** que identifique y alerte sobre **ingresos de *outlier* que se repitan con el mismo monto y la misma operación** en una sola cuenta dentro de un período de 6 o 12 meses. Estas cuentas (`account_id`) deben ser auditadas inmediatamente.
  * **Optimización del Modelo:** Recomendar al equipo de *Data Science* o Riesgo que el modelo de detección de *outliers* no solo busque montos altos, sino que también incorpore una **métrica de frecuencia o repetición de montos** para capturar mejor el riesgo de estructuración.

-----

## 📄 Resumen Ejecutivo de Hallazgos (Los 7 *Insights*)

Con esto, has completado un análisis de datos profundo que cruza riesgo, *engagement* y anomalías. Aquí están tus 7 *insights* principales consolidados:

| \# | Área | *Insight* Clave | Recomendación Estratégica |
| :--- | :--- | :--- | :--- |
| **1** | Riesgo Crediticio | La Tasa de *Default* en préstamos **'Very Large (300K+)' es 5x mayor** que en los pequeños (20.73%), indicando una falla crítica en la evaluación de riesgo para montos altos. | **Aplicar criterios de aprobación más estrictos** o aumentar significativamente el interés en préstamos $\ge 300\text{K}$. |
| **2** | Riesgo Demográfico | El riesgo de alto monto está concentrado en mujeres **jóvenes (18-24)** y mujeres de **mediana edad (45-54)**. | **Limitar el monto máximo** de préstamo para el segmento F 18-24 y priorizar la **cobranza** en F 45-54. |
| **3** | Riesgo Geográfico | Existe una correlación directa entre bajo salario y alto *default* (Ej: West Bohemia, 15.79%), pero la región **'north Bohemia' es una anomalía** de bajo riesgo a pesar del bajo salario. | **Restringir las aprobaciones** en las 3 regiones de alto riesgo e **investigar el factor mitigante** de 'north Bohemia' para replicarlo. |
| **4** | Comportamiento | El segmento **Femenino 25-34 es el más activo** en volumen de transacciones salientes (32,977 VYDAJ), mientras que M 35-44 y F 45-54 tienen el ingreso promedio más alto. | **Ofrecer productos de *cross-selling*** a F 25-34 (ej: tarjetas con *cashback*) y **productos de inversión** a los segmentos de alto ingreso. |
| **5** | Lealtad/Adopción | La base de clientes es **extremadamente activa**, con el **86.5%** en el segmento de 'Alta Actividad' y casi cero inactividad. | Enfocar la estrategia en ***uplifting*** (mover las 613 cuentas de Actividad Media a Alta) en lugar de en reactivación. |
| **6** | Productos/Frecuencia | El plan de extracto **`POPLATEK TYDNE` (Semanal) no atrae alta actividad** y el **uso de tarjetas es muy bajo** para retiros. | **Reestructurar o descontinuar el plan Semanal** e incentivar fuertemente el uso de `VYBER KARTOU` (retiros con tarjeta) para aumentar la digitalización. |
| **7** | Fraude/AML | Hay dos patrones de *outliers*: **Retiros con sobregiro (`VYDAJ`/`VYBER`)** y **depósitos idénticos, recurrentes y anómalos (`PRIJEM`/`PREVOD Z UCTU`)** en la misma cuenta. | **Implementar alertas** para retiros que causen sobregiro y para **ingresos idénticos y recurrentes** que sugieren estructuración o lavado de dinero (AML). |
Este es un trabajo de síntesis y análisis crucial. Vamos a integrar los 7 *insights* detallados de tus *queries* de Athena con la evidencia visual proporcionada en los informes (`Resumen_Ejecutivo.pdf`, `Analisis_de_Clientes.pdf`, `Analisis_de_Fraude.pdf`) para generar una **Conclusión Ejecutiva** completa.

[cite_start]La base del análisis es la salud financiera de **4,500 Cuentas Activas** [cite: 109] [cite_start]que representan un **Monto Total de Cartera Activa de $\text{€}18.6\text{M}$**[cite: 102].

---

## 🚀 Conclusión Ejecutiva: Análisis de Cartera, Riesgo y Comportamiento

El principal hallazgo de este análisis es que la institución financiera presenta una **base de clientes altamente activa y comprometida**, pero enfrenta un **riesgo crediticio sistémico y concentrado** que requiere una intervención inmediata en las políticas de aprobación de préstamos.

### 1. Riesgo Crediticio y Cartera (El Desafío Principal)

[cite_start]La Tasa de *Default* general de la cartera se sitúa en un **11%** [cite: 111][cite_start], con un **Capital en Incumplimiento de $\text{€}16\text{M}$**[cite: 192], indicando que el riesgo actual está afectando significativamente el balance.

| Hallazgo Clave (Integración) | Evidencia Crucial | Implicación Estratégica |
| :--- | :--- | :--- |
| **Falla en Montos Altos (Insight 1)** | Los préstamos **'Very Large' ($\ge 300\text{K}$) tienen una Tasa de *Default* del 20.73%** (5 veces mayor que los pequeños). | El modelo de riesgo es débil para la alta exposición. Se requiere **suspender o aplicar criterios de evaluación mucho más estrictos** a los montos grandes. |
| **Riesgo Concentrado Geográficamente (Insight 3)** | El riesgo está focalizado en distritos específicos con bajo salario. [cite_start]Por ejemplo, **Brno-mesto** presenta una Tasa de *Default* del **21%** [cite: 163][cite_start], y **Ostrava-mesto** del **19%**[cite: 168]. | La segmentación geográfica es crucial para la tarificación. Se debe **aplicar un recargo o restricción inmediata** para solicitantes en distritos de alto riesgo. |
| **Riesgo Concentrado Demográficamente (Insight 2)** | Los préstamos más riesgosos se concentran en mujeres jóvenes (18-24) con el monto promedio más alto, y mujeres de mediana edad (45-54). | Se deben **revisar las políticas de préstamo** para el género femenino en estos rangos de edad, especialmente limitando el monto máximo para el segmento más joven. |

### 2. Comportamiento y *Engagement* (La Gran Oportunidad)

La base de clientes demuestra una salud de *engagement* excepcional. [cite_start]Las **transacciones de Ingreso/Depósito (PRIJEM) superan a las de Gasto/Pago (VYDAJ)** en volumen[cite: 326, 327], y el **86.5%** de los clientes están en el segmento de **'Alta Actividad'** (Insight 5), lo que minimiza el costo de reactivación.

| Hallazgo Clave (Integración) | Evidencia Crucial | Implicación Estratégica |
| :--- | :--- | :--- |
| **Motores de Transacción (Insight 4)** | **Femenino 25-34** es el segmento más activo en volumen de egresos (`VYDAJ`), y los segmentos **M 35-44 / F 45-54** tienen el ingreso promedio más alto. | **Foco en *Cross-Selling***: Venta de productos transaccionales (tarjetas, *cashback*) a F 25-34 y productos de valor (inversión, *wealth management*) a los segmentos de alto ingreso. |
| **Falla en el Producto Semanal (Insight 6)** | El plan de cuenta **`POPLATEK TYDNE` (Semanal)** no logra capturar a clientes de alta frecuencia y presenta bajo volumen transaccional en comparación con el plan mensual. | **Reestructurar o descontinuar el plan Semanal** y redirigir a los clientes a productos más rentables o de mayor *engagement*. |
| **Baja Digitalización (Insight 6)** | El uso de tarjetas para retiros (`VYBER KARTOU`) es marginal, predominando el retiro directo (`VYBER`). | Existe una **oportunidad significativa para fomentar la digitalización** mediante incentivos de *cashback* o la eliminación de comisiones por uso de tarjeta. |

### 3. Detección de Fraude y Riesgo Operacional (Foco AML)

[cite_start]El sistema ha identificado **29K Transacciones Sospechosas**[cite: 191], de las cuales el análisis revela dos patrones de alto riesgo (Insight 7):

| Patrón Identificado | Evidencia Crucial | Acción de Auditoría |
| :--- | :--- | :--- |
| **Fraude/Vaciado** | [cite_start]Se observan transacciones anómalas de retiro (`VYDAJ`/`VYBER`) que resultan en un **Balance Final Negativo** o cercano a cero[cite: 181]. | [cite_start]**Ajustar el límite de retiro** para evitar sobregiros y auditar las cuentas con balance negativo en el historial[cite: 207]. |
| **Estructuración (AML)** | Múltiples cuentas presentan un patrón de **ingresos idénticos y recurrentes** (`PRIJEM`/`PREVOD Z UCTU`) de montos altos, a intervalos regulares. | **Implementar una regla de monitoreo** que alerte sobre la repetición de montos anómalos en el tiempo para investigar posible estructuración o lavado de dinero. |

---

### **Recomendaciones Prioritarias (Resumen Ejecutivo)**

La acción más urgente es la mitigación del riesgo crediticio, ya que impacta la salud financiera general:

1.  **Revisión Inmediata de Riesgo Crediticio:** Aumentar la tasa de interés y/o suspender la aprobación de préstamos en el segmento **'Very Large ($\ge 300\text{K}$)'** y en los distritos de alta morosidad (Brno-mesto, Ostrava-mesto, etc.).
2.  **Monitoreo Transaccional Reforzado:** Implementar una regla de alerta para el patrón de **ingresos recurrentes de monto idéntico** (riesgo AML) y para cualquier retiro que lleve el saldo a territorio negativo.
3.  **Capitalizar el *Engagement*:** Lanzar una campaña de **venta cruzada dirigida** de productos de inversión a los segmentos de mayor ingreso (M 35-44, F 45-54) y una campaña de tarjetas para el segmento más activo (F 25-34).


# 🏦 Análisis de Cartera BERKA FINTECH: Prioridades de Riesgo y Oportunidades de Crecimiento

## 📅 Fecha de Presentación

2 de Diciembre de 2025

## 👥 Resumen Ejecutivo

[cite_start]La institución financiera (BERKA FINTECH) gestiona actualmente **4,500 Cuentas Activas** [cite: 248] [cite_start]con una **cartera de préstamos activa de $\text{€}18.6\text{M}$**[cite: 7]. La base de clientes es **extremadamente activa** (86.5% con alta actividad), lo que representa una gran oportunidad de venta cruzada. [cite_start]Sin embargo, la salud de la cartera está comprometida por un **riesgo crediticio concentrado** que contribuye a una **Tasa de *Default* general del 11%** [cite: 16] [cite_start]y un **Capital en Incumplimiento de $\text{€}16\text{M}$**[cite: 97].

La prioridad estratégica debe ser la mitigación inmediata del riesgo en el origen del préstamo, seguida de la capitalización del alto *engagement* del cliente.

---

## 🛑 1. Principal Desafío: Riesgo Crediticio Sistémico

El análisis demuestra que el riesgo de incumplimiento no es aleatorio, sino que está **estructuralmente concentrado** por monto, geografía y demografía.

### 1.1 Falla Crítica en la Evaluación de Préstamos Grandes

* **Hallazgo:** La Tasa de *Default* en préstamos **'Very Large' ($\ge 300\text{K}$) alcanza el 20.73%** (5 veces mayor que los préstamos pequeños) [Insight 1].
* **Implicación:** El modelo de riesgo actual es insuficiente para evaluar la complejidad y el riesgo de montos altos.

### 1.2 Concentración Geográfica del Riesgo

* [cite_start]**Hallazgo:** El riesgo está impulsado por regiones con salarios promedio bajos, como **Brno-mesto** (Tasa de *Default* del **21%**) [cite: 68] [cite_start]y **Ostrava-mesto** (Tasa de *Default* del **19%**)[cite: 73].
* **Anomalía:** **North Bohemia** presenta un riesgo inusualmente bajo (1.64%) a pesar de tener salarios medios similares a los de alto riesgo [Insight 3].

### 1.3 Perfil Demográfico de Alto Riesgo

* **Hallazgo:** El riesgo de alto monto está concentrado en mujeres **jóvenes (18-24)** y mujeres de **mediana edad (45-54)** [Insight 2].
* **Mitigación:** Se requiere limitar el monto máximo aprobado para mujeres jóvenes.

---

## 📈 2. Oportunidades: Comportamiento y Venta Cruzada

[cite_start]La base de clientes es una fuente de ingresos estable, con un volumen de **Ingresos/Depósitos (PRIJEM)** superior al de **Gastos/Pagos (VYDAJ)**[cite: 231, 232].

### 2.1 Identificación de Clientes Objetivo (Targeting)

* **Alto *Engagement* (Transacciones):** El segmento **Femenino 25-34** es el más activo en volumen de egresos, ideal para **ofertas de tarjetas y *cashback*** [Insight 4].
* **Alto Valor (Ingreso):** Los clientes **Hombres 35-44** y **Mujeres 45-54** presentan el mayor monto promedio de ingresos, siendo el *target* principal para **productos de Inversión y Gestión Patrimonial** [Insight 4].

### 2.2 Desafíos de Producto y Adopción

* **Ineficiencia del Producto Semanal:** El plan **`POPLATEK TYDNE`** (Extracto Semanal) no atrae alta actividad [Insight 6].
* **Baja Digitalización:** El uso de tarjetas para retiros (`VYBER KARTOU`) es marginal, predominando el retiro directo, lo que indica una **baja adopción de la tarjeta como herramienta de retiro** [Insight 6].

---

## 🚨 3. Monitoreo y Fraude (Riesgo Operacional)

[cite_start]El sistema ha identificado **29K Transacciones Sospechosas**[cite: 96], lo que exige un refuerzo de los controles.

* **Patrón de Egreso:** Hay transacciones anómalas de retiro (`VYDAJ`/`VYBER`) que resultan en **saldos finales negativos** [Insight 7].
* **Alerta AML (Anti-Lavado de Dinero):** Se identificó un patrón de **ingresos idénticos y recurrentes** de montos altos en las mismas cuentas, una señal de **estructuración** o posible lavado [Insight 7].

---

## 🎯 Plan de Acción Prioritario

| Prioridad | Acción | Impacto Esperado |
| :--- | :--- | :--- |
| **P1. Riesgo Crediticio** | **Restricción de Origen:** Endurecer los criterios de aprobación para préstamos **$\ge 300\text{K}$** y aplicar filtros geográficos para distritos de alto riesgo (Ej: Brno-mesto, Ostrava-mesto). | [cite_start]Reducción directa del **Capital en Incumplimiento ($\text{€}16\text{M}$)** y la Tasa de *Default* del 11%[cite: 97, 16]. |
| **P2. Riesgo Operacional** | Implementar una **regla de Monitoreo Transaccional (AML)** para alertar sobre ingresos idénticos y recurrentes en el tiempo. | Mitigación del riesgo de lavado de dinero y prevención de pérdidas por fraude de sobregiro. |
| **P3. Crecimiento** | Lanzar campañas de **venta cruzada hiper-dirigidas** para ofrecer productos de inversión a los segmentos de mayor ingreso. | Aumento de ingresos por comisiones y mayor rentabilidad por cliente. |

---

