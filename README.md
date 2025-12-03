<div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
  
  <div style="flex: 1;">
    <h1>🚀 Proyecto ETL - Análisis Bancario Berka</h1>
    <p>
      Este repositorio contiene el <em>pipeline</em> de Extracción, Transformación y Carga (ETL)
      desarrollado en <strong>PySpark</strong> para procesar los datos históricos del dataset bancario Berka,
      transformándolos de una capa <strong>Raw</strong> a una capa <strong>Processed</strong> y, finalmente, a una capa
      <strong>Curated</strong> optimizada para el análisis.
      <br><br>
      El proyecto está diseñado para ser ejecutado de forma local usando <strong>LocalStack</strong> (simulando servicios de AWS)
      y en producción usando <strong>AWS Glue</strong>.
    </p>
  </div>

  <div style="flex-shrink: 0;">
    <img src="./img/logo-berka.png" alt="Logo Berka" width="150">
  </div>

</div>

## 📘 Documentación Completa

- 🏗️ [Arquitectura del Pipeline](docs/arquitectura.md)
- 🔍 [EDA Completo](docs/eda.md)
- 📊 [Análisis de Negocio](docs/analisis.md)
- 🎨 [Metodología del Dashboard](docs/metodologia_dashboard.md)
- 🏦 [Dashboard Conclusiones](docs/dashboard_conclusiones.md)
- 💰 [Optimizacion de Costos](docs/optimizacion_costos.md)

## 🏗️ Estructura del Proyecto

| Elemento                                    | Tipo          | Descripción                                                                                        |
| ------------------------------------------- | ------------- | -------------------------------------------------------------------------------------------------- |
| **`/glue-jobs`**                            | Directorio    | Scripts PySpark listos para ejecutarse en AWS Glue.                                                |
| ├── `raw_to_processed.py`                   | Script        | Limpieza, estandarización y conversión RAW → PROCESSED.                                            |
| ├── `processed_to_curated.py`               | Script        | Feature Engineering, métricas financieras y creación del modelo dimensional (PROCESSED → CURATED). |
| └── `berka_curated_to_rds.py`               | Script        | Carga final de la capa Curated hacia MySQL RDS.                                                    |
| **`/local`**                                | Directorio    | Configuración del entorno local (LocalStack + Docker) y datos de ingesta.                          |
| ├── `/data_original`                        | Directorio    | Archivos CSV originales utilizados en el EDA y la ingesta RAW.                                     |
| ├── `EDA.ipynb`                             | Notebook      | Notebook del análisis exploratorio inicial (EDA).                                                  |
| ├── `run_job_local.sh`                      | Script        | Orquestador local completo del pipeline en Docker.                                                 |
| ├── `docker-compose.yml`                    | Configuración | Ambiente local que emula AWS (LocalStack, MySQL, Spark).                                           |
| **`/docs`**                                 | Directorio    | Documentación del proyecto.                                                                        |
| ├── `arquitectura.md`                       | Documento     | Explicación de la arquitectura y diseño del Data Lake House.                                       |
| ├── `metodologia_dashboard.md`              | Documento     | Lógica analítica, definiciones de KPIs y gobernanza de QuickSight.                                 |
| ├── `eda.md`                                | Documento     | EDA documentado que justifica decisiones del ETL y del dashboard.                                  |
| └── *otros documentos añadidos al proyecto* | —             | (mockups, decisiones técnicas, etc.)                                                               |
| **`/athena-queries`**                       | Directorio    | Consultas SQL utilizadas durante análisis intermedio o auditorías.                                 |
| └── `analisis_v4.sql`                          | Script SQL    | Ejecuciones de prueba/validación sobre capas procesadas.                                           |
| **`/MySql`**                                | Directorio    | Scripts SQL para creación de tablas destino en MySQL RDS.                                          |
| **`/quicksight`**                           | Directorio    | Mockups, PDFs y artefactos de diseño de tableros.                                                  |
| **`/img`**                                  | Directorio    | Logos, diagramas e imágenes usadas en documentación.                                               |
| **`README.md`**                             | Documentación | Visión general del proyecto, explicación funcional y técnica del pipeline.                         |
| **`deploy_to_aws_v2.sh`**                   | Script        | Despliegue automatizado de infraestructura y código con CloudFormation.                            |
| **`cloudformation_template_v6.yaml`**       | IaC           | Plantilla que define S3, RDS, IAM Roles, VPC y servicios AWS asociados.                            |


## 1\. Configuración de Entorno Local (Docker Compose)

El archivo `docker-compose.yml` define los servicios necesarios para simular el entorno de nube (**LocalStack**) y la base de datos de destino (**MySql**), permitiendo el desarrollo y prueba de los Jobs Spark de forma aislada.

### `docker-compose.yml`

```yaml
version: '3.8'

services:
  # 1. Base de Datos de Destino (Data Warehouse)
  mysql:
    image: mysql:8.0
    container_name: berka_mysql_db 
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: berka_warehouse
    ports:
      - "3306:3306" 
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - berka_network
    healthcheck:
        test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p$$MYSQL_ROOT_PASSWORD"]
        interval: 5s
        timeout: 5s
        retries: 5
        start_period: 20s

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

## 2\. Scripts ETL de PySpark (Jobs)

Ambos scripts usan el patrón de **Configuración Adaptativa** que detecta la variable de entorno `EXECUTION_MODE`.

  * **Modo `GLUE` (Default):** Usa las librerías de `awsglue`, obtiene parámetros de `getResolvedOptions`, y usa el protocolo `s3://`.
  * **Modo `LOCAL`:** Inicializa una `SparkSession` con la configuración de `s3a://localhost:4566` y usa parámetros *hardcodeados*.

-----

### 2.1. `raw_to_processed.py` (Raw → Processed)

Este Job se encarga de la limpieza y estandarización inicial de los archivos CSV brutos.

#### 🎯 Tareas Principales

  * **Carga Adaptativa:** Usa el protocolo `s3a://` en local y `s3://` en AWS.
  * **Limpieza de Nombres:** Normaliza todos los nombres de columnas a *snake\_case* y elimina caracteres especiales/comillas.
  * **Conversión de Fechas:** Convierte el formato histórico AAMMDD a `yyyy-MM-dd` (asumiendo 19XX).
  * **Imputación Funcional:** Rellena valores nulos (`NULL`, `vacío`, `-`) en columnas categóricas (`k_symbol`, `operation`) con etiquetas de negocio como `NO_SYMBOL` o `UNKNOWN`.
  * **Tipado:** Convierte columnas a los tipos de datos correctos (`IntegerType`, `DoubleType`, `DateType`).
  * **Salida:** Escribe los DataFrames limpios a la capa **Processed** en formato **Parquet**, particionando por columnas clave (`frequency`, `type`, `status`).

-----

### 2.2. `processed_to_curated.py` (Processed → Curated)

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
### 2.3. berka_curated_to_rds.py (Curated → RDS/MySQL)

Este es el Job de Ingesta y Persistencia, la etapa final del pipeline que mueve los modelos de datos dimensionales y las tablas de hechos (Facts) desde el Data Lake (capa Curated en S3) hacia el Data Warehouse relacional (RDS/MySQL). Este destino es el punto de consumo para herramientas de Business Intelligence (BI) y aplicaciones.

#### 🎯 Tareas Principales

* **Carga de Tablas Finales:** 
     * Carga todas las tablas dimensionales (dim_client, dim_account, dim_loan, etc.) y las tablas de hechos(fact_account_summary, fact_transactions, etc.) generadas por el job processed_to_curated.py desde la capa Curated de S3.
* **Limpieza y Adaptación para SQL (clean_dataframe_for_mysql):**
      * Tipado: Convierte tipos de datos de Spark que pueden ser problemáticos en MySQL (ej., DecimalType a DoubleType).
      * Normalización de Nombres: Elimina caracteres especiales (guiones -, espacios, puntos .) de los nombres de columnas y asegura el snake_case para la base de datos relacional.
* **Conexión Adaptativa:**
      * Utiliza los parámetros de conexión JDBC (JDBC_URL, JDBC_USER, JDBC_PASSWORD) obtenidos de manera segura: mediante getResolvedOptions en modo GLUE (producción) o a través de variables de entorno y valores hardcodeados en modo LOCAL (desarrollo).
* **Persistencia Optimizada (write_to_mysql):**

      * Escribe cada DataFrame a su tabla MySQL correspondiente en modo overwrite (reemplazo total de la tabla).
      * Aplica optimizaciones JDBC como batchsize, isolationLevel (READ_UNCOMMITTED) y rewriteBatchedStatements para una transferencia de datos eficiente y rápida.
      * Incluye un paso de Validación Post-escritura para verificar que el conteo de filas en Spark (df.count()) coincide con el conteo de filas en la tabla MySQL después de la carga, asegurando la integridad de los datos.

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

-----

## 4\. ⚙️ Detalle de Orquestación y Despliegue (Scripts Shell)

Esta sección explica la secuencia de comandos utilizada para ejecutar y validar los Jobs ETL tanto en el entorno de desarrollo local como en el entorno de producción de AWS Glue.

### 4.1. Guía de Ejecución Local (`run_job_local.sh`)

Este *script* es el **orquestador local** que gestiona la configuración de Docker, la carga de datos en el Data Lake simulado (LocalStack) y la ejecución secuencial de los Jobs PySpark, culminando con la validación de datos en MySQL.

| Fase | Tarea Principal | Comandos Clave | Propósito |
| :--- | :--- | :--- | :--- |
| **0 & 1. Preparación** | Levanta los contenedores Docker y limpia directorios locales (`processed`, `curated`) que podrían tener errores de permisos. | `docker compose up -d`, `sudo rm -rf...` | Asegura un estado limpio y reproducible para la ejecución. |
| **2 & 3. Health Checks** | Espera a que los servicios críticos (`LocalStack S3` y `MySQL`) estén operativos antes de continuar. | `curl... grep -q '"s3": "available"'`, `docker exec... mysqladmin ping` | Evita errores de conexión al intentar ejecutar Spark antes de que las dependencias estén listas (fundamental en Docker). |
| **4. Carga RAW** | Crea el *bucket* de S3 simulado y sincroniza los archivos CSV de la carpeta local (`./data/raw/berka/`) al *path* de S3 (`s3://berka-data-lake/raw/berka/`). | `aws s3 mb`, `aws s3 sync` | Simula la ingesta inicial de datos brutos en el Data Lake. |
| **5, 7 & 9. Ejecución ETL** | Ejecuta secuencialmente los tres Jobs PySpark (Raw → Processed → Curated → RDS) utilizando el comando `spark-submit` dentro del contenedor `spark-client`. | `docker exec... spark-submit --packages...` | Lanza el *pipeline* de transformación, asegurando que se utilizan los paquetes JDBC y Hadoop AWS necesarios para la conexión. |
| **6 & 8. Verificación** | Verifica que los Jobs intermedios crearon archivos en S3 y descarga una copia de las capas **Processed** y **Curated** al host local. | `aws s3 ls...`, `aws s3 sync...` | Permite al desarrollador inspeccionar la calidad y el formato Parquet de los datos generados. |
| **10. Validación Final** | Ejecuta consultas SQL directamente en el contenedor de MySQL para validar el conteo de filas, la calidad de datos (género, riesgo) y el formato de las tablas cargadas. | `docker exec... mysql -e "SELECT..."` | Confirma que el *pipeline* ha cargado la base de datos de destino con la integridad esperada. |
| **Cleanup** (Trap) | Detiene y elimina los contenedores Docker en caso de éxito o fallo del *script*. | `docker compose down` | Libera recursos del sistema después de la ejecución. |

-----

### 4.2. Guía de Despliegue en AWS Glue (`deploy_aws.sh`)

Este *script* está diseñado para un despliegue de **Infraestructura como Código (IaC)**. Su objetivo es crear todos los recursos de AWS (S3, RDS, IAM Roles, Security Groups, etc.) a través de **CloudFormation** y luego cargar los artefactos necesarios para la ejecución.

| Fase | Tarea Principal | Comando Clave | Propósito |
| :--- | :--- | :--- | :--- |
| **1 & 2. Validaciones** | Verifica la existencia de AWS CLI y credenciales, y obtiene información de la cuenta (ID, IP pública). | `aws sts get-caller-identity`, `curl https://api.ipify.org` | Previene fallos de despliegue por falta de configuración y obtiene la IP para configurar el acceso a RDS. |
| **3 & 4. CloudFormation** | Crea el *Stack* de CloudFormation, provisionando la VPC, el RDS y los Roles de IAM (incluyendo el Rol para Glue). Luego espera a que la creación se complete y obtiene los *outputs* clave. | `aws cloudformation create-stack...`, `aws cloudformation wait...` | Establece el ambiente de producción completo antes de cargar cualquier código o dato. |
| **5. Subir Scripts** | Sube los tres Jobs PySpark (`raw_to_processed.py`, etc.) al *bucket* de S3 creado por CloudFormation (en el *path* `/scripts`). | `aws s3 cp "$SCRIPTS_DIR/$JOB"...` | Prepara los artefactos de código para que los Jobs de AWS Glue puedan ser definidos y ejecutados. |
| **6. Subir Datos RAW** | Sincroniza el directorio local de datos originales (`./data_original`) al *path* de entrada de la capa RAW en S3 (`s3://$BUCKET_NAME/raw/berka/`). | `aws s3 sync "$RAW_DATA_DIR"...` | Asegura que el *pipeline* tenga los datos brutos disponibles para iniciar el procesamiento. |
| **7. Instrucciones** | Imprime los comandos finales de AWS CLI que el usuario debe ejecutar **manualmente** después de que el *script* haya finalizado. | `echo "aws glue start-job-run..."` | **El *script* despliega la infraestructura y el código, pero el usuario debe iniciar el flujo de ejecución y el Crawler de Glue.** |

#### 📝 Secuencia de Ejecución de Jobs en Producción (Manual)

Una vez que el *script* de despliegue finaliza, el flujo se controla mediante la consola de AWS Glue o la CLI:

1.  **Ejecutar Job 1 (Transformación):** RAW → PROCESSED.
    ```bash
    aws glue start-job-run --job-name <tu_nombre>-raw-to-processed
    ```
2.  **Ejecutar Job 2 (Feature Engineering):** PROCESSED → CURATED.
    ```bash
    aws glue start-job-run --job-name <tu_nombre>-processed-to-curated
    ```
3.  **Ejecutar Crawler:** Catalogar los datos Parquet de la capa CURATED en el AWS Glue Data Catalog.
    ```bash
    aws glue start-crawler --name <tu_nombre>-curated-crawler
    ```
4.  **Ejecutar Job 3 (Carga a RDS):** CURATED → RDS (MySQL).
    ```bash
    aws glue start-job-run --job-name <tu_nombre>-curated-to-rds
    ```