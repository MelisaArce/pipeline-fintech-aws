<div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
  <div style="flex: 1;">
    <h1>ANÁLISIS DE NEGOCIO Y RIESGO - BERKA FINTECH</h1>
    <p>
      <strong>OBJETIVO:</strong> Profundizar en el análisis del comportamiento del cliente y la detección de riesgo/anomalías para la gerencia de una Fintech.
    </p>
  </div>
  <div style="flex-shrink: 0;">
    <img src="../img/logo-berka.png" alt="logo berka" width="200">
  </div>
</div>

## **Introducción**

En este trabajo presento el análisis integral que realicé sobre el comportamiento crediticio, demográfico y transaccional de los clientes de **Berka Fintech**, a partir del dataset histórico utilizado para la construcción de un pipeline *end-to-end*. Mi objetivo fue comprender el riesgo asociado a distintos segmentos de clientes y detectar patrones relevantes para la toma de decisiones estratégicas.

A continuación detallo el proceso, los resultados más significativos y las conclusiones derivadas de cada uno de los cinco análisis principales.

### 1\. 🔍 Análisis 1: Tasa de *Default* por Segmento de Monto de Préstamo

  * **Nombre del Análisis:** Riesgo Crediticio por Segmento de Monto de Préstamo
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


### 1. Contexto y Enfoque

En primer lugar, decidí evaluar si existía una relación entre el monto del préstamo y su probabilidad de caer en *default*. Para esto, segmenté los préstamos en cuatro grupos: *Small*, *Medium*, *Large* y *Very Large*.

Mi propósito fue identificar si ciertos rangos de monto presentan un riesgo crediticio anormalmente elevado y, a partir de ello, evaluar la solidez del modelo actual de aprobación de préstamos.

### 2. Resultados Principales

Los datos evidencian que el segmento **Very Large (300K+)** presenta una tasa de *default* **20.73%**, muy superior al resto. A modo de referencia, los préstamos *Small* (<50K) presentan solo un **3.97%**.

Este patrón muestra una escalada consistente del riesgo a medida que el monto aumenta.

### 3. Interpretación y Reflexiones

Durante el análisis observé una **correlación directa entre el monto del préstamo y el riesgo de incumplimiento**. Esta relación me llevó a cuestionar la efectividad del modelo crediticio actual, especialmente para los montos más altos.

Considero prioritario revisar los criterios de aprobación para préstamos superiores a 300K, ya sea endureciendo las condiciones o aplicando tasas diferenciales. También propongo investigar más profundamente qué características comparten los clientes de alto monto que cayeron en *default*, ya que podría tratarse de un patrón no capturado por el modelo vigente.

-----

## 🔬 Análisis 2: Perfil Demográfico de Clientes con Préstamos Riesgosos

### 1\. Contexto de la *Query*

  * **Nombre del Análisis:** Perfil Demográfico (Edad y Género) del Riesgo Crediticio.
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

### 1. Objetivo y Proceso

En el segundo análisis busqué comprender cómo se distribuye el riesgo crediticio entre distintos segmentos demográficos, específicamente según **edad y género**. Para ello, filtré únicamente los préstamos marcados como *risky* y contabilicé cuántos correspondían a cada combinación demográfica.

### 2. Principales Hallazgos

Detecté que el riesgo se concentra principalmente en dos segmentos femeninos:

1. **Mujeres de 45-54 años**, con el mayor volumen de préstamos riesgosos.
2. **Mujeres de 18-24 años**, con el **monto promedio más alto** entre todos los grupos riesgosos.

Este segundo punto es especialmente relevante: clientes jóvenes con historial crediticio limitado están recibiendo préstamos de montos elevados.

### 3. Conclusiones

En términos académicos y operativos, esto revela una inconsistencia entre el perfil de riesgo esperado y las aprobaciones realizadas. Sugiero revisar la política crediticia de ambos segmentos, con especial énfasis en mujeres jóvenes, donde el impacto financiero de un *default* es mayor.

Como próximo paso, propongo unir este análisis con el anterior para confirmar si estas clientas están presentes en los segmentos *Large* o *Very Large*.

-----

## 🌎 Análisis 3: Correlación entre Salario Regional y Riesgo de Préstamo

### 1\. Contexto de la *Query*

  * **Nombre del Análisis:** Estabilidad Económica Distrital y Tasa de *Default*.
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

### 1. Enfoque Analítico

Mi intención en este análisis fue determinar si el entorno socioeconómico regional afecta el riesgo crediticio. Para ello, asocié el salario promedio de cada distrito con las tasas locales de *default*.

### 2. Resultados Observados

Los datos confirmaron mi hipótesis inicial: **las regiones con salarios más bajos presentan un riesgo significativamente mayor**.

Las tres regiones con mayor riesgo (*west Bohemia*, *north Moravia*, *south Bohemia*) muestran salarios entre 8,800 y 9,500, junto a tasas de *default* entre 15% y 16%.

Por el contrario, **Prague**, la región de mayor ingreso promedio, presenta una tasa notablemente más baja (8.33%).

Un caso especialmente interesante fue **north Bohemia**, una región que rompe la tendencia: salarios bajos pero una tasa mínima de *default* (1.64%).

### 3. Reflexión y Relevancia

Este hallazgo me llevó a cuestionar qué factores adicionales podrían estar contribuyendo a la estabilidad crediticia en esta región. Sugiero realizar un análisis de *clustering* para evaluar si existe un perfil financiero particular que pueda replicarse en otras zonas de riesgo.

-----

## 📈 Análisis 4: Patrones de Transacciones por Edad y Género

### 1\. Contexto de la *Query*

  * **Nombre del Análisis:** Comportamiento de *Engagement* (Ingreso vs. Gasto) Demográfico.
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

### 1. Objetivo

Busqué identificar qué segmentos demográficos presentan mayor actividad transaccional y cómo varían los montos promedio de ingresos y gastos.

### 2. Principales Resultados

Los hallazgos fueron consistentes y reveladores:

* **F 25-34** es el grupo con mayor volumen de transacciones de gasto, lo que indica un fuerte vínculo con el uso diario del sistema.
* **M 35-44** y **F 45-54** muestran los montos más altos de ingresos promedio.
* El segmento **65+ M** realiza muchos gastos de bajo monto, un patrón típico de usuarios jubilados.

### 3. Interpretación

Estos comportamientos permiten orientar estrategias diferenciadas:

* Venta cruzada para el segmento joven femenino.
* Productos de inversión para adultos de ingresos altos.
* Análisis específico para retiros en efectivo, dado el alto monto promedio.
-----

# **📊 Análisis 5: Segmentación de Clientes por Actividad Transaccional**

## 1. Propósito

Este análisis buscó clasificar a los clientes según su nivel de actividad, con el fin de identificar oportunidades de crecimiento y lealtad.

## 2. Resultados

La institución presenta una base de clientes altamente comprometida:

* **86.5%** de las cuentas se ubican en *Alta Actividad*.
* Solo 17 cuentas muestran *Baja Actividad*.
* No existen cuentas inactivas.

## 3. Conclusiones y Relevancia Operativa

En lugar de enfocarse en reactivar usuarios, la estrategia debería orientarse a potenciar la actividad, especialmente en las cuentas de actividad media. La base altamente activa también representa una excelente oportunidad para estrategias de venta cruzada.

---

# **📌 Conclusión General**

A lo largo de los cinco análisis identifiqué patrones consistentes que permiten comprender mejor tanto el riesgo crediticio como el comportamiento financiero de los clientes.

Los *insights* más relevantes se resumen en:

1. **Riesgo creciente con el monto del préstamo**, especialmente en el segmento Very Large.
2. **Concentración del riesgo demográfico** en mujeres jóvenes (por monto) y mujeres de mediana edad (por volumen).
3. **Influencia del salario regional** en la tasa de *default*, con anomalías que vale la pena investigar.
4. **Patrones de gasto y engagment** diferenciados según edad y género.
5. **Una base de clientes altamente activa**, lo que abre oportunidades para estrategias de crecimiento y fidelización.

Este proceso me permitió no solo analizar el comportamiento financiero del dataset, sino también reflexionar sobre las oportunidades de mejora y los puntos críticos para un sistema fintech real.

---


