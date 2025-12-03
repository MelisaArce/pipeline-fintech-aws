<div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
  
  <div style="flex: 1;">
    <h1>🧪 EDA del Dataset Berka</h1>
    <p>
      Este documento resume el Análisis Exploratorio de Datos (EDA) que realicé sobre el Dataset Bancario Berka. Este análisis fue la base fundamental para todas las decisiones posteriores del proyecto ETL, el diseño de mi Data Lake House, la construcción del modelo dimensional y los dashboards finales.
    </p>
  </div>

  <div style="flex-shrink: 0;">
    <img src="../img/logo-berka.png" alt="Logo Berka" width="150">
  </div>

</div>

---

# 1. 📌 Configuración Inicial

## 📚 Librerías Utilizadas

Para explorar el dataset utilicé las librerías estándar de análisis de datos en Python:

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
```

* **pandas** → para la exploración tabular
* **numpy** → para operaciones numéricas
* **matplotlib / seaborn** → para generar visualizaciones y distribuciones

## 📦 Archivos Analizados

El dataset Berka está compuesto por múltiples archivos separados, sin esquema y sin llaves relacionales explícitas:

* `account.csv`
* `client.csv`
* `card.csv`
* `district.csv`
* `disp.csv`
* `loan.csv`
* `order.csv`
* `trans.csv`

Esto implicó un esfuerzo extra para reconstruir relaciones y estandarizar esquemas.

## 🧪 Estrategia de Muestreo

Para optimizar tiempos y evitar cargas innecesarias —sobre todo en `trans.csv`, que es masivo— tomé una **muestra del 5%**:

```python
df_trans_sample = df_trans.sample(frac=0.05, random_state=42)
```

Gracias a esto pude analizar:

* volumen de transacciones
* montos atípicos
* distribución temporal
* comportamiento por tipo de operación

Este muestreo fue clave para avanzar rápido sin perder representatividad.

---

# 2. 🔍 Exploración por Tabla

## 🟦 2.1. CLIENT

Variables relevantes:

* `client_id`
* `birth_number`
* `district_id`

### 🔑 Insight importante

Descubrí que `birth_number` codifica **fecha de nacimiento y género**.
A partir de eso generé:

* `gender`
* `age`
* `age_segment`

Este hallazgo fue fundamental para el *Feature Engineering* y para los dashboards demográficos.

---

## 🟧 2.2. LOAN

Variables principales:

* `loan_id`, `account_id`, `amount`, `duration`, `payments`, `status`

### 🔎 Insights

* Los montos estaban muy desbalanceados.
* Los status (`A, B, C, D`) no venían documentados, pero pude inferir que **C y D representan riesgo / default**.
* Este insight me llevó a crear la variable **`is_risky`** en la capa Curated.

---

## 🟩 2.3. DISTRICT

Incluye variables socioeconómicas:

* salario promedio
* criminalidad
* desempleo
* población

### 🔎 Insights

Encontré correlaciones entre:

* **menor salario promedio** → mayores tasas de **default**
* ciertos distritos con patrones de riesgo más marcados

Esto justificó la creación de la dimensión **`dim_district`**.

---

## 🟪 2.4. TRANS (5% sample)

Variables clave:

* fecha
* monto
* tipo
* símbolo bancario

### 🔎 Insights

* Encontré outliers muy altos que requerían limpieza.
* Algunos `k_symbol` no tenían interpretación → los clasifiqué como `UNKNOWN`.
* Detecté patrones útiles para crear features como:

  * `avg_trans_amount_3m`
  * `initial_balance`

Estos features enriquecieron el modelo dimensional.

---

# 3. 🎯 Hallazgos que Guiaron Mi ETL

El EDA no fue un documento aislado: **fue el mapa** que definió todas mis decisiones del pipeline.

## 🔧 Limpieza (RAW → PROCESSED)

Implementé:

* estandarización `snake_case`
* conversiones de fecha
* imputaciones explícitas
* cast de tipos correctos
* detección de outliers

## 🧬 Feature Engineering (PROCESSED → CURATED)

A partir de lo que encontré en el EDA generé:

* extracción de género y edad
* segmentos demográficos
* balances iniciales
* promedios móviles de transacciones
* flag de riesgo crediticio

## 🏛️ Modelado Dimensional

Las tablas finales nacieron directamente del conocimiento exploratorio:

* `dim_client`
* `dim_loan`
* `dim_account`
* `dim_district`
* `fact_account_transactions`
* `fact_account_summary`

---

# 4. 📊 Conclusiones del EDA

### ✔️ El dataset tenía suficiente riqueza para construir un **modelo dimensional completo y realista**.

### ✔️ Fue necesario un fuerte proceso de limpieza por inconsistencias de origen.

### ✔️ El EDA definió totalmente el camino del ETL:

* features demográficos
* métricas financieras
* clasificación de riesgo
* integración socioeconómica

### ✔️ También definió el enfoque de mis dashboards:

* riesgo por monto
* riesgo por edad
* riesgo por región

---
