"""AWS Lambda — Déclenchement serverless du pipeline SIG éolien.

Déploiement:
    zip lambda_pipeline.zip lambda_pipeline.py
    aws lambda update-function-code --function-name eolien-pipeline-trigger \
        --zip-file fileb://lambda_pipeline.zip

Variables d'environnement Lambda:
    AIRFLOW_API_URL : URL de l'API REST Airflow (MWAA ou EC2)
    AIRFLOW_USER    : utilisateur Airflow
    AIRFLOW_PASS    : mot de passe Airflow
    SNS_TOPIC_ARN   : ARN du topic SNS pour les notifications
"""
import json
import os
import urllib.request
import urllib.parse
import base64
from datetime import datetime


AIRFLOW_API_URL = os.environ.get("AIRFLOW_API_URL", "")
AIRFLOW_USER = os.environ.get("AIRFLOW_USER", "admin")
AIRFLOW_PASS = os.environ.get("AIRFLOW_PASS", "")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

DAG_MAP = {
    "cadastre": "dag_cadastre_dgfip",
    "bdtopo": "dag_bdtopo_ign",
    "enedis": "dag_enedis_ore",
    "sia": "dag_obstacles_sia_anfr",
    "elus": "dag_elus_rne",
    "zaer": "dag_zaer",
    "patrimoine": "dag_monuments_histo",
}


def _airflow_auth_header() -> str:
    token = base64.b64encode(f"{AIRFLOW_USER}:{AIRFLOW_PASS}".encode()).decode()
    return f"Basic {token}"


def trigger_dag(dag_id: str, conf: dict | None = None) -> dict:
    url = f"{AIRFLOW_API_URL}/api/v1/dags/{dag_id}/dagRuns"
    payload = json.dumps({
        "dag_run_id": f"lambda_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "conf": conf or {},
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": _airflow_auth_header(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def send_notification(subject: str, message: str) -> None:
    if not SNS_TOPIC_ARN:
        return
    import boto3
    sns = boto3.client("sns", region_name=os.getenv("AWS_REGION", "eu-west-3"))
    sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)


def lambda_handler(event: dict, context) -> dict:
    """
    Événement attendu:
        {"source": "cadastre", "dept": "60"}      → déclenche DAG cadastre
        {"source": "all"}                          → déclenche tous les DAGs
        {"dag_id": "dag_cadastre_dgfip"}           → déclenche DAG par ID direct
    """
    source = event.get("source")
    dag_id = event.get("dag_id")
    conf = {k: v for k, v in event.items() if k not in ("source", "dag_id")}

    triggered = []

    if dag_id:
        result = trigger_dag(dag_id, conf)
        triggered.append({"dag_id": dag_id, "run_id": result.get("dag_run_id")})

    elif source == "all":
        for key, did in DAG_MAP.items():
            try:
                result = trigger_dag(did, conf)
                triggered.append({"dag_id": did, "run_id": result.get("dag_run_id")})
            except Exception as exc:
                triggered.append({"dag_id": did, "error": str(exc)})

    elif source and source in DAG_MAP:
        result = trigger_dag(DAG_MAP[source], conf)
        triggered.append({"dag_id": DAG_MAP[source], "run_id": result.get("dag_run_id")})

    else:
        return {"statusCode": 400, "body": f"source ou dag_id inconnu : {event}"}

    send_notification(
        subject=f"Pipeline éolien déclenché — {len(triggered)} DAG(s)",
        message=json.dumps(triggered, indent=2),
    )
    return {"statusCode": 200, "body": json.dumps(triggered)}
