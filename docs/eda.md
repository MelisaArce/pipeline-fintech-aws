# 🧪 EDA del Dataset Berka

Este documento resume el **Análisis Exploratorio de Datos (EDA)** realizado sobre el *Dataset Bancario Berka*. Este EDA fue la **base fundamental** para todas las decisiones posteriores del proyecto ETL, el diseño del Data Lake House, la construcción del modelo dimensional y los dashboards finales.

---

# 1. 📌 Configuración Inicial

## 📚 Librerías Utilizadas

Se utilizaron las librerías estándar para análisis de datos en Python:

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
```

* **pandas** → lectura y exploración tabular
* **numpy** → manipulación numérica
* **matplotlib / seaborn** → visualizaciones

## 📦 Archivos Analizados

El dataset incluye múltiples archivos independientes:

* `account.csv`
* `client.csv`
* `card.csv`
* `district.csv`
* `disp.csv`
* `loan.csv`
* `order.csv`
* `trans.csv`

Cada uno viene **sin esquema definido**, con formatos inconsistentes y sin claves relacionales explícitas.

## 🧪 Estrategia de Muestreo

Para evitar alto costo computacional (especialmente en `trans.csv`, con cientos de miles de filas):

```python
df_trans_sample = df_trans.sample(frac=0.05, random_state=42)
```

➡️ Se tomó **el 5% de las tablas** para exploraciones preliminares.

Esto permitió analizar:

* Volumen por tipo de transacción
* Montos atípicos
* Distribución de fechas
* Patrones de actividad por cuenta

---

# 2. 🔍 Exploración por Tabla

## 🟦 2.1. Tabla CLIENT

Variables clave:

* `client_id`
* `birth_number`
* `district_id`

### 🔑 Insight importante

El campo `birth_number` contenía **el género y fecha de nacimiento comprimidos**, lo cual permitió crear:

* **gender** (M/F)
* **age** al momento del análisis (1998)
* **age_segment** (clasificación útil para dashboard)

Esta extracción fue esencial para el Feature Engineering posterior.

---

## 🟧 2.2. Tabla LOAN

Variables:

* `loan_id`, `account_id`, `amount`, `duration`, `payments`, `status`

### 🔎 Insights

* Distribución muy desigual del **monto del préstamo**.
* Existencia de varios **status** (A, B, C, D) sin descripción.
* Se detectó que **status = C y D son defaults / high risk**, insight clave para el dashboard.

➡️ Esto llevó a crear la variable `is_risky` en la capa Curated.

---

## 🟩 2.3. Tabla DISTRICT

Incluye información socio-económica:

* salario promedio
* crimen
* población
* desempleo

### 🔎 Insights

* Las regiones con **salario promedio más bajo** correlacionan con **mayor default**.
* Información perfecta para enriquecer el Data Warehouse.

➡️ Esto justificó la creación de la tabla dimensión `dim_district`.

---

## 🟪 2.4. Tabla TRANS (muestra 5%)

Contenía:

* fecha
* monto
* tipo de operación
* símbolo bancario

### 🔎 Insights

* Existían **montos extremadamente altos** que requerían limpieza.
* Algunos `k_symbol` no tenían significado → se imputó `UNKNOWN`.
* Se detectaron patrones de gasto útiles para features:

  * `avg_trans_amount_3m`
  * `initial_balance`

➡️ Estos features fueron utilizados para el modelado dimensional.

---

# 3. 🎯 Hallazgos que Guiaron el ETL

Cada decisión del ETL provino directamente del EDA.

## 🔧 Limpieza (RAW → PROCESSED)

* Estandarizar nombres a `snake_case`.
* Convertir fechas de `AAMMDD` → `YYYY-MM-DD`.
* Imputación explícita de valores nulos.
* Casting correcto de tipos.

## 🧬 Feature Engineering (PROCESSED → CURATED)

* Extracción de género y edad.
* Segmentos demográficos.
* Balance inicial.
* Montos promedio móviles.
* Flag de riesgo crediticio.

## 🏛️ Modelado Dimensional

Creación de:

* `dim_client`
* `dim_loan`
* `dim_account`
* `dim_district`
* `fact_account_transactions`
* `fact_account_summary`

Toda la estructura se definió gracias a los insights del EDA.

---

# 4. 📊 Conclusiones del EDA

### ✔️ El dataset contenía suficiente riqueza para construir un **modelo dimensional realista**.

### ✔️ Fue necesario aplicar mucha limpieza debido a inconsistencias.

### ✔️ Los hallazgos guiaron por completo el ETL:

* extracción de features clave (edad, riesgo)
* integración socioeconómica (salario / distrito)
* cálculo de métricas financieras

### ✔️ El EDA permitió definir el enfoque del dashboard:

* Riesgo por monto
* Riesgo demográfico
* Sensibilidad regional
