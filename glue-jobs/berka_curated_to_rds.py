import sys
import os
from pyspark.context import SparkContext
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col
from pyspark.sql.types import DoubleType, IntegerType, StringType, DateType

# ============================================================================
# ⚠️ CONFIGURACIÓN DUAL-MODE ⚠️
# ============================================================================

EXECUTION_MODE = os.environ.get('EXECUTION_MODE', 'GLUE')
print(f"[INFO] Modo de Ejecución: {EXECUTION_MODE}")

if EXECUTION_MODE == 'GLUE':
    S3_PROTOCOL = "s3"
    print("[INFO] Usando protocolo S3 nativo de AWS (s3://)")
    
    from awsglue.transforms import *
    from awsglue.utils import getResolvedOptions
    from awsglue.context import GlueContext
    from awsglue.job import Job
    print("[INFO] Librerías de AWS Glue importadas exitosamente.")
    
    args = getResolvedOptions(sys.argv, [
        'JOB_NAME', 
        'S3_BUCKET', 
        'CURATED_PREFIX',
        'JDBC_URL',
        'JDBC_USER',
        'JDBC_PASSWORD',
        'EXECUTION_MODE'
    ])
    
    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)
    
    S3_BUCKET = args['S3_BUCKET']
    CURATED_PREFIX = args['CURATED_PREFIX']
    
    # ✅ Credenciales desde parámetros del job
    JDBC_URL = args['JDBC_URL']
    JDBC_USER = args['JDBC_USER']
    JDBC_PASSWORD = args['JDBC_PASSWORD']
    
    print(f"[INFO] JDBC URL: {JDBC_URL}")
    print(f"[INFO] JDBC User: {JDBC_USER}")

else:
    # Modo LOCAL
    S3_PROTOCOL = "s3a"
    print("[INFO] Usando protocolo S3A para LocalStack (s3a://)")
    
    S3_BUCKET = "berka-data-lake"
    CURATED_PREFIX = 'curated/berka/'

    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'mysql')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'berka_warehouse')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'admin')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'password')
    
    JDBC_URL = f"jdbc:mysql://{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    JDBC_USER = MYSQL_USER
    JDBC_PASSWORD = MYSQL_PASSWORD
    
    AWS_ENDPOINT = os.environ.get('AWS_ENDPOINT_URL', 'http://localstack:4566')
    AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID', 'test')
    AWS_SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'test')
    
    print(f"[INFO] AWS Endpoint configurado: {AWS_ENDPOINT}")
    print(f"[INFO] MySQL Host: {MYSQL_HOST}:{MYSQL_PORT}")
    
    spark = SparkSession.builder \
        .appName('berka-curated-to-rds-local') \
        .config("spark.hadoop.fs.s3a.endpoint", AWS_ENDPOINT) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .getOrCreate()
    
    sc = spark.sparkContext
    
    class DummyContext:
        def __init__(self, spark_session):
            self.spark_session = spark_session
    glueContext = DummyContext(spark)
    
    class DummyJob:
        def init(self, *args): pass
        def commit(self): 
            print("[INFO] Simulación de job.commit() completada.")
    job = DummyJob()

print(f"[INFO] Bucket S3: {S3_BUCKET}")
print(f"[INFO] Prefijo Curated: {CURATED_PREFIX}")
print(f"[INFO] Protocolo S3: {S3_PROTOCOL}")

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def clean_dataframe_for_mysql(df: DataFrame) -> DataFrame:
    """
    Limpia un DataFrame antes de escribirlo a MySQL.
    Convierte tipos de datos problemáticos y maneja valores NULL.
    """
    print(f"   🧹 Limpiando DataFrame para MySQL...")
    print(f"      Filas originales: {df.count():,}")
    print(f"      Columnas: {len(df.columns)}")
    
    # Convertir tipos problemáticos
    for field in df.schema.fields:
        col_name = field.name
        col_type = str(field.dataType)
        
        # Convertir DecimalType a DoubleType
        if "DecimalType" in col_type:
            print(f"      Convirtiendo {col_name}: {col_type} → DoubleType")
            df = df.withColumn(col_name, col(col_name).cast(DoubleType()))
        
        # Convertir LongType a IntegerType si es seguro
        elif col_type == "LongType" and "id" not in col_name.lower():
            print(f"      Convirtiendo {col_name}: {col_type} → IntegerType")
            df = df.withColumn(col_name, col(col_name).cast(IntegerType()))
    
    # Renombrar columnas con caracteres especiales
    for col_name in df.columns:
        clean_name = col_name.replace('-', '_').replace(' ', '_').replace('.', '_').lower()
        if clean_name != col_name:
            print(f"      Renombrando columna: {col_name} → {clean_name}")
            df = df.withColumnRenamed(col_name, clean_name)
    
    return df


def load_curated_table(table_name: str) -> DataFrame:
    """
    Carga una tabla desde la capa Curated (formato Parquet).
    """
    path = f"{S3_PROTOCOL}://{S3_BUCKET}/{CURATED_PREFIX}{table_name}/"
    print(f"[INFO] Cargando {table_name} desde: {path}")
    return spark.read.parquet(path)


def write_to_mysql(df: DataFrame, table_name: str, write_mode: str = "overwrite"):
    """
    Escribe un DataFrame a MySQL con configuración optimizada.
    
    Args:
        df: DataFrame de Spark
        table_name: Nombre de la tabla en MySQL
        write_mode: 'overwrite' | 'append' | 'ignore'
    """
    print(f"\n{'='*80}")
    print(f"📤 Escribiendo tabla: {table_name}")
    print(f"   Modo: {write_mode}")
    
    row_count = df.count()
    print(f"   Filas: {row_count:,}")
    print(f"   Columnas: {len(df.columns)}")
    
    # Mostrar schema resumido
    print(f"\n   📋 Schema:")
    df.printSchema()
    
    # Mostrar muestra de datos
    print(f"\n   📊 Muestra (primeras 3 filas):")
    df.show(3, truncate=True)
    
    try:
        print(f"\n   🔌 Conectando a MySQL...")
        print(f"      URL: {JDBC_URL}")
        print(f"      Usuario: {JDBC_USER}")
        print(f"      Tabla destino: {table_name}")
        
        # ✅ CONFIGURACIÓN OPTIMIZADA PARA CONEXIÓN DIRECTA
        df.write \
            .mode(write_mode) \
            .format("jdbc") \
            .option("url", JDBC_URL) \
            .option("dbtable", table_name) \
            .option("user", JDBC_USER) \
            .option("password", JDBC_PASSWORD) \
            .option("driver", "com.mysql.cj.jdbc.Driver") \
            .option("batchsize", "1000") \
            .option("isolationLevel", "READ_UNCOMMITTED") \
            .option("truncate", "true") \
            .option("createTableOptions", "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4") \
            .option("useSSL", "false") \
            .option("allowPublicKeyRetrieval", "true") \
            .option("rewriteBatchedStatements", "true") \
            .option("connectTimeout", "60000") \
            .option("socketTimeout", "60000") \
            .save()
        
        print(f"   ✅ {table_name} escrito exitosamente")
        
        # Verificar escritura
        print(f"\n   🔍 Verificando escritura...")
        verify_count = spark.read \
            .format("jdbc") \
            .option("url", JDBC_URL) \
            .option("dbtable", f"(SELECT COUNT(*) as cnt FROM {table_name}) as count_query") \
            .option("user", JDBC_USER) \
            .option("password", JDBC_PASSWORD) \
            .option("driver", "com.mysql.cj.jdbc.Driver") \
            .load() \
            .collect()[0]['cnt']
        
        print(f"   ✅ Filas verificadas en MySQL: {verify_count:,}")
        
        if verify_count != row_count:
            print(f"   ⚠️  WARNING: Discrepancia! Esperadas: {row_count:,}, Encontradas: {verify_count:,}")
        
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"   ❌ ERROR al escribir {table_name}")
        print(f"   Tipo de error: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        
        # Debug info
        print(f"\n   🔍 Información de debug:")
        print(f"      Particiones del DataFrame: {df.rdd.getNumPartitions()}")
        print(f"      Tipos de datos: {[str(f.dataType) for f in df.schema.fields]}")
        
        import traceback
        traceback.print_exc()
        raise


# ============================================================================
# TRANSFORMACIONES FINALES PRE-CARGA
# ============================================================================

def prepare_dim_client(df: DataFrame) -> DataFrame:
    """Prepara dim_client para carga en MySQL"""
    columns_to_keep = [
        'client_id', 'birth_number', 'district_id',
        'gender', 'birth_date', 'age_at_1998', 'age_segment'
    ]
    
    existing_cols = [c for c in columns_to_keep if c in df.columns]
    df_selected = df.select(existing_cols)
    return clean_dataframe_for_mysql(df_selected)


def prepare_dim_account(df: DataFrame) -> DataFrame:
    """Prepara dim_account para carga en MySQL"""
    columns_to_keep = [
        'account_id', 'district_id', 'frequency', 'date',
        'owner_client_id', 'account_age_days', 'account_age_years',
        'account_age_segment', 'district_name', 'region',
        'average_salary', 'unemployment_rate_96'
    ]
    
    existing_cols = [c for c in columns_to_keep if c in df.columns]
    df_selected = df.select(existing_cols)
    return clean_dataframe_for_mysql(df_selected)


def prepare_dim_loan(df: DataFrame) -> DataFrame:
    """Prepara dim_loan para carga en MySQL"""
    columns_to_keep = [
        'loan_id', 'account_id', 'loan_start_date', 'loan_end_date',
        'amount', 'duration', 'payments', 'status', 'status_label',
        'is_risky', 'payment_to_amount_ratio', 'loan_amount_segment',
        'is_amount_outlier'
    ]
    
    existing_cols = [c for c in columns_to_keep if c in df.columns]
    df_selected = df.select(existing_cols)
    return clean_dataframe_for_mysql(df_selected)


def prepare_fact_account_summary(df: DataFrame) -> DataFrame:
    """Prepara fact_account_summary"""
    return clean_dataframe_for_mysql(df)


def prepare_fact_transactions(df: DataFrame) -> DataFrame:
    """Prepara fact_transactions"""
    columns_to_keep = [
        'trans_id', 'account_id', 'date', 'type', 'operation',
        'amount', 'initial_balance', 'final_balance', 'k_symbol',
        'is_amount_outlier', 'avg_trans_amount_3m', 'num_trans_3m'
    ]
    
    existing_cols = [c for c in columns_to_keep if c in df.columns]
    df_selected = df.select(existing_cols)
    return clean_dataframe_for_mysql(df_selected)


# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

def main():
    """
    Ejecuta el pipeline ETL completo de Curated a RDS MySQL.
    """
    print("\n" + "="*80)
    print("🚀 INICIANDO PIPELINE ETL: CURATED → RDS MYSQL")
    print("="*80 + "\n")
    
    # 1. Validar configuración
    print("[STEP 1] Validando configuración...")
    print(f"   JDBC URL: {JDBC_URL}")
    print(f"   Usuario: {JDBC_USER}")
    print(f"   S3 Bucket: {S3_BUCKET}")
    print(f"   Curated Prefix: {CURATED_PREFIX}")
    print("[SUCCESS] Configuración validada\n")
    
    # 2. Definir tablas a cargar
    tables_to_load = {
        # Dimensiones
        'dim_client': prepare_dim_client,
        'dim_account': prepare_dim_account,
        'dim_loan': prepare_dim_loan,
        'dim_district': lambda df: clean_dataframe_for_mysql(df),
        'dim_card': lambda df: clean_dataframe_for_mysql(df),
        'dim_disp': lambda df: clean_dataframe_for_mysql(df),
        'dim_order': lambda df: clean_dataframe_for_mysql(df),
        
        # Hechos
        'fact_account_transactions': lambda df: clean_dataframe_for_mysql(df),
        'fact_account_summary': prepare_fact_account_summary,
        'fact_transactions': prepare_fact_transactions,
    }
    
    # 3. Procesar y cargar cada tabla
    print("[STEP 2] Cargando tablas en MySQL...")
    success_count = 0
    error_count = 0
    failed_tables = []
    
    for table_name, prepare_func in tables_to_load.items():
        try:
            print(f"\n{'🔄'*40}")
            print(f"🔄 Procesando: {table_name}")
            print(f"{'🔄'*40}")
            
            # Cargar desde S3 Curated
            df_curated = load_curated_table(table_name)
            
            # Aplicar transformaciones finales
            df_prepared = prepare_func(df_curated)
            
            # Escribir a MySQL
            write_to_mysql(
                df=df_prepared,
                table_name=table_name,
                write_mode="overwrite"
            )
            
            success_count += 1
            
        except Exception as e:
            print(f"\n❌ ERROR CRÍTICO procesando {table_name}: {str(e)}")
            error_count += 1
            failed_tables.append(table_name)
            continue
    
    # 4. Resumen de ejecución
    print("\n" + "="*80)
    print(f"✅ PIPELINE CURATED → RDS COMPLETADO")
    print(f"   Exitosas: {success_count}/{len(tables_to_load)}")
    print(f"   Fallidas: {error_count}/{len(tables_to_load)}")
    
    if failed_tables:
        print(f"\n   ⚠️  Tablas que fallaron:")
        for table in failed_tables:
            print(f"      - {table}")
    
    print("="*80 + "\n")
    
    # 5. Validación post-carga
    if success_count > 0:
        print("[STEP 3] Validando carga en MySQL...")
        print("-" * 80)
        
        for table_name in tables_to_load.keys():
            if table_name in failed_tables:
                continue
                
            try:
                df_mysql = spark.read \
                    .format("jdbc") \
                    .option("url", JDBC_URL) \
                    .option("dbtable", table_name) \
                    .option("user", JDBC_USER) \
                    .option("password", JDBC_PASSWORD) \
                    .option("driver", "com.mysql.cj.jdbc.Driver") \
                    .load()
                
                count = df_mysql.count()
                print(f"   ✅ {table_name}: {count:,} filas en MySQL")
                
            except Exception as e:
                print(f"   ⚠️  {table_name}: Error al verificar - {str(e)}")
        
        print("-" * 80 + "\n")


if __name__ == "__main__":
    main()
    
    if EXECUTION_MODE == 'GLUE':
        job.commit()