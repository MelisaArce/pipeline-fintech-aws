<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px;">

  <!-- Texto del banner -->
  <div style="flex: 1;">
    <h1 style="margin: 0; font-size: 32px;">📊 Conclusiones del Dashboard — BERKA FINTECH</h1>
    <p style="margin: 5px 0 0; font-size: 18px;">
      Este documento resume los hallazgos, insights clave y conclusiones estratégicas que obtuve después de construir los dashboards en QuickSight. Estas conclusiones complementan mi EDA y justifican las decisiones que tomé en el pipeline ETL y en el diseño del modelo analítico.
    </p>
  </div>

  <!-- Logo a la derecha -->
  <img src="../img/logo-berka.png" alt="Logo Berka" width="140" style="margin-left: 20px;">
</div>

---

#  1. Mi Resumen Ejecutivo

Durante el análisis entendí que la institución financiera muestra una **base de clientes muy activa**, un volumen de préstamos grande y un nivel de riesgo que, si bien está controlado en general, presenta focos críticos.

**Mis puntos destacados:**

* ~4.500 cuentas activas → veo un **engagement elevado**.
* €103M en préstamos → indica un negocio grande y con movimiento.
* ~11% de *default* → manejable, pero con segmentos que preocupan.
* 59% de los préstamos están “running” → **cartera estable**.

---

#  2. Insights de Riesgo que Identifiqué

## 2.1 Riesgo Concentrado en Préstamos de Montos Altos

Cuando analicé los segmentos, descubrí que los préstamos "Very Large" (≥ €300K) tienen una Tasa de *Default* del **20.7%**, muchísimo más alta que el resto.

**Conclusión personal:** este segmento necesita **criterios más estrictos** y mayor control.

---

## 2.2 Riesgo Geográfico

Vi que algunas regiones tienen tasas de default demasiado altas:

* **Brno-mesto** y **Ostrava-mesto** → 19–21% de default.
* **North Bohemia** → casi sin default, a pesar de salarios similares.

**Conclusión:** tendría que aplicarse **política crediticia diferenciada**, porque el riesgo claramente no es homogéneo.

---

## 2.3 Riesgo Demográfico

Noté mayor riesgo especialmente en mujeres jóvenes (18–24) y mujeres de 45–54.

**Conclusión:** evaluar límites o criterios especiales para estos segmentos.

---

# 3. Oportunidades de Crecimiento que Detecté

## 3.1 Cross-Selling Basado en Segmentos

Analizando la actividad:

* Mujeres 25–34 → muy activas. Pueden ser un buen segmento para **tarjetas y consumo**.
* Hombres 35–44 y Mujeres 45–54 → altos ingresos. Ideales para **inversiones**.

**Conclusión:** hay mucho espacio para **campañas hiper-segmentadas**.

---

## 3.2 Comportamiento Transaccional

Noté que los ingresos superan a los gastos, lo que sugiere estabilidad.

Por otro lado, detecté **uso bajo de tarjetas**, lo que muestra baja digitalización.

**Conclusión:** promover productos digitales y beneficios asociados.

---

# 4. Riesgo Operacional y Posible Fraude

## 4.1 Transacciones Sospechosas

Encontré más de **29K transacciones anómalas**, con patrones repetitivos o saldos negativos.

**Conclusión:** esto amerita **reglas AML** y monitoreo inmediato.

---

## 4.2 Outliers de Alto Saldo

Las cuentas con más saldo resultaron ser las más propensas a anomalías.

**Conclusión:** monitoreo especial para cuentas de valor elevado.

---

# 5. Mi Plan Estratégico Final (Desde el Análisis)

| Prioridad | Acción que considero necesaria                                        | Impacto Esperado                                |
| --------- | --------------------------------------------------------------------- | ----------------------------------------------- |
| **P1**    | Endurecer criterios de préstamos ≥ €300K y aplicar filtros regionales | Menor riesgo crediticio y reducción del default |
| **P2**    | Implementar reglas AML detectando ingresos repetitivos                | Prevención de fraude y pérdidas operativas      |
| **P3**    | Campañas hipersegmentadas basadas en actividad e ingreso              | Incremento del revenue y engagement             |

---

#  6. Cómo Se Relaciona Esto con Mi ETL y Arquitectura

Todo lo que pude ver en los dashboards fue posible gracias al pipeline que construí:

* En la capa **Curated** generé las métricas y features que necesitaba.
* Limpieza y estandarización permitieron tener regiones y transacciones consistentes.
* Definí estados del préstamo, rangos de monto y agregaciones para QuickSight.

**Sin el EDA, este pipeline y este dashboard, estos insights no hubiesen sido posibles.**

---

# 📎 Archivos Relacionados

* 🏗️ Arquitectura del Pipeline — `docs/arquitectura.md`
* 🔍 EDA Completo — `docs/eda.md`
* 📊 Análisis de Negocio — `docs/analisis.md`
* 🎨 Metodología del Dashboard — `docs/metodologia_dashboard.md`
