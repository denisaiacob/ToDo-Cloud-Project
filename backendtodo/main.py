from google.cloud import firestore
from google.oauth2 import service_account
import functions_framework
from datetime import datetime
from flask import Request, make_response
import json
from google.cloud import logging
import googlecloudprofiler
from google.cloud import monitoring_v3
import time

# Initialize Firestore client
credentials = service_account.Credentials.from_service_account_file("todo-454613-1b9473315763.json")
db = firestore.Client()
TASK_FIELD = ["completed", "created at", "description", "duedate", "task"]

monitoring_client = monitoring_v3.MetricServiceClient()
project_id = "your-gcp-project-id"

def create_custom_metric(metric_type, value):
    """Sends custom metrics to Cloud Monitoring"""
    series = monitoring_v3.TimeSeries()
    series.metric.type = f"custom.googleapis.com/{metric_type}"
    series.resource.type = "global"

    point = monitoring_v3.Point()
    point.value.double_value = value
    now = datetime.utcnow()
    point.interval.end_time.seconds = int(now.timestamp())

    series.points.append(point)

    request = monitoring_v3.CreateTimeSeriesRequest(
        name=f"projects/{project_id}",
        time_series=[series],
    )

    monitoring_client.create_time_series(request)

try:
    googlecloudprofiler.start(
        service="task-api-service",
        service_version="1.0.0",
        verbose=0  # Set to 1 for debugging
    )
except (ValueError, NotImplementedError) as e:
    print(f"Profiler not started: {e}")

# Initialize Cloud Logging client
logging_client = logging.Client()
logger = logging_client.logger("task-api-logs")

def log_message(level, message, extra_data=None):
        """Helper function to log messages to Cloud Logging."""
        log_entry = {"message": message}
        if extra_data:
            log_entry.update(extra_data)

        if level == "INFO":
            logger.log_struct(log_entry, severity="INFO")
        elif level == "ERROR":
            logger.log_struct(log_entry, severity="ERROR")

def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

def convert_firestore_document(doc):
    data = doc.to_dict()
    for key, value in data.items():
        if isinstance(value, datetime):  
            data[key] = value.isoformat()
    return data

def get_all_documents_for_db(db_name):
    db_connection = db.collection(db_name)
    documents = db_connection.stream()
    return documents


def get_all_tasks(request:Request):
    start_time = time.time()
    try:
        username = request.args.get("username")
        if not username:
            return add_cors_headers(make_response(json.dumps({"error": "Missing username parameter"}), 400))

        documents = get_all_documents_for_db("tasks")
        document_list = []

        for doc in documents:
            task_data = convert_firestore_document(doc)
            task_name = task_data.get("task", "")

            if "|" in task_name:
                doc_username, actual_task_name = task_name.split("|", 1)
                if doc_username == username:
                    task_data["task"] = actual_task_name  # Remove username from task name
                    document_list.append(task_data)

        duration = time.time() - start_time
        create_custom_metric("task_api/request_duration", duration)

        log_message("INFO", "Fetched tasks successfully", {"username": username, "task_count": len(document_list)})

        response = make_response(json.dumps(document_list), 200)
        response.headers["Content-Type"] = "application/json"
        return add_cors_headers(response)

    except Exception as e:
        log_message("ERROR", f"Error fetching tasks: {str(e)}")
        return add_cors_headers(make_response(json.dumps({"error": str(e)}), 500))



def insert_task(request:Request):
    try:
        data = request.get_json(silent=True)
        print("Raw Request Data:", request.data)
        print("Content-Type Header:", request.headers.get("Content-Type"))

        if not data or "task" not in data or "description" not in data or "username" not in data:
            return add_cors_headers(make_response(json.dumps({"error": "Missing argument"}), 400))

        task_name = data["username"]+'|'+ data["task"]
        task_description = data["description"]
        task_duedate = data["duedate"]
        doc_ref = db.collection("tasks").document(task_name)
        doc_ref.set({"task": task_name, "description": task_description, "completed": False, "duedate": task_duedate})

        return add_cors_headers(make_response(json.dumps({"message": "Inserted"}), 201))
    
    except Exception as e:
        return add_cors_headers(make_response(json.dumps({"error": str(e)}), 500))


def delete_task(request:Request):
    try:
        data = request.get_json(silent=True)
        if not data or "task" not in data or "username" not in data:
            return add_cors_headers(make_response(json.dumps({"error": "Missing argument"}), 400))

        task_name = data["username"]+'|'+ data["task"]
        doc_ref = db.collection("tasks").document(task_name)

        if not doc_ref.get().exists:
            return add_cors_headers(make_response(json.dumps({"error": "Task not found"}), 404))

        doc_ref.delete()
        return add_cors_headers(make_response(json.dumps({"message": "Task Deleted"}), 200))

    except Exception as e:
        return add_cors_headers(make_response(json.dumps({"error": str(e)}), 500))

def update_task(request: Request):
    try:
        data = request.get_json(silent=True)
        if not data or "task" not in data or "username" not in data:
            return add_cors_headers(make_response(json.dumps({"error": "Missing argument"}), 400))

        task_name = data["username"] + '|' + data["task"]
        doc_ref = db.collection("tasks").document(task_name)

        if not doc_ref.get().exists:
            return add_cors_headers(make_response(json.dumps({"error": "Task not found"}), 404))

        to_update = {key: data[key] for key in data if key in TASK_FIELD and key != "task"}

        if not to_update:
            return add_cors_headers(make_response(json.dumps({"error": "Invalid fields in request"}), 400))

        doc_ref.update(to_update)

        return add_cors_headers(make_response(json.dumps({"message": "Update successful"}), 200))

    except Exception as e:
        return add_cors_headers(make_response(json.dumps({"error": str(e)}), 500))


@functions_framework.http
def cloud_function_entry_point(request):
    # Get the HTTP method
    method = request.method
    
    # Check the URL path
    path = request.path

    if path == "/get_all_tasks" and method == 'GET':
        return get_all_tasks(request)
    elif path == "/insert_task" and method == 'POST':
        return insert_task(request)
    elif path == "/delete_task" and method == 'DELETE':
        return delete_task(request)
    elif path == "/update_task" and method == 'PUT':
        return update_task(request)
    else:
        return add_cors_headers(make_response(json.dumps({"error": "Not Found or Invalid Method"}), 404))