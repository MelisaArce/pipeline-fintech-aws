🚀 Proyecto ETL - Análisis Bancario Berka

Este repositorio contiene el *pipeline* de Extracción, Transformación y Carga (ETL) desarrollado en **PySpark** para procesar los datos históricos del dataset bancario Berka, transformándolos de una capa **Raw** a una capa **Processed** y, finalmente, a una capa **Curated** optimizada para el análisis.

El proyecto está diseñado para ser ejecutado de forma local usando **LocalStack** (simulando AWS S3) y en producción usando **AWS Glue**.

## 🏗️ Estructura del Proyecto

```
/berka-etl-pipeline
├── docker-compose.yml              # Configuración de los contenedores (Spark, LocalStack, PostgreSQL)
├── spark-submit-local.sh           # Script para ejecutar los jobs en modo LocalStack
├── raw_csv_transform_w_local.py    # Job ETL: Raw (CSV) -> Processed (Parquet)
├── curated_job.py                  # Job ETL: Processed -> Curated (S3)
└── rds_load_job.py                 # Job ETL: Curated -> RDS (Próximo paso)
```

## 1\. Configuración de Entorno Local (Docker Compose)

El archivo `docker-compose.yml` define los servicios necesarios para simular el entorno de nube (**LocalStack**) y la base de datos de destino (**PostgreSQL**), permitiendo el desarrollo y prueba de los Jobs Spark de forma aislada.

### `docker-compose.yml`

```yaml
version: '3.8'

services:
  # 1. Base de Datos de Destino (Data Warehouse)
  db:
    image: postgres:15-alpine
    container_name: berka-postgres-db
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: berka_dw
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - berka_network

  # 2. LocalStack (Simulador de AWS S3)
  localstack:
    container_name: localstack_berka
    image: localstack/localstack:latest
    ports:
      - "4566:4566"        # Puerto API de LocalStack
      - "4571:4571"
    environment:
      # Activar solo los servicios que se necesitan para ahorrar recursos
      SERVICES: s3,rds,iam
      # Configurar la región y usar el hostname del contenedor
      AWS_DEFAULT_REGION: us-east-1
      DOCKER_HOST: unix:///var/run/docker.sock
    volumes:
      - ./data:/tmp/data  # Montar un volumen para archivos de inicialización (opcional)
      - "/var/run/docker.sock:/var/run/docker.sock"
    networks:
      - berka_network
    
  # 3. Contenedor del Cliente Spark (Para ejecutar spark-submit)
  spark-client:
    container_name: berka-spark-client
    # Imagen oficial de Spark para PySpark
    image: bitnami/spark:3.5.0
    command: ["tail", "-f", "/dev/null"] # Mantener el contenedor vivo
    environment:
      # Configuración de Spark para conectar a LocalStack
      SPARK_LOCAL_IP: "spark-client"
      AWS_ACCESS_KEY_ID: test
      AWS_SECRET_ACCESS_KEY: test
    volumes:
      # Montar los scripts ETL y los datos RAW
      - ./jobs:/opt/bitnami/spark/jobs
      - ./data/raw:/data/raw
    networks:
      - berka_network
    depends_on:
      db:
        condition: service_healthy
      localstack:
        condition: service_started

networks:
  berka_network:
    driver: bridge
```

### 📋 Pasos de Ejecución Local

1.  **Levantar Contenedores:**
    ```bash
    docker compose up -d
    ```
2.  **Copiar datos Raw a S3 simulado (LocalStack):**
    Una vez que los contenedores estén corriendo, debes copiar tus archivos CSV (`account.csv`, `client.csv`, etc.) del directorio local `./data/raw` al *bucket* `berka-data-lake` en LocalStack.
3.  **Ejecutar los Jobs ETL:** Usa el script auxiliar `spark-submit-local.sh` dentro del contenedor `spark-client`.

## 2\. Scripts ETL de PySpark (Jobs)

Ambos scripts usan el patrón de **Configuración Adaptativa** que detecta la variable de entorno `EXECUTION_MODE`.

  * **Modo `GLUE` (Default):** Usa las librerías de `awsglue`, obtiene parámetros de `getResolvedOptions`, y usa el protocolo `s3://`.
  * **Modo `LOCAL`:** Inicializa una `SparkSession` con la configuración de `s3a://localhost:4566` y usa parámetros *hardcodeados*.

-----

### 2.1. `raw_csv_transform_w_local.py` (Raw → Processed)

Este Job se encarga de la limpieza y estandarización inicial de los archivos CSV brutos.

#### 🎯 Tareas Principales

  * **Carga Adaptativa:** Usa el protocolo `s3a://` en local y `s3://` en AWS.
  * **Limpieza de Nombres:** Normaliza todos los nombres de columnas a *snake\_case* y elimina caracteres especiales/comillas.
  * **Conversión de Fechas:** Convierte el formato histórico AAMMDD a `yyyy-MM-dd` (asumiendo 19XX).
  * **Imputación Funcional:** Rellena valores nulos (`NULL`, `vacío`, `-`) en columnas categóricas (`k_symbol`, `operation`) con etiquetas de negocio como `NO_SYMBOL` o `UNKNOWN`.
  * **Tipado:** Convierte columnas a los tipos de datos correctos (`IntegerType`, `DoubleType`, `DateType`).
  * **Salida:** Escribe los DataFrames limpios a la capa **Processed** en formato **Parquet**, particionando por columnas clave (`frequency`, `type`, `status`).

-----

### 2.2. `curated_job.py` (Processed → Curated)

Este es el Job de **Feature Engineering** y Agregación, construyendo el modelo dimensional final.

#### 🎯 Tareas Principales

  * **Enriquecimiento Dimensional:**
      * **CLIENT:** Calcula `gender`, `age_at_1998` y `age_segment` a partir del `birth_number`.
      * **LOAN:** Calcula `loan_end_date`, el *flag* binario `is_risky`, y ratios financieros.
      * **ACCOUNT:** Se enriquece con datos demográficos de `DISTRICT`, el `client_id` del propietario (`OWNER`) y la antigüedad de la cuenta.
  * **Feature Engineering Avanzado:**
      * **TRANSACTIONS:** Calcula el `initial_balance` usando funciones de ventana (`lag`) y agrega métricas rodantes (ej., `avg_trans_amount_3m`).
      * Crea *flags* de *outliers* basados en el percentil 95.
  * **Agregación de Hechos (Facts):**
      * Crea `fact_account_transactions` con métricas globales y promedio mensual de transacciones.
      * Crea `fact_account_summary` (la tabla estrella principal) consolidando todas las dimensiones y hechos a nivel de cuenta, incluyendo la creación del `customer_segment` (Premium, Loan, Card, Basic).
  * **Resolución de Ambigüedad:** Se incluye la corrección para renombrar `df_card.type` a **`type_card`** para evitar el error `[AMBIGUOUS_REFERENCE]` al unir con `df_disp`.

-----

## 3\. Guía de Despliegue en AWS Glue (Producción)

Para ejecutar estos Jobs en AWS, solo necesitas subir el script y configurar el Job de Glue.

### 📝 Requerimientos AWS

1.  **S3:** Los buckets deben estar configurados para albergar las capas **Raw**, **Processed**, y **Curated**.
2.  **IAM Role:** Necesitas un Rol de IAM para AWS Glue con las siguientes políticas:
      * `AWSGlueServiceRole` (para Glue en general).
      * **S3 R/W** (Lectura/Escritura) para los prefijos `RAW_PREFIX`, `PROCESSED_PREFIX`, y `CURATED_PREFIX`.
      * **Secret Manager R/W** (si vas a usar credenciales seguras para RDS).
3.  **VPC/Subnet/Security Group (Solo para Job de RDS):** El Job de RDS necesitará ejecutarse dentro de la VPC que contenga la instancia de RDS.

### ⚙️ Configuración del Job de Glue

Al crear un nuevo Job de Glue, usarás los siguientes **Parámetros de Job** (en la pestaña "Job details" o "Configuración"):

| Clave (Key) | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `--S3_BUCKET` | Nombre del bucket principal de S3. | `berka-data-lake-prod` |
| `--RAW_PREFIX` | Prefijo de la capa RAW. | `raw/berka/` |
| `--PROCESSED_PREFIX` | Prefijo de la capa PROCESSED. | `processed/berka/` |
| `--CURATED_PREFIX` | Prefijo de la capa CURATED. | `curated/berka/` |
| `--JOB_NAME` | Nombre para identificar el Job. | `berka-etl-raw-processed` |

El script automáticamente usará el protocolo `s3://` y las credenciales del Rol de IAM, ya que la variable `EXECUTION_MODE` por defecto será `GLUE`.