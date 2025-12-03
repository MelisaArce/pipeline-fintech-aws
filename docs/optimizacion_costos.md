# Documentación: Optimización de Costos y Eficiencia (FinOps)

La optimización de costos fue un pilar fundamental durante el desarrollo del proyecto. Desde las primeras etapas tomé decisiones arquitectónicas y metodológicas orientadas a maximizar la eficiencia y minimizar el consumo de recursos en AWS, sin sacrificar la capacidad analítica del sistema.

---

## 1. Logro Financiero

El costo total asociado al desarrollo, implementación y pruebas del *pipeline* ETL completo se mantuvo **por debajo del umbral de los 40 USD** (precisamente, **$10,54**). Este resultado es consecuencia directa de las decisiones de optimización que diseñé e implementé durante todo el proyecto.

![optimizacion](../img/Captura%20desde%202025-12-02%2016-16-04.png)
---

## 2. Decisiones de Optimización Implementadas (3+)

A continuación, detallo las decisiones clave que tomé para garantizar un uso eficiente de recursos y minimizar el costo operativo en AWS:

### 2.1. Formato de Almacenamiento Eficiente (Parquet)

* **Decisión:** Convertí los archivos de datos brutos (CSV) al formato **Apache Parquet** dentro de las capas **Processed** y **Curated** del Data Lake.
* **Justificación:** Parquet es un formato columnar altamente comprimido, lo que reduce el **costo de almacenamiento en S3** y permite **consultas más rápidas** en Glue y Athena. Esto se traduce en menor costo de ejecución y mayor eficiencia en el análisis.

---

### 2.2. Particionamiento para Ahorro de Lectura

* **Decisión:** Implementé particionamiento en las tablas de mayor volumen —especialmente `fact_transactions`— dentro de S3.
* **Justificación:** El particionamiento permite que los motores de consulta escaneen únicamente las particiones necesarias (por ejemplo, por año o por mes). Esto reduce significativamente la cantidad de datos leídos, que es la métrica clave para el costo tanto en Athena como en Glue, mejorando a su vez la velocidad de respuesta.

---

### 2.3. Entornos de Prueba Locales (LocalStack)

* **Decisión:** Utilicé **LocalStack** para simular S3, Glue y otros servicios de AWS durante el desarrollo.
* **Justificación:** Al probar y depurar los Jobs ETL en un entorno local, evité múltiples ejecuciones innecesarias en la nube. Esto redujo de forma sustancial los costos asociados al tiempo de cómputo en Glue y me permitió desarrollar de manera continua sin incurrir en gastos adicionales.

---

### 2.4. Control Futuro del RDS (Roadmap)

* **Decisión (Roadmap):** Planifiqué la implementación de una función AWS **Lambda** destinada a automatizar el encendido y apagado de la instancia de **MySQL RDS**.
* **Justificación:** Las bases de datos RDS representan uno de los costos más altos dentro de la arquitectura. Mantener la instancia apagada cuando no está en uso garantiza que solo se incurra en costos de almacenamiento, y no de cómputo.

---

## 3. Control de Recursos Inactivos

Para asegurar el cumplimiento del principio de **"Recursos detenidos cuando no están en uso"**, implementé dos estrategias complementarias:

1. **Gestión del Ciclo de Vida (CloudFormation):**
   Al definir todos los recursos mediante Infrastructure as Code, puedo **crear y eliminar completamente** la infraestructura (RDS, Glue, S3, IAM, etc.) con un solo comando. Esto asegura que ningún recurso costoso quede activo accidentalmente fuera de los períodos de trabajo.

2. **Entorno de Desarrollo Controlado:**
   Realicé el desarrollo del código ETL principalmente en un entorno local simulado mediante **LocalStack**, reservando el uso de los servicios reales de AWS únicamente para la carga final de datos y la validación del modelo. Esto permitió reducir al mínimo los costos asociados a pruebas y ejecuciones intermedias.


