from diagrams import Diagram, Cluster
from diagrams.aws.storage import S3
from diagrams.aws.analytics import Glue, GlueCrawlers, Athena, Quicksight
from diagrams.aws.database import RDS
from diagrams.onprem.compute import Server  # Para CSVs fuente

# Config global
graph_attr = {
    "fontsize": "12",
    "bgcolor": "#f4f4f4"
}

with Diagram(
    "Pipeline End-to-End Berka AWS",
    show=True,
    direction="LR",
    filename="berka_pipeline_fixed_v1",
    graph_attr=graph_attr
):
    
    # Ingesta: CSVs Berka
    csv_berka = Server("CSVs Berka\n(Datos fuente)")
    
    # Cluster Procesamiento
    with Cluster("Procesamiento (3 Glue Jobs)"):
        raw = S3("Raw\n(Crudo)")
        processed = S3("Processed\n(Limpio)")
        curated = S3("Curated\n(Refinado)")
        
        job1 = Glue("Job 1\nRaw → Processed")
        job2 = Glue("Job 2\nProcessed → Curated")
        job3 = Glue("Job 3\nCurated → RDS")
    
    # Analytics & BI
    with Cluster("Analytics & BI"):
        crawler = GlueCrawlers("Glue Crawler\n(Data Catalog)")
        athena = Athena("Athena\n(Queries SQL)")
        rds = RDS("RDS\n(Cargado de Curated)")
        qs = Quicksight("QuickSight\n(Dashboards)")
    
    # Flujo end-to-end
    csv_berka >> raw >> job1 >> processed >> job2 >> curated
    
    # Job3: Curated → RDS
    curated >> job3 >> rds >> qs
    
    # Curated → Crawler → Athena → QS
    curated >> crawler >> athena 
