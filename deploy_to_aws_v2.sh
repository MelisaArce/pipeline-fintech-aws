#!/bin/bash
set -e

# ==============================================================================
# SCRIPT DE DEPLOYMENT DEL PIPELINE BERKA A AWS
# ==============================================================================

echo "======================================================================"
echo "🚀 DEPLOYMENT DEL PIPELINE BERKA A AWS"
echo "======================================================================"

# ==============================================================================
# CONFIGURACIÓN - ACTUALIZAR ESTOS VALORES
# ==============================================================================
source .env

AUTHORIZED_IP="$(curl -s https://api.ipify.org)/32" 
STACK_NAME="berka-pipeline"
REGION="us-east-1" 
VPC_ID=""  
CLOUDFORMATION_FILE="./cloudformation_template_v6.yaml" 
SCRIPTS_DIR="../glue-jobs/"
RAW_DATA_DIR="./data_original"

JOB_RAW_TO_PROCESSED="raw_to_processed.py"
JOB_PROCESSED_TO_CURATED="processed_to_curated.py"
JOB_CURATED_TO_RDS="berka_curated_to_rds_v1.py"

echo ""
echo "📋 Configuración:"
echo "   Nombre: $YOUR_NAME"
echo "   Stack: $STACK_NAME"
echo "   Región: $REGION"
echo "   Tu IP: $AUTHORIZED_IP"
echo ""

# ==============================================================================
# VALIDACIONES PREVIAS
# ==============================================================================
echo "1/8. Validando prerequisitos..."

# Verificar AWS CLI instalado
if ! command -v aws &> /dev/null; then
    echo "❌ ERROR: AWS CLI no está instalado"
    exit 1
fi

# Verificar credenciales AWS configuradas
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ ERROR: AWS CLI no está configurado"
    exit 1
fi

# Verificar que existe el archivo CloudFormation
if [ ! -f "$CLOUDFORMATION_FILE" ]; then
    echo "❌ ERROR: No se encuentra $CLOUDFORMATION_FILE"
    exit 1
fi

# Verificar que existen los scripts Python
if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "❌ ERROR: No se encuentra el directorio de scripts: $SCRIPTS_DIR"
    exit 1
fi

# Verificar que existen los 3 scripts clave
declare -a REQUIRED_SCRIPTS=(
  $JOB_RAW_TO_PROCESSED
  $JOB_PROCESSED_TO_CURATED
  $JOB_CURATED_TO_RDS
)

for script in "${REQUIRED_SCRIPTS[@]}"; do
  if [ ! -f "$SCRIPTS_DIR/$script" ]; then
    echo "❌ ERROR: Script no encontrado: $SCRIPTS_DIR/$script"
    exit 1
  fi
done

echo "✅ Prerequisitos OK"
echo ""

# ==============================================================================
# OBTENER INFO DE LA CUENTA
# ==============================================================================
echo "2/8. Obteniendo información de la cuenta AWS..."

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="${YOUR_NAME}-datalake-${ACCOUNT_ID}-${REGION}" # Corregido para coincidir con CF

echo "   Account ID: $ACCOUNT_ID"
echo "   Bucket S3 (será creado): $BUCKET_NAME"
echo ""

# ==============================================================================
# CONFIRMAR DEPLOYMENT
# ==============================================================================
echo "⚠️  ATENCIÓN: Vas a crear recursos en AWS"
echo "   Stack CloudFormation: $STACK_NAME"
echo "   Región: $REGION"
echo ""
read -p "¿Continuar? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelado"
    exit 1
fi
echo ""

# ==============================================================================
# CREAR CLOUDFORMATION STACK
# ==============================================================================
echo "3/8. Creando stack de CloudFormation..."
echo "   Esto puede tardar 10-15 minutos (RDS tarda en crear)..."

STACK_CREATION_RESULT=$(aws cloudformation create-stack \
  --stack-name "$STACK_NAME" \
  --template-body "file://$CLOUDFORMATION_FILE" \
  --parameters \
    ParameterKey=YourName,ParameterValue="$YOUR_NAME" \
    ParameterKey=RDSUsername,ParameterValue="$RDS_USERNAME" \
    ParameterKey=RDSPassword,ParameterValue="$RDS_PASSWORD" \
    ParameterKey=AuthorizedIP,ParameterValue="$AUTHORIZED_IP" \
    ParameterKey=VpcId,ParameterValue="$VPC_ID" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" 2>&1)

if [ $? -ne 0 ]; then
    echo "❌ ERROR al crear el stack:"
    echo "$STACK_CREATION_RESULT"
    exit 1
fi

STACK_ID=$(echo "$STACK_CREATION_RESULT" | awk '/StackId/ {print $2}') # Mejorado para manejar JSON o texto
echo "✅ Stack creado (ID: $STACK_ID). Esperando a que complete..."
echo ""

if ! aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$REGION"; then
    echo "❌ ERROR: Fallo al esperar la creación del stack"
    exit 1
fi

echo "✅ Stack creado exitosamente!"
echo ""

# ==============================================================================
# OBTENER OUTPUTS DEL STACK
# ==============================================================================
echo "4/8. Obteniendo información del stack..."

# Obtener el nombre del bucket creado
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
  --output text 2>/dev/null)

# Obtener endpoint de RDS
RDS_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' \
  --output text 2>/dev/null)

if [ -z "$BUCKET_NAME" ] || [ -z "$RDS_ENDPOINT" ]; then
    echo "❌ ERROR: No se pudieron obtener los outputs clave (Bucket/RDS Endpoint)"
    exit 1
fi

echo "   Bucket S3: $BUCKET_NAME"
echo "   RDS Endpoint: $RDS_ENDPOINT"
echo ""

# ==============================================================================
# SUBIR SCRIPTS PYTHON A S3
# ==============================================================================
echo "5/8. Subiendo scripts Python a S3..."
SCRIPTS_DEST="s3://$BUCKET_NAME/scripts"

# Subir Job 1: RAW -> PROCESSED
echo "   Subiendo $JOB_RAW_TO_PROCESSED -> berka_raw_to_processed.py..."
if ! aws s3 cp "$SCRIPTS_DIR/$JOB_RAW_TO_PROCESSED" \
  "$SCRIPTS_DEST/berka_raw_to_processed.py" \
  --region "$REGION"; then
  echo "❌ ERROR: Fallo al subir script $JOB_RAW_TO_PROCESSED"
  exit 1
fi

# Subir Job 2: PROCESSED -> CURATED
echo "   Subiendo $JOB_PROCESSED_TO_CURATED -> berka_processed_to_curated.py..."
if ! aws s3 cp "$SCRIPTS_DIR/$JOB_PROCESSED_TO_CURATED" \
  "$SCRIPTS_DEST/berka_processed_to_curated.py" \
  --region "$REGION"; then
  echo "❌ ERROR: Fallo al subir script $JOB_PROCESSED_TO_CURATED"
  exit 1
fi

# Subir Job 3: CURATED -> RDS
echo "   Subiendo $JOB_CURATED_TO_RDS..."
if ! aws s3 cp "$SCRIPTS_DIR/$JOB_CURATED_TO_RDS" \
  "$SCRIPTS_DEST/$JOB_CURATED_TO_RDS" \
  --region "$REGION"; then
  echo "❌ ERROR: Fallo al subir script $JOB_CURATED_TO_RDS"
  exit 1
fi

echo "✅ Scripts subidos a S3"
echo ""

# ==============================================================================
# SUBIR DATOS RAW A S3
# ==============================================================================
echo "6/8. Subiendo datos RAW a S3..."

if [ -d "$RAW_DATA_DIR" ]; then
  if ! aws s3 sync "$RAW_DATA_DIR" "s3://$BUCKET_NAME/raw/berka/" --region "$REGION"; then
    echo "❌ ERROR: Fallo al subir datos raw"
    exit 1
  fi

  # Contar archivos subidos
  FILE_COUNT=$(aws s3 ls "s3://$BUCKET_NAME/raw/berka/" --recursive | wc -l)
  echo "✅ $FILE_COUNT archivos subidos a S3"
else
  echo "⚠️  ADVERTENCIA: Directorio de datos raw no encontrado: $RAW_DATA_DIR"
  echo "   Deberás subir los datos manualmente más tarde a s3://$BUCKET_NAME/raw/berka/"
fi
echo ""

# ==============================================================================
# PASOS FINALES E INSTRUCCIONES
# ==============================================================================
echo "======================================================================"
echo "🎉 DEPLOYMENT COMPLETO EXITOSAMENTE. INSTRUCCIONES:"
echo "======================================================================"
echo "1. Ejecuta el Job 1 (RAW -> PROCESSED):"
echo "   aws glue start-job-run --job-name ${YOUR_NAME}-raw-to-processed --region $REGION"
echo "2. Ejecuta el Job 2 (PROCESSED -> CURATED):"
echo "   aws glue start-job-run --job-name ${YOUR_NAME}-processed-to-curated --region $REGION"
echo "3. Ejecuta el CRAWLER (para catalogar los datos curados):"
echo "   aws glue start-crawler --name ${YOUR_NAME}-curated-crawler --region $REGION"
echo "   (Espera a que el crawler termine antes del paso 4)"
echo "4. Ejecuta el Job 3 (CURATED -> RDS):"
echo "   aws glue start-job-run --job-name ${YOUR_NAME}-curated-to-rds --region $REGION"
echo "5. Detener RDS (para ahorrar costos):"
echo "   aws lambda invoke --function-name ${YOUR_NAME}-rds-control --log-type Tail response.json --region $REGION"
echo ""