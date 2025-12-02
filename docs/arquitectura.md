<!-- Banner: logo a la derecha, título a la izquierda -->
<div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
  <div>
    <h1>🏗️ Arquitectura y Diseño</h1>
  </div>
  <img src="../img/logo-berka.png" alt="logo berka" width="160" style="border-radius: 8px;">
</div>

## 📐 Diagrama de Arquitectura

![descripcion](./img/Arquitectura-berka.drawio.png)

El diseño sigue un **patrón de Data Lake House en AWS**, asegurando:

- Escalabilidad  
- Procesamiento distribuido  
- Persistencia relacional para BI  

---

## 🔄 Explicación del Flujo

### **1. Ingesta (RAW)**
Los datos CSV brutos se cargan inicialmente en el bucket S3 en la carpeta **raw/**.

### **2. Procesamiento (AWS Glue)**
Se ejecutan **dos Jobs PySpark**:

- **Job 1:** RAW → PROCESSED  
  _Limpieza, estandarización, tipado_
- **Job 2:** PROCESSED → CURATED  
  _Feature Engineering + Modelo Dimensional_

### **3. Data Warehouse (RDS)**
Un tercer Job de Glue toma la capa **curated/** y la carga en **MySQL RDS** (tablas dimensionales y de hechos).

### **4. Consumo (QuickSight)**
QuickSight se conecta a RDS para generar dashboards utilizando vistas pre-agregadas.

---

## 🛠️ Servicios AWS Usados y Por Qué

| Servicio AWS          | Propósito                                                        | Justificación |
|-----------------------|------------------------------------------------------------------|---------------|
| **Amazon S3**         | Almacenamiento Raw / Processed / Curated                        | Escalable, durable y económico. Ideal para Data Lake House. |
| **AWS Glue**          | Procesamiento ETL distribuido (PySpark)                         | Serverless, escalable, sin gestionar infraestructura. |
| **Amazon RDS (MySQL)**| Data Warehouse relacional final                                 | Baja latencia para BI, consultas SQL optimizadas para QuickSight. |
| **AWS CloudFormation**| Infraestructura como Código (IaC)                               | Despliegue reproducible y automatizado. |
| **AWS IAM**           | Gestión de roles y permisos                                     | Principio de privilegio mínimo en Glue, S3, RDS y Secrets Manager. |

---

## 🔐 Consideraciones de Seguridad

- **Aislamiento de Red:**  
  Glue y RDS operan dentro de una **VPC/Security Groups** dedicados.  
  Acceso externo a RDS restringido a la **IP autorizada**.

- **Credenciales Seguras:**  
  Uso de **AWS Secrets Manager** para manejar el JDBC de MySQL sin credenciales hardcodeadas.

- **Acceso a BI:**  
  QuickSight utiliza un usuario dedicado **quicksight_readonly**, evitando riesgos sobre los datos productivos.

---
