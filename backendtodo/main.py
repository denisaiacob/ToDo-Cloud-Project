from google.cloud import firestore
from google.oauth2 import service_account
import functions_framework
# Initialize Firestore client
credentials = service_account.Credentials.from_service_account_file("todo-454613-1b9473315763.json")
db = firestore.Client()
TASK_FIELD = ["completed", "created at", "description", "duedate", "task"]

def get_all_documents_for_db(db_name):
    db_connection = db.collection(db_name)
    documents = db_connection.stream()
    return documents


def get_all_tasks(request):
    documents = get_all_documents_for_db("tasks")
    document_list = []
    for doc in documents:
        document_list.append(doc.to_dict())
    return document_list


def insert_task(request):
    if "task" not in request.form.keys():
        return "There is not 'task' field!"

    if "description" not in request.form.keys():
        return "There is not 'description' field!"

    task_name = request.form["task"]
    task_description = request.form["description"]
    doc_ref = db.collection("tasks").document(task_name)
    doc_ref.set({
        "task": task_name,
        "description": task_description,
        "completed": False
    })
    return "Inserted"


def delete_task(request):
    if "task" not in request.form.keys():
        return "There is not 'task' field in the request!"
    task_name = request.form["task"]
    doc_ref = db.collection("tasks").document(task_name)
    if not doc_ref.get().exists:
        return "There is not task to delete!"
    doc_ref.delete()
    return "Task Deleted"


def update_task(request):
    print(request.form)
    keys_list = request.form.keys()
    if len(keys_list) == 0:
        return "There is nothing in the request to Update!"
    task_name = request.form["task"]
    doc_ref = db.collection("tasks").document(task_name)
    if not doc_ref.get().exists:
        return "There is not task to update!"
    print(task_name)
    to_update = {}
    for key in keys_list:
        if key not in TASK_FIELD:
            return "We found a key which is not in the TASK_FIELD!"
        to_update[key] = request.form[key]
    doc_ref.update(to_update)
    return "Update Ok!"

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
        return jsonify({"error": "Not Found or Invalid Method"}), 404