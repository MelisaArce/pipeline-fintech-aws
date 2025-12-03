import sys
import os
from pyspark.context import SparkContext
from pyspark.sql import DataFrame, Window
from pyspark.sql.functions import (
    col, when, substring, length, to_date, lit, concat,
    year, month, datediff, current_date, add_months,
    sum as _sum, count, avg, max as _max, min as _min,
    stddev, round as _round, coalesce, row_number,
    dense_rank, lag, lead, expr, ceil, trim
)
from pyspark.sql.types import IntegerType, DoubleType, StringType, DateType
from datetime import datetime

# ============================================================================
# ⚠️ CONFIGURACIÓN INICIAL Y ADAPTACIÓN DE ENTORNO ⚠️
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

    # Obtener parámetros del Job de Glue
    args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_BUCKET', 'PROCESSED_PREFIX', 'CURATED_PREFIX'])

    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)

    # Parámetros S3
    S3_BUCKET = args['S3_BUCKET']
    PROCESSED_PREFIX = args['PROCESSED_PREFIX']
    CURATED_PREFIX = args['CURATED_PREFIX']

else:
    # --- Configuración para LOCALSTACK (EXECUTION_MODE == 'LOCAL') ---
    S3_PROTOCOL = "s3a"
    print("[INFO] Usando protocolo S3A para LocalStack (s3a://)")
    
    from pyspark.sql import SparkSession

    # Parámetros para la ejecución local
    S3_BUCKET = "berka-data-lake"
    PROCESSED_PREFIX = 'processed/berka/'
    CURATED_PREFIX = 'curated/berka/'
    JOB_NAME = 'berka-curated-job-local'

    # LEER ENDPOINT DESDE VARIABLE DE ENTORNO
    AWS_ENDPOINT = os.environ.get('AWS_ENDPOINT_URL', 'http://localstack:4566')
    AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID', 'test')
    AWS_SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'test')
    
    print(f"[INFO] AWS Endpoint configurado: {AWS_ENDPOINT}")

    # Inicialización de Spark Session configurada para LocalStack S3
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

    # Simular GlueContext y Job
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

print(f"[INFO] Bucket S3: {S3_BUCKET}")
print(f"[INFO] Prefijo Processed: {PROCESSED_PREFIX}")
print(f"[INFO] Prefijo Curated: {CURATED_PREFIX}")
print(f"[INFO] Protocolo S3: {S3_PROTOCOL}")

# ============================================================================
# FUNCIONES DE CARGA DESDE PROCESSED
# ============================================================================

def load_processed_table(table_name: str) -> DataFrame:
    """Carga una tabla desde la capa Processed (formato Parquet)"""
    path = f"{S3_PROTOCOL}://{S3_BUCKET}/{PROCESSED_PREFIX}{table_name}/"
    print(f"[INFO] Cargando {table_name} desde: {path}")
    return spark.read.parquet(path)

# ============================================================================
# FEATURE ENGINEERING - DIMENSIONES ENRIQUECIDAS
# ============================================================================

def enrich_client_dimension(df_client: DataFrame) -> DataFrame:
    """
    Feature Engineering en CLIENT:
    - Extrae EDAD y GÉNERO desde birth_number
    - Calcula edad actual
    """
    df = df_client.withColumn("birth_number_str", col("birth_number").cast(StringType()))
    
    # Extraer año, mes, día
    df = df.withColumn("yy", substring(col("birth_number_str"), 1, 2).cast(IntegerType()))
    df = df.withColumn("mm", substring(col("birth_number_str"), 3, 2).cast(IntegerType()))
    df = df.withColumn("dd", substring(col("birth_number_str"), 5, 2).cast(IntegerType()))
    
    # Determinar género
    df = df.withColumn(
        "gender",
        when(col("mm") > 50, lit("F")).otherwise(lit("M"))
    )
    
    # Ajustar mes para mujeres
    df = df.withColumn(
        "birth_month",
        when(col("mm") > 50, col("mm") - 50).otherwise(col("mm"))
    )
    
    # Construir año completo
    df = df.withColumn(
        "birth_year",
        when(col("yy") < 100, 1900 + col("yy")).otherwise(col("yy"))
    )
    
    # Construir fecha de nacimiento
    df = df.withColumn(
        "birth_date",
        to_date(
            concat(
                col("birth_year").cast(StringType()),
                lit("-"),
                when(col("birth_month") < 10, concat(lit("0"), col("birth_month").cast(StringType())))
                    .otherwise(col("birth_month").cast(StringType())),
                lit("-"),
                when(col("dd") < 10, concat(lit("0"), col("dd").cast(StringType())))
                    .otherwise(col("dd").cast(StringType()))
            ),
            "yyyy-MM-dd"
        )
    )
    
    # Calcular edad al final del dataset
    reference_date = lit("1998-12-31").cast(DateType())
    df = df.withColumn(
        "age_at_1998",
        (year(reference_date) - year(col("birth_date")))
    )
    
    # Crear segmentos de edad
    df = df.withColumn(
        "age_segment",
        when(col("age_at_1998") < 25, lit("18-24"))
        .when(col("age_at_1998") < 35, lit("25-34"))
        .when(col("age_at_1998") < 45, lit("35-44"))
        .when(col("age_at_1998") < 55, lit("45-54"))
        .when(col("age_at_1998") < 65, lit("55-64"))
        .otherwise(lit("65+"))
    )
    
    # Limpiar columnas temporales
    df = df.drop("birth_number_str", "yy", "mm", "dd", "birth_month", "birth_year")
    
    return df


def standardize_categorical_columns(df: DataFrame, columns: list) -> DataFrame:
    """Estandariza columnas categóricas: TRIM + UPPER"""
    for col_name in columns:
        if col_name in df.columns:
            df = df.withColumn(
                col_name,
                trim(col(col_name)).cast(StringType())
            )
    return df


def enrich_loan_dimension(df_loan: DataFrame) -> DataFrame:
    """Feature Engineering en LOAN"""
    # Calcular fecha de finalización
    df = df_loan.withColumn(
        "loan_end_date",
        add_months(col("date"), col("duration"))
    )
    
    df = df.withColumnRenamed("date", "loan_start_date")
    
    # Variable target de riesgo
    df = df.withColumn(
        "is_risky",
        when(col("status").isin(["B", "D"]), lit(1)).otherwise(lit(0))
    )
    
    # Etiquetas descriptivas
    df = df.withColumn(
        "status_label",
        when(col("status") == "A", lit("Contract finished, no problems"))
        .when(col("status") == "B", lit("Contract finished, loan not paid"))
        .when(col("status") == "C", lit("Contract running, OK so far"))
        .when(col("status") == "D", lit("Contract running, client in debt"))
        .otherwise(lit("Unknown")).cast(StringType()) 
    )
    
    # Ratio de pago
    df = df.withColumn(
        "payment_to_amount_ratio",
        _round((col("payments") * col("duration")) / col("amount"), 4)
    )
    
    # Segmentos de monto
    df = df.withColumn(
        "loan_amount_segment",
        when(col("amount") < 50000, lit("Small (< 50K)"))
        .when(col("amount") < 150000, lit("Medium (50K-150K)"))
        .when(col("amount") < 300000, lit("Large (150K-300K)"))
        .otherwise(lit("Very Large (300K+)"))
    )
    
    df = standardize_categorical_columns(df, ["status"])
    
    return df


def enrich_account_dimension(df_account: DataFrame, df_district: DataFrame, 
                            df_disp: DataFrame, df_client: DataFrame) -> DataFrame:
    """Enriquece ACCOUNT con información completa"""
    # Join con district
    df = df_account.join(df_district, "district_id", "left")
    
    # Obtener owner
    df_owners = df_disp.filter(col("type") == "OWNER") \
                       .select("account_id", 
                              col("client_id").alias("owner_client_id"))
    
    df = df.join(df_owners, "account_id", "left")
    
    # Info del cliente propietario
    df_client_info = df_client.select(
        col("client_id").alias("owner_client_id"),
        col("gender").alias("owner_gender"),
        col("age_at_1998").alias("owner_age"),
        col("age_segment").alias("owner_age_segment")
    )
    
    df = df.join(df_client_info, "owner_client_id", "left")
    
    # Antigüedad de la cuenta
    reference_date = lit("1998-12-31").cast(DateType())
    df = df.withColumn(
        "account_age_days",
        datediff(reference_date, col("date"))
    )
    
    df = df.withColumn(
        "account_age_years",
        _round(col("account_age_days") / 365.25, 2)
    )
    
    # Segmentos de antigüedad
    df = df.withColumn(
        "account_age_segment",
        when(col("account_age_years") < 1, lit("New (< 1 year)"))
        .when(col("account_age_years") < 3, lit("Recent (1-3 years)"))
        .when(col("account_age_years") < 5, lit("Established (3-5 years)"))
        .otherwise(lit("Mature (5+ years)"))
    )
    
    df = df.withColumn("frequency", 
                      trim(col("frequency")).cast(StringType()))
    
    return df


def create_outlier_flags(df: DataFrame, amount_col: str, threshold_percentile: float = 0.95) -> DataFrame:
    """Crea flags para detectar outliers"""
    threshold = df.approxQuantile(amount_col, [threshold_percentile], 0.01)[0]
    
    df = df.withColumn(
        f"is_{amount_col}_outlier",
        when(col(amount_col) > threshold, lit(1)).otherwise(lit(0))
    )
    
    return df


def enrich_transactions_with_window_features(df_trans: DataFrame) -> DataFrame:
    """Enriquece TRANS con métricas de ventana temporal"""
    window_spec = Window.partitionBy("account_id").orderBy("date", "trans_id")
    
    df = df_trans.withColumn(
        "initial_balance",
        lag("balance", 1).over(window_spec)
    )
    
    df = df.withColumn(
        "initial_balance",
        when(col("initial_balance").isNull(),
             when(col("type") == "PRIJEM", col("balance") - col("amount"))
             .otherwise(col("balance") + col("amount")))
        .otherwise(col("initial_balance"))
    )
    
    df = df.withColumnRenamed("balance", "final_balance")
    
    # Métricas rolling 3 meses
    window_3m = Window.partitionBy("account_id") \
                      .orderBy(col("date").cast("long")) \
                      .rangeBetween(-90*86400, 0)
    
    df = df.withColumn("avg_trans_amount_3m", _round(avg("amount").over(window_3m), 2))
    df = df.withColumn("total_income_3m", _sum(when(col("type") == "PRIJEM", col("amount")).otherwise(0)).over(window_3m))
    df = df.withColumn("total_expense_3m", _sum(when(col("type") == "VYDAJ", col("amount")).otherwise(0)).over(window_3m))
    df = df.withColumn("num_trans_3m", count("*").over(window_3m))
    
    return df


def create_fact_account_transactions(df_trans: DataFrame) -> DataFrame:
    """Crea tabla de hechos agregada por cuenta"""
    fact_global = df_trans.groupBy("account_id").agg(
        count("*").alias("total_transactions"),
        _sum(when(col("type") == "PRIJEM", 1).otherwise(0)).alias("total_income_transactions"),
        _sum(when(col("type") == "VYDAJ", 1).otherwise(0)).alias("total_expense_transactions"),
        _sum(when(col("type") == "PRIJEM", col("amount")).otherwise(0)).alias("total_income_amount"),
        _sum(when(col("type") == "VYDAJ", col("amount")).otherwise(0)).alias("total_expense_amount"),
        avg("amount").alias("avg_transaction_amount"),
        _max("amount").alias("max_transaction_amount"),
        _min("amount").alias("min_transaction_amount"),
        stddev("amount").alias("stddev_transaction_amount"),
        _max("final_balance").alias("max_balance"),
        _min("final_balance").alias("min_balance"),
        avg("final_balance").alias("avg_balance"),
        _max("date").alias("last_transaction_date"),
        _min("date").alias("first_transaction_date")
    )
    
    fact = fact_global.withColumn("net_balance", col("total_income_amount") - col("total_expense_amount"))
    fact = fact.withColumn("income_to_expense_ratio",
        when(col("total_expense_amount") > 0, _round(col("total_income_amount") / col("total_expense_amount"), 4))
        .otherwise(lit(None)))
    fact = fact.withColumn("has_negative_balance", when(col("min_balance") < 0, lit(1)).otherwise(lit(0)))
    fact = fact.withColumn("days_active", datediff(col("last_transaction_date"), col("first_transaction_date")))
    fact = fact.withColumn("transactions_per_day",
        when(col("days_active") > 0, _round(col("total_transactions") / col("days_active"), 4))
        .otherwise(lit(None)))
    
    return fact


def create_fact_account_summary(df_account: DataFrame, df_trans_agg: DataFrame, 
                                df_loan: DataFrame, df_card: DataFrame, 
                                df_disp: DataFrame) -> DataFrame:
    """Crea tabla de hechos consolidada"""
    fact = df_account.join(df_trans_agg, "account_id", "left")
    
    loan_agg = df_loan.groupBy("account_id").agg(
        count("*").alias("num_loans"),
        _sum("amount").alias("total_loan_amount"),
        avg("amount").alias("avg_loan_amount"),
        _sum("is_risky").alias("num_risky_loans"),
        _max("is_risky").alias("has_risky_loan")
    )
    fact = fact.join(loan_agg, "account_id", "left")
    
    card_agg = df_card.join(df_disp, "disp_id", "inner") \
                      .groupBy("account_id").agg(
        count("*").alias("num_cards"),
        _max("type").alias("highest_card_type")
    )
    fact = fact.join(card_agg, "account_id", "left")
    
    numeric_cols = ["num_loans", "total_loan_amount", "avg_loan_amount", 
                    "num_risky_loans", "has_risky_loan", "num_cards"]
    
    for col_name in numeric_cols:
        if col_name in fact.columns:
            fact = fact.withColumn(col_name, coalesce(col(col_name), lit(0)))
    
    fact = fact.withColumn(
        "customer_segment",
        when((col("num_loans") > 0) & (col("num_cards") > 0), lit("Premium"))
        .when(col("num_loans") > 0, lit("Loan Customer"))
        .when(col("num_cards") > 0, lit("Card Customer"))
        .otherwise(lit("Basic"))
    )
    
    return fact


# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

def main():
    """Ejecuta el pipeline ETL completo de Processed a Curated"""
    
    print("\n" + "=" * 80)
    print("🚀 INICIANDO PIPELINE ETL: PROCESSED → CURATED")
    print("=" * 80)
    print(f"[INFO] Protocolo S3: {S3_PROTOCOL}://")
    print(f"[INFO] Bucket: {S3_BUCKET}")
    print(f"[INFO] Processed Prefix: {PROCESSED_PREFIX}")
    print(f"[INFO] Curated Prefix: {CURATED_PREFIX}")
    
    # ========================================================================
    # 1. CARGAR TODAS LAS TABLAS PROCESADAS
    # ========================================================================
    print("\n[STEP 1] Cargando tablas desde Processed...")
    
    try:
        df_account = load_processed_table("account")
        df_client = load_processed_table("client")
        df_disp = load_processed_table("disp")
        df_loan = load_processed_table("loan")
        df_order = load_processed_table("order")
        df_trans = load_processed_table("trans")
        df_card = load_processed_table("card")
        df_district = load_processed_table("district")
        
        print("[SUCCESS] Todas las tablas cargadas correctamente")
    except Exception as e:
        print(f"[ERROR] Fallo al cargar tablas: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # ========================================================================
    # 2. ENRIQUECER DIMENSIONES
    # ========================================================================
    print("\n[STEP 2] Aplicando Feature Engineering...")
    
    print("  - Enriqueciendo dim_client...")
    dim_client = enrich_client_dimension(df_client)
    
    print("  - Enriqueciendo dim_loan...")
    dim_loan = enrich_loan_dimension(df_loan)
    
    print("  - Enriqueciendo fact_transactions...")
    df_trans_enriched = enrich_transactions_with_window_features(df_trans)
    
    print("  - Enriqueciendo dim_account...")
    dim_account = enrich_account_dimension(df_account, df_district, df_disp, dim_client)
    
    print("  - Estandarizando columnas categóricas...")
    df_card = df_card.withColumnRenamed("type", "type_card")
    df_order = standardize_categorical_columns(df_order, ["k_symbol"])
    df_card = standardize_categorical_columns(df_card, ["type_card"])
    df_disp = standardize_categorical_columns(df_disp, ["type"])
    
    print("  - Detectando outliers...")
    df_trans_enriched = create_outlier_flags(df_trans_enriched, "amount", 0.95)
    dim_loan = create_outlier_flags(dim_loan, "amount", 0.95)
    
    print("[SUCCESS] Feature Engineering completado")
    
    # ========================================================================
    # 3. CREAR TABLAS DE HECHOS
    # ========================================================================
    print("\n[STEP 3] Creando tablas de hechos agregadas...")
    
    print("  - Creando fact_account_transactions...")
    fact_account_trans = create_fact_account_transactions(df_trans_enriched)
    
    print("  - Creando fact_account_summary...")
    fact_account_summary = create_fact_account_summary(
        dim_account, fact_account_trans, dim_loan, df_card, df_disp
    )
    
    print("[SUCCESS] Tablas de hechos creadas")
    
    # ========================================================================
    # 4. GUARDAR TABLAS CURATED
    # ========================================================================
    print("\n[STEP 4] Guardando tablas en Curated...")
    
    tables_to_save = {
        'dim_client': (dim_client, None),
        'dim_account': (dim_account, ['district_id']),
        'dim_loan': (dim_loan, ['status']),
        'dim_district': (df_district, None),
        'dim_card': (df_card, ['type_card']),
        'dim_disp': (df_disp, ['type']),
        'dim_order': (df_order, None),
        'fact_transactions': (df_trans_enriched, ['type']),
        'fact_account_transactions': (fact_account_trans, None),
        'fact_account_summary': (fact_account_summary, ['customer_segment'])
    }
    
    for table_name, (df, partition_cols) in tables_to_save.items():
        try:
            curated_path = f"{S3_PROTOCOL}://{S3_BUCKET}/{CURATED_PREFIX}{table_name}/"
            
            print(f"\n  📊 Guardando {table_name}...")
            print(f"     Path: {curated_path}")
            
            writer = df.write.mode("overwrite")
            
            if partition_cols:
                writer = writer.partitionBy(*partition_cols)
                print(f"     Particionado por: {', '.join(partition_cols)}")
            
            writer.option("compression", "snappy").parquet(curated_path)
            
            row_count = df.count()
            print(f"     ✅ {row_count:,} filas guardadas")
            
        except Exception as e:
            print(f"     ❌ Error: {str(e)}")
            continue
    
    print("\n" + "=" * 80)
    print("✅ PIPELINE PROCESSED → CURATED COMPLETADO")
    print("=" * 80)

if __name__ == "__main__":
    main()
    if EXECUTION_MODE == 'GLUE':
        job.commit()



# #arreglar:
# # Ejemplo en PySpark/Glue:
# df_dim_account = df_dim_account.withColumn(
#     "district_id",
#     col("district_id").cast(IntegerType()) # <--- Asegura que se escriba como INT
# )

# # Luego, escribe el DataFrame:
# df_dim_account.write.mode("overwrite").parquet(...)


# def enrich_account_dimension(df_account: DataFrame, df_district: DataFrame, 
#                             df_disp: DataFrame, df_client: DataFrame) -> DataFrame:
#     """Enriquece ACCOUNT con información completa"""
    
#     # ====================================================================
#     # 💥 CORRECCIÓN CRÍTICA: Castear district_id de STRING a INTEGER.
#     # Esto soluciona el error de tipo ('varchar', 'integer') en el JOIN 
#     # y asegura que la columna se guarde correctamente en la capa Curated.
#     # ====================================================================
#     df_account = df_account.withColumn(
#         "district_id", 
#         col("district_id").cast(IntegerType())
#     )
    
#     # Join con district
#     df = df_account.join(df_district, "district_id", "left")
    
#     # Obtener owner
#     df_owners = df_disp.filter(col("type") == "OWNER") \
# # ... el resto del código es igual ...