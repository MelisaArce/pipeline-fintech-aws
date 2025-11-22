#!/bin/bash
# Activa la detención inmediata del script si cualquier comando falla
set -e

# ==============================================================================
# EXPORTAR USER_ID/GROUP_ID PARA DOCKER-COMPOSE
# ==============================================================================
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)
echo "[INFO] Configurando permisos - USER_ID: $USER_ID, GROUP_ID: $GROUP_ID"

# ==============================================================================
# CONFIGURACIÓN DE VARIABLES
# ==============================================================================
# Para comandos AWS CLI desde el host
AWS_ENDPOINT_URL="http://localhost:4566"
# Para Spark dentro del contenedor Docker (usar nombre del servicio)
AWS_ENDPOINT_URL_CONTAINER="http://localstack:4566"
AWS_BUCKET="berka-data-lake"
RAW_DATA_PATH="./data/raw/berka/"
PROCESSED_DATA_PATH="./data/processed/berka/"
CURATED_DATA_PATH="./data/curated/berka/"
SPARK_CLIENT_NAME="spark_client_berka"
MYSQL_CONTAINER_NAME="berka_mysql_db"

# Rutas de los scripts dentro del contenedor
ETL_RAW_PROCESSED_SCRIPT="/opt/bitnami/spark/jobs/berka_etl_job.py"
ETL_PROCESSED_CURATED_SCRIPT="/opt/bitnami/spark/jobs/berka_curated_job.py" 
ETL_CURATED_RDS_SCRIPT="/opt/bitnami/spark/jobs/berka_rds_job.py"

# Paquetes Spark: S3A + Conector MySQL JDBC
SPARK_PACKAGES="org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-s3:1.12.500,mysql:mysql-connector-java:8.0.33"
MAX_RETRIES=20
WAIT_TIME=2

echo "===================================================================="
echo "🚀 Iniciando Pipeline ETL Local (RAW->PROCESSED->CURATED->MYSQL)"
echo "===================================================================="

# Limpiar directorios de ejecuciones anteriores con permisos incorrectos
echo "0/10. Limpiando directorios de ejecuciones anteriores..."
if [ -d "$PROCESSED_DATA_PATH" ]; then
    echo "🧹 Removiendo directorio processed con sudo (si tiene permisos incorrectos)..."
    sudo rm -rf "$PROCESSED_DATA_PATH" || true
fi
if [ -d "$CURATED_DATA_PATH" ]; then
    echo "🧹 Removiendo directorio curated con sudo (si tiene permisos incorrectos)..."
    sudo rm -rf "$CURATED_DATA_PATH" || true
fi

echo "1/10. Levantando contenedores (LocalStack, MySQL y Spark Client)..."
docker compose up -d

cleanup() {
    EXIT_CODE=$?
    echo "===================================================================="
    echo "11/11. Deteniendo y eliminando contenedores..."
    docker compose down
    echo "Contenedores detenidos. Código de salida: $EXIT_CODE"
    echo "===================================================================="
    if [ $EXIT_CODE -ne 0 ]; then
        echo "🚨 FALLO: Revise el output anterior para depuración."
    fi
    exit $EXIT_CODE
}

trap cleanup EXIT

# ========================================================================
# 2. Esperar a que LocalStack S3 esté listo
# ========================================================================
echo "2/10. Esperando a que el servicio S3 esté 'available' en LocalStack..."
RETRY_COUNT=0
S3_HEALTH_ENDPOINT="$AWS_ENDPOINT_URL/_localstack/health"
sleep 5

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    HEALTH_STATUS=$(curl -sS $S3_HEALTH_ENDPOINT 2>/dev/null || echo "")
    if echo "$HEALTH_STATUS" | grep -q '"s3": "available"'; then
        echo -e "\n✅ LocalStack S3 está UP y 'available'. Continuando."
        break
    fi
    echo -n "."
    sleep $WAIT_TIME
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "\n❌ ERROR: LocalStack S3 no inició correctamente después de $MAX_RETRIES intentos."
    exit 1
fi

# ========================================================================
# 3. Esperar a que MySQL esté listo y acepte conexiones
# ========================================================================
echo "3/10. Esperando a que el servicio MySQL esté listo para aceptar conexiones..."
RETRY_COUNT=0
MYSQL_USER="root"
MYSQL_PASSWORD="password" 

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec $MYSQL_CONTAINER_NAME mysqladmin ping -h localhost -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" --silent 2>/dev/null; then
        echo -e "\n✅ MySQL está UP y listo para conexiones. Continuando."
        break
    fi
    echo -n "."
    sleep $WAIT_TIME
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "\n❌ ERROR: MySQL no inició correctamente o no acepta conexiones después de $MAX_RETRIES intentos."
    exit 1
fi

# ========================================================================
# 4. Configurar S3 y cargar datos Raw
# ========================================================================
echo "4/10. Creando bucket S3 y subiendo datos raw..."
export AWS_ENDPOINT_URL=$AWS_ENDPOINT_URL
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# Verificar si el bucket ya existe antes de crearlo
if ! aws s3 ls s3://$AWS_BUCKET --endpoint-url=$AWS_ENDPOINT_URL 2>/dev/null; then
    aws s3 mb s3://$AWS_BUCKET --endpoint-url=$AWS_ENDPOINT_URL
    echo "✅ Bucket $AWS_BUCKET creado."
else
    echo "ℹ️  Bucket $AWS_BUCKET ya existe."
fi

if [ -d "$RAW_DATA_PATH" ]; then
    aws s3 sync $RAW_DATA_PATH s3://$AWS_BUCKET/raw/berka/ --endpoint-url=$AWS_ENDPOINT_URL
    echo "✅ Datos raw cargados correctamente."
else
    echo "⚠️  ADVERTENCIA: Directorio $RAW_DATA_PATH no encontrado. Saltando la carga de datos raw."
fi 

# ========================================================================
# 5. EJECUCIÓN DEL PRIMER JOB (RAW -> PROCESSED)
# ========================================================================
echo "5/10. Ejecutando spark-submit (RAW -> PROCESSED)..."
if ! docker exec -i \
    -e EXECUTION_MODE=LOCAL \
    -e AWS_ENDPOINT_URL=$AWS_ENDPOINT_URL_CONTAINER \
    -e AWS_ACCESS_KEY_ID=test \
    -e AWS_SECRET_ACCESS_KEY=test \
    $SPARK_CLIENT_NAME spark-submit \
    --master local[*] \
    --packages $SPARK_PACKAGES \
    --conf spark.hadoop.fs.s3a.endpoint=$AWS_ENDPOINT_URL_CONTAINER \
    --conf spark.hadoop.fs.s3a.access.key=test \
    --conf spark.hadoop.fs.s3a.secret.key=test \
    --conf spark.hadoop.fs.s3a.path.style.access=true \
    --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
    --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false \
    $ETL_RAW_PROCESSED_SCRIPT; then
    echo "❌ ERROR: Falló la ejecución del job RAW -> PROCESSED"
    exit 1
fi

echo "6/10. Verificación de archivos Processed en S3..."
sleep 5
if aws s3 ls s3://$AWS_BUCKET/processed/berka/ --recursive --endpoint-url=$AWS_ENDPOINT_URL | grep -q "."; then
    echo "✅ Stage RAW -> PROCESSED completada correctamente."
    aws s3 ls s3://$AWS_BUCKET/processed/berka/ --recursive --endpoint-url=$AWS_ENDPOINT_URL
    
    # Descargar datos procesados a local
    echo "📥 Descargando datos procesados de S3 a local..."
    mkdir -p "$PROCESSED_DATA_PATH"
    
    if aws s3 sync s3://$AWS_BUCKET/processed/berka/ "$PROCESSED_DATA_PATH" --endpoint-url=$AWS_ENDPOINT_URL; then
        echo "✅ Datos procesados descargados a: $PROCESSED_DATA_PATH"
        echo "📂 Archivos locales:"
        ls -lh "$PROCESSED_DATA_PATH" 2>/dev/null || echo "Directorio vacío o sin acceso"
    else
        echo "⚠️  Error al descargar datos procesados"
    fi
else
    echo "⚠️  ADVERTENCIA: No se encontraron archivos en processed/berka/"
fi

# ========================================================================
# 7. EJECUCIÓN DEL SEGUNDO JOB (PROCESSED -> CURATED)
# ========================================================================
echo "7/10. Ejecutando spark-submit (PROCESSED -> CURATED)..."
if ! docker exec -i \
    -e EXECUTION_MODE=LOCAL \
    -e AWS_ENDPOINT_URL=$AWS_ENDPOINT_URL_CONTAINER \
    -e AWS_ACCESS_KEY_ID=test \
    -e AWS_SECRET_ACCESS_KEY=test \
    $SPARK_CLIENT_NAME spark-submit \
    --master local[*] \
    --packages $SPARK_PACKAGES \
    --conf spark.hadoop.fs.s3a.endpoint=$AWS_ENDPOINT_URL_CONTAINER \
    --conf spark.hadoop.fs.s3a.access.key=test \
    --conf spark.hadoop.fs.s3a.secret.key=test \
    --conf spark.hadoop.fs.s3a.path.style.access=true \
    --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
    --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false \
    $ETL_PROCESSED_CURATED_SCRIPT; then
    echo "❌ ERROR: Falló la ejecución del job PROCESSED -> CURATED"
    exit 1
fi

echo "8/10. Verificación de archivos Curated en S3..."
sleep 5
if aws s3 ls s3://$AWS_BUCKET/curated/berka/ --recursive --endpoint-url=$AWS_ENDPOINT_URL | grep -q "."; then
    echo "✅ Stage PROCESSED -> CURATED completada correctamente."
    aws s3 ls s3://$AWS_BUCKET/curated/berka/ --recursive --endpoint-url=$AWS_ENDPOINT_URL
    
    # Descargar datos curated a local
    echo "📥 Descargando datos curated de S3 a local..."
    mkdir -p "$CURATED_DATA_PATH"
    
    if aws s3 sync s3://$AWS_BUCKET/curated/berka/ "$CURATED_DATA_PATH" --endpoint-url=$AWS_ENDPOINT_URL; then
        echo "✅ Datos curated descargados a: $CURATED_DATA_PATH"
        echo "📂 Archivos locales:"
        ls -lh "$CURATED_DATA_PATH" 2>/dev/null || echo "Directorio vacío o sin acceso"
    else
        echo "⚠️  Error al descargar datos curated"
    fi
else
    echo "⚠️  ADVERTENCIA: No se encontraron archivos en curated/berka/"
fi

# ========================================================================
# 9. EJECUCIÓN DEL TERCER JOB (CURATED -> RDS MySQL)
# ========================================================================
echo "9/10. Ejecutando spark-submit (CURATED -> RDS MySQL)..."
if ! docker exec -i \
    -e EXECUTION_MODE=LOCAL \
    -e AWS_ENDPOINT_URL=$AWS_ENDPOINT_URL_CONTAINER \
    -e AWS_ACCESS_KEY_ID=test \
    -e AWS_SECRET_ACCESS_KEY=test \
    $SPARK_CLIENT_NAME spark-submit \
    --master local[*] \
    --packages $SPARK_PACKAGES \
    --conf spark.hadoop.fs.s3a.endpoint=$AWS_ENDPOINT_URL_CONTAINER \
    --conf spark.hadoop.fs.s3a.access.key=test \
    --conf spark.hadoop.fs.s3a.secret.key=test \
    --conf spark.hadoop.fs.s3a.path.style.access=true \
    --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
    --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false \
    $ETL_CURATED_RDS_SCRIPT; then
    echo "❌ ERROR: Falló la ejecución del job CURATED -> RDS"
    exit 1
fi

echo "✅ Stage CURATED -> RDS MySQL completada correctamente."

# ========================================================================
# 10. VALIDACIÓN DE DATOS EN MYSQL
# ========================================================================
echo ""
echo "===================================================================="
echo "📊 VALIDACIÓN DE DATOS EN MYSQL"
echo "===================================================================="

echo ""
echo "Conteo de filas por tabla:"
echo "--------------------------------------------------------------------"

# Ejecutar query de conteo para cada tabla
docker exec $MYSQL_CONTAINER_NAME mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" berka_warehouse -e "
SELECT 'dim_client' as Tabla, COUNT(*) as Filas FROM dim_client
UNION ALL
SELECT 'dim_account', COUNT(*) FROM dim_account
UNION ALL
SELECT 'dim_loan', COUNT(*) FROM dim_loan
UNION ALL
SELECT 'dim_district', COUNT(*) FROM dim_district
UNION ALL
SELECT 'dim_card', COUNT(*) FROM dim_card
UNION ALL
SELECT 'dim_disp', COUNT(*) FROM dim_disp
UNION ALL
SELECT 'dim_order', COUNT(*) FROM dim_order
UNION ALL
SELECT 'fact_account_transactions', COUNT(*) FROM fact_account_transactions
UNION ALL
SELECT 'fact_account_summary', COUNT(*) FROM fact_account_summary
UNION ALL
SELECT 'fact_transactions', COUNT(*) FROM fact_transactions
ORDER BY Tabla;
" 2>/dev/null

echo ""
echo "--------------------------------------------------------------------"
echo "Ejemplo de datos - dim_client (primeras 5 filas):"
echo "--------------------------------------------------------------------"

docker exec $MYSQL_CONTAINER_NAME mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" berka_warehouse -e "
SELECT 
    client_id,
    gender,
    age_at_1998 as edad,
    age_segment as segmento_edad,
    district_id
FROM dim_client 
LIMIT 5;
" 2>/dev/null

echo ""
echo "--------------------------------------------------------------------"
echo "Ejemplo de datos - fact_account_summary (primeras 5 filas):"
echo "--------------------------------------------------------------------"

docker exec $MYSQL_CONTAINER_NAME mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" berka_warehouse -e "
SELECT 
    account_id,
    customer_segment as segmento,
    total_transactions as transacciones,
    ROUND(net_balance, 2) as balance_neto,
    num_loans as prestamos,
    num_cards as tarjetas
FROM fact_account_summary 
LIMIT 5;
" 2>/dev/null

echo ""
echo "--------------------------------------------------------------------"
echo "Resumen de calidad de datos:"
echo "--------------------------------------------------------------------"

docker exec $MYSQL_CONTAINER_NAME mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" berka_warehouse -e "
SELECT 
    'Clientes por género' as Metrica,
    CONCAT(
        'M: ', SUM(CASE WHEN gender = 'M' THEN 1 ELSE 0 END),
        ' | F: ', SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END)
    ) as Valor
FROM dim_client
UNION ALL
SELECT 
    'Préstamos riesgosos',
    CONCAT(SUM(is_risky), ' de ', COUNT(*), ' (', ROUND(SUM(is_risky)*100/COUNT(*), 1), '%)')
FROM dim_loan
UNION ALL
SELECT 
    'Segmentos de clientes',
    GROUP_CONCAT(DISTINCT customer_segment ORDER BY customer_segment SEPARATOR ', ')
FROM fact_account_summary;
" 2>/dev/null

echo ""
echo "===================================================================="
echo "🎉 Pipeline ETL completado exitosamente!"
echo "===================================================================="

# El script termina aquí. El 'trap cleanup EXIT' ejecuta el paso 11/11.