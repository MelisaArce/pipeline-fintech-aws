#!/bin/bash
set -e

# ==============================================================================
# SCRIPT DE DEPLOYMENT DEL PIPELINE BERKA A AWS
# ==============================================================================

echo "======================================================================"
echo "🚀 DEPLOYMENT DEL PIPELINE BERKA A AWS"
echo "======================================================================"

# ==============================================================================
# CONFIGURACIÓN - CAMBIAR ESTOS VALORES
# ==============================================================================
YOUR_NAME="berka"  
RDS_USERNAME="admin"
RDS_PASSWORD="BerkaPassword123!"  
AUTHORIZED_IP="$(curl -s https://api.ipify.org)/32"  
STACK_NAME="berka-pipeline"
REGION="us-east-1" 
VPC_ID=""  
CLOUDFORMATION_FILE="./cloudformation_template_v1.yaml"
SCRIPTS_DIR="../glue-jobs/"
RAW_DATA_DIR="./data/raw/berka/"

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
    echo "   Instalar desde: https://aws.amazon.com/cli/"
    exit 1
fi

# Verificar credenciales AWS configuradas
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ ERROR: AWS CLI no está configurado"
    echo "   Ejecutar: aws configure"
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

echo "✅ Prerequisitos OK"
echo ""

# ==============================================================================
# OBTENER INFO DE LA CUENTA
# ==============================================================================
echo "2/8. Obteniendo información de la cuenta AWS..."

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="${YOUR_NAME}-datalake-${ACCOUNT_ID}"

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

STACK_ID=$(echo "$STACK_CREATION_RESULT" | jq -r '.StackId')
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

if [ -z "$BUCKET_NAME" ]; then
    echo "❌ ERROR: No se pudo obtener el nombre del bucket S3"
    exit 1
fi

# Obtener endpoint de RDS
RDS_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' \
  --output text 2>/dev/null)

if [ -z "$RDS_ENDPOINT" ]; then
    echo "❌ ERROR: No se pudo obtener el endpoint de RDS"
    exit 1
fi

echo "   Bucket S3: $BUCKET_NAME"
echo "   RDS Endpoint: $RDS_ENDPOINT"
echo ""

# ==============================================================================
# SUBIR SCRIPTS PYTHON A S3
# ==============================================================================
echo "5/8. Subiendo scripts Python a S3..."

# Verificar que los scripts existen
declare -a REQUIRED_SCRIPTS=(
  "raw_csv_transform_w_local.py"
  "curated_job.py"
  "berka_curated_to_rds.py"
)

for script in "${REQUIRED_SCRIPTS[@]}"; do
  if [ ! -f "$SCRIPTS_DIR/$script" ]; then
    echo "❌ ERROR: Script no encontrado: $SCRIPTS_DIR/$script"
    exit 1
  fi
done

# Subir scripts con nombres correctos para Glue
SCRIPTS_DEST="s3://$BUCKET_NAME/scripts"

echo "   Subiendo raw_csv_transform_w_local.py..."
if ! aws s3 cp "$SCRIPTS_DIR/raw_csv_transform_w_local.py" \
  "$SCRIPTS_DEST/berka_raw_to_processed.py" \
  --region "$REGION"; then
  echo "❌ ERROR: Fallo al subir script raw_csv_transform_w_local.py"
  exit 1
fi

echo "   Subiendo curated_job.py..."
if ! aws s3 cp "$SCRIPTS_DIR/curated_job.py" \
  "$SCRIPTS_DEST/berka_processed_to_curated.py" \
  --region "$REGION"; then
  echo "❌ ERROR: Fallo al subir script curated_job.py"
  exit 1
fi

echo "   Subiendo curated_to_rds.py..."
if ! aws s3 cp "$SCRIPTS_DIR/berka_curated_to_rds.py" \
  "$SCRIPTS_DEST/berka_curated_to_rds.py" \
  --region "$REGION"; then
  echo "❌ ERROR: Fallo al subir script berka_curated_to_rds.py"
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
  echo "   Deberás subir los datos manualmente más tarde"
fi
echo ""

