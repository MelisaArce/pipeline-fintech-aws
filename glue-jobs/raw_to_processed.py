import sys
import os
from pyspark.context import SparkContext
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, trim, regexp_replace, when, length,
    to_date, year, concat, lit, substring,
    lower, regexp_extract, coalesce
)
from pyspark.sql.types import StringType, IntegerType, DoubleType, DateType


# ============================================================================
# ⚠️ IMPORTACIONES CONDICIONALES PARA AWS GLUE ⚠️
# ============================================================================

# 1. Definir el modo de ejecución
EXECUTION_MODE = os.environ.get('EXECUTION_MODE', 'GLUE')
print(f"[INFO] Modo de Ejecución: {EXECUTION_MODE}")

if EXECUTION_MODE == 'GLUE':
    S3_PROTOCOL = "s3"
    print("[INFO] Usando protocolo S3 nativo de AWS (s3://)")
    # --- Importaciones exclusivas de AWS Glue ---
    try:
        from awsglue.transforms import *
        from awsglue.utils import getResolvedOptions
        from awsglue.context import GlueContext
        from awsglue.job import Job
        print("[INFO] Librerías de AWS Glue importadas con éxito.")
    except ImportError:
        print("[ERROR] Fallo al importar librerías de AWS Glue en modo GLUE. Terminando.")
        sys.exit(1)
else:
    S3_PROTOCOL = "s3a"
    print("[INFO] Usando protocolo S3A para LocalStack (s3a://)")


# ============================================================================
# CONFIGURACIÓN INICIAL ADAPTATIVA
# ============================================================================

if EXECUTION_MODE == 'LOCAL':
    # --- MODO LOCALSTACK (spark-submit) ---
    S3_BUCKET = "berka-data-lake"
    RAW_PREFIX = 'raw/berka/'
    PROCESSED_PREFIX = 'processed/berka/'
    JOB_NAME = 'berka-etl-job-local'

    # LEER ENDPOINT DESDE VARIABLE DE ENTORNO (pasado por el script bash)
    AWS_ENDPOINT = os.environ.get('AWS_ENDPOINT_URL', 'http://localstack:4566')
    AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID', 'test')
    AWS_SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'test')
    
    print(f"[INFO] AWS Endpoint configurado: {AWS_ENDPOINT}")

    # Inicialización de Spark Session configurada para acceder a LocalStack S3
    spark = SparkSession.builder \
        .appName(JOB_NAME) \
        .config("spark.hadoop.fs.s3a.endpoint", AWS_ENDPOINT) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .getOrCreate()

    sc = spark.sparkContext

    # Simulaciones mínimas para evitar errores de referencia de Glue
    class DummyContext:
        def __init__(self, spark_session):
            self.spark_session = spark_session
    glueContext = DummyContext(spark)

    class DummyJob:
        def init(self, *args):
            pass
        def commit(self):
            print("[INFO] Simulación de job.commit() completada.")
    job = DummyJob()
    
else:
    # --- MODO AWS GLUE REAL ---
    args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_BUCKET', 'RAW_PREFIX', 'PROCESSED_PREFIX'])

    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)

    # Parámetros S3
    S3_BUCKET = args['S3_BUCKET']
    RAW_PREFIX = args['RAW_PREFIX']
    PROCESSED_PREFIX = args['PROCESSED_PREFIX']

print(f"[INFO] Bucket S3: {S3_BUCKET}")
print(f"[INFO] Prefijo Raw: {RAW_PREFIX}")
print(f"[INFO] Prefijo Processed: {PROCESSED_PREFIX}")
print(f"[INFO] Protocolo S3: {S3_PROTOCOL}")
    
# ============================================================================
# FUNCIONES DE TRANSFORMACIÓN
# ============================================================================

def clean_column_names(df: DataFrame) -> DataFrame:
    """
    Limpia nombres de columnas: elimina comillas, espacios, convierte a minúsculas y snake_case.
    """
    for col_name in df.columns:
        clean_name = col_name.strip().replace('"', '').lower().replace(' ', '_')
        df = df.withColumnRenamed(col_name, clean_name)
    return df


def convert_berka_date(df: DataFrame, date_columns: list) -> DataFrame:
    """
    Convierte fechas en formato AAMMDD (entero) a YYYY-MM-DD (Date).
    Ejemplo: 930101 → 1993-01-01. Asume siglo 19.
    """
    for date_col in date_columns:
        if date_col in df.columns:
            df = df.withColumn(
                f"{date_col}_str",
                when(col(date_col).isNotNull(), 
                     regexp_replace(col(date_col).cast(StringType()), r'(\d{2})(\d{2})(\d{2})', 
                                    r'19$1-$2-$3'))
            )
            
            df = df.withColumn(
                date_col,
                to_date(col(f"{date_col}_str"), 'yyyy-MM-dd')
            ).drop(f"{date_col}_str")
    
    return df


def convert_berka_datetime(df: DataFrame, datetime_columns: list) -> DataFrame:
    """
    Convierte fechas con formato 'AAMMDD HH:MM:SS' a solo fecha YYYY-MM-DD.
    Ejemplo: '931107 00:00:00' → 1993-11-07
    """
    for dt_col in datetime_columns:
        if dt_col in df.columns:
            df = df.withColumn(
                f"{dt_col}_date_part",
                substring(col(dt_col).cast(StringType()), 1, 6)
            )
            
            df = df.withColumn(
                f"{dt_col}_formatted",
                regexp_replace(col(f"{dt_col}_date_part"), r'(\d{2})(\d{2})(\d{2})', r'19$1-$2-$3')
            )
            
            df = df.withColumn(
                dt_col,
                to_date(col(f"{dt_col}_formatted"), 'yyyy-MM-dd')
            ).drop(f"{dt_col}_date_part", f"{dt_col}_formatted")
    
    return df


def impute_functional_nulls(df: DataFrame, columns_to_impute: dict) -> DataFrame:
    """
    Imputa valores nulos/vacíos con etiquetas de negocio.
    """
    for col_name, replacement in columns_to_impute.items():
        if col_name in df.columns:
            df = df.withColumn(
                col_name,
                when(
                    (col(col_name).isNull()) | (trim(col(col_name)) == ''),
                    lit(replacement)
                ).otherwise(col(col_name))
            )
    return df


def rename_demographic_columns(df: DataFrame) -> DataFrame:
    """
    Renombra columnas crípticas de DEMOGRAPHIC a nombres legibles.
    """
    column_mapping = {
        'a1': 'district_id', 'a2': 'district_name', 'a3': 'region',
        'a4': 'population', 'a5': 'num_cities_lt_499', 'a6': 'num_cities_500_1999',
        'a7': 'num_cities_2000_9999', 'a8': 'num_cities_gt_10000',
        'a9': 'num_cities', 'a10': 'urban_ratio', 'a11': 'average_salary',
        'a12': 'unemployment_rate_95', 'a13': 'unemployment_rate_96',
        'a14': 'num_entrepreneurs_per_1000', 'a15': 'num_crimes_95',
        'a16': 'num_crimes_96'
    }
    
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            df = df.withColumnRenamed(old_name, new_name)
    
    return df


def cast_numeric_columns(df: DataFrame, column_types: dict) -> DataFrame:
    """
    Convierte columnas a tipos numéricos apropiados.
    """
    for col_name, target_type in column_types.items():
        if col_name in df.columns:
            df = df.withColumn(col_name, col(col_name).cast(target_type))
    
    return df


# ============================================================================
# PROCESAMIENTO POR TABLA
# ============================================================================

def process_account(s3_path: str) -> DataFrame:
    """Procesa la tabla ACCOUNT"""
    print("[INFO] Procesando ACCOUNT...")
    df = spark.read.option("header", "true").option("sep", ";").csv(s3_path)
    df = clean_column_names(df)
    df = convert_berka_date(df, ['date'])
    df = cast_numeric_columns(df, {
        'account_id': IntegerType(),
        'district_id': IntegerType()
    })
    return df


def process_client(s3_path: str) -> DataFrame:
    """Procesa la tabla CLIENT"""
    print("[INFO] Procesando CLIENT...")
    df = spark.read.option("header", "true").option("sep", ";").csv(s3_path)
    df = clean_column_names(df)
    df = cast_numeric_columns(df, {
        'client_id': IntegerType(),
        'district_id': IntegerType()
    })
    return df


def process_disp(s3_path: str) -> DataFrame:
    """Procesa la tabla DISP (Disposition)"""
    print("[INFO] Procesando DISP...")
    df = spark.read.option("header", "true").option("sep", ";").csv(s3_path)
    df = clean_column_names(df)
    df = cast_numeric_columns(df, {
        'disp_id': IntegerType(),
        'client_id': IntegerType(),
        'account_id': IntegerType()
    })
    return df


def process_loan(s3_path: str) -> DataFrame:
    """Procesa la tabla LOAN"""
    print("[INFO] Procesando LOAN...")
    df = spark.read.option("header", "true").option("sep", ";").csv(s3_path)
    df = clean_column_names(df)
    df = convert_berka_date(df, ['date'])
    df = cast_numeric_columns(df, {
        'loan_id': IntegerType(),
        'account_id': IntegerType(),
        'amount': DoubleType(),
        'duration': IntegerType(),
        'payments': DoubleType()
    })
    return df


def process_order(s3_path: str) -> DataFrame:
    """Procesa la tabla ORDER"""
    print("[INFO] Procesando ORDER...")
    df = spark.read.option("header", "true").option("sep", ";").csv(s3_path)
    df = clean_column_names(df)
    df = impute_functional_nulls(df, {'k_symbol': 'NO_SYMBOL'})
    df = cast_numeric_columns(df, {
        'order_id': IntegerType(),
        'account_id': IntegerType(),
        'amount': DoubleType()
    })
    return df


def process_trans(s3_path: str) -> DataFrame:
    """Procesa la tabla TRANS (Transactions) - La más grande y crítica"""
    print("[INFO] Procesando TRANS...")
    df = spark.read.option("header", "true").option("sep", ";").csv(s3_path)
    df = clean_column_names(df)
    df = convert_berka_date(df, ['date'])
    df = impute_functional_nulls(df, {
        'bank': 'INTERNO',
        'account': 'NA_CASH',
        'k_symbol': 'NO_SYMBOL',
        'operation': 'UNKNOWN'
    })
    df = cast_numeric_columns(df, {
        'trans_id': IntegerType(),
        'account_id': IntegerType(),
        'amount': DoubleType(),
        'balance': DoubleType()
    })
    return df


def process_card(s3_path: str) -> DataFrame:
    """Procesa la tabla CARD"""
    print("[INFO] Procesando CARD...")
    df = spark.read.option("header", "true").option("sep", ";").csv(s3_path)
    df = clean_column_names(df)
    df = convert_berka_datetime(df, ['issued'])
    df = cast_numeric_columns(df, {
        'card_id': IntegerType(),
        'disp_id': IntegerType()
    })
    return df

def process_demographic(s3_path: str) -> DataFrame:
    """Procesa la tabla DEMOGRAPHIC (District)"""
    print("[INFO] Procesando DISTRICT/DEMOGRAPHIC...")
    df = spark.read.option("header", "true").option("sep", ";").csv(s3_path)
    df = clean_column_names(df)
    df = rename_demographic_columns(df)
    df = cast_numeric_columns(df, {
        'district_id': IntegerType(),
        'population': IntegerType(),
        'average_salary': IntegerType(),
        'unemployment_rate_95': DoubleType(),  # <--- CORRECCIÓN 1: Faltaba y debe ser Double
        'unemployment_rate_96': DoubleType(),  # <--- CORRECCIÓN 2: Faltaba y debe ser Double
        'num_entrepreneurs_per_1000': IntegerType(),
        'num_crimes_95': IntegerType(),
        'num_crimes_96': IntegerType()
    })
    return df


# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

def main():
    """Ejecuta el pipeline ETL completo"""
    
    print("\n" + "=" * 80)
    print("🚀 INICIANDO PIPELINE ETL: RAW → PROCESSED")
    print("=" * 80)
    
    # Mapeo de archivos y funciones de procesamiento
    table_processors = {
        'account': process_account,
        'client': process_client,
        'disp': process_disp,
        'loan': process_loan,
        'order': process_order,
        'trans': process_trans,
        'card': process_card,
        'district': process_demographic
    }
    
    # Estrategia de particionamiento por tabla
    partition_strategies = {
        'account': ['frequency'],
        'client': None,
        'disp': ['type'],
        'loan': ['status'],
        'order': None,
        'trans': ['type'],
        'card': ['type'],
        'district': None
    }
    
    for table_name, processor_func in table_processors.items():
        try:
            # Construir rutas S3 con protocolo adaptativo
            raw_path = f"{S3_PROTOCOL}://{S3_BUCKET}/{RAW_PREFIX}{table_name}.csv"
            processed_path = f"{S3_PROTOCOL}://{S3_BUCKET}/{PROCESSED_PREFIX}{table_name}/"
            
            print(f"\n📊 Procesando tabla: {table_name.upper()}")
            print(f"   📥 Raw path: {raw_path}")
            
            # Procesar tabla
            df_processed = processor_func(raw_path)
            
            # Obtener estrategia de particionamiento
            partition_cols = partition_strategies.get(table_name)
            
            # Escribir a S3 en formato Parquet
            writer = df_processed.write.mode("overwrite")
            
            # Aplicar particionamiento si está definido
            if partition_cols:
                writer = writer.partitionBy(*partition_cols)
                print(f"   🗂️  Particionando por: {', '.join(partition_cols)}")
            
            # Escribir con compresión snappy
            writer.option("compression", "snappy").parquet(processed_path)
            
            # Contar filas procesadas
            row_count = df_processed.count()
            
            print(f"   ✅ {table_name.upper()} procesado correctamente")
            print(f"   📈 Filas procesadas: {row_count:,}")
            print(f"   📤 Processed path: {processed_path}")
            print("   " + "-" * 76)
            
        except Exception as e:
            print(f"   ❌ ERROR procesando {table_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            # Continuar con las demás tablas en caso de error
            continue
    
    print("\n" + "=" * 80)
    print("✅ PIPELINE ETL RAW → PROCESSED COMPLETADO EXITOSAMENTE")
    print("=" * 80 + "\n")


# Ejecutar el job
if __name__ == "__main__":
    main()
    
    if EXECUTION_MODE == 'GLUE':
        job.commit()