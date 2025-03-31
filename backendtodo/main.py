from google.cloud import firestore
from google.oauth2 import service_account
import functions_framework
from datetime import datetime
from flask import Request, make_response
import json

credentials = service_account.Credentials.from_service_account_file("todo-454613-1b9473315763.json")
db = firestore.Client()
TASK_FIELD = ["completed", "created at", "description", "duedate", "task"]

def handle_options():
    response = make_response("", 204) 
    return add_cors_headers(response)

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
                    task_data["task"] = actual_task_name  
                    document_list.append(task_data)
        
        response = make_response(json.dumps(document_list), 200)
        response.headers["Content-Type"] = "application/json"
        return add_cors_headers(response)

    except Exception as e:
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
    
    method = request.method
    path = request.path

    if method == "OPTIONS":
        return handle_options()

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