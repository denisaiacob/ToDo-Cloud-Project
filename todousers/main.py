from google.oauth2 import service_account
from google.cloud import bigquery
import functions_framework
import datetime
import json
from flask import make_response, Request

client = bigquery.Client()

def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
    
def get_user_by_email(email):
    query = f"SELECT username, password FROM `todo-454613.todo_users.users` WHERE email='{email}' LIMIT 1;"
    query_job = client.query(query)
    results = query_job.result()

    if results.total_rows == 0:
        return {"users": 0}  # No users found

    users = [{"username": row.username, "password": row.password} for row in results]
    return {"users": users}


def insert_user(request:Request):
    data = request.get_json(silent=True)

    if not data or "email" not in data or "username" not in data or "password" not in data:
        return add_cors_headers(make_response(json.dumps({"error": "Missing argument"}), 400))

    user = get_user_by_email(data["email"])
    if user["users"] != 0:
        return add_cors_headers(make_response(json.dumps({"error": "User with this email already exists!"}), 400))

    query = f"INSERT INTO `todo-454613.todo_users.users` (username, email, password) VALUES ('{data['username']}', '{data['email']}', '{data['password']}')"
    client.query(query)

    return add_cors_headers(make_response(json.dumps({"message": "User created"}), 201))


def login_user(request:Request):
    data = request.get_json(silent=True)

    if not data or "email" not in data or "password" not in data:
        return add_cors_headers(make_response(json.dumps({"error": "Missing argument"}), 400))

    user = get_user_by_email(data["email"])
    if user["users"] == 0:
        return add_cors_headers(make_response(json.dumps({"error": "This email does not exist in Database!"}), 404))

    if user["users"][0]["password"] == data["password"]:
        return add_cors_headers(make_response(json.dumps({"user": user["users"][0]}), 200))

    return add_cors_headers(make_response(json.dumps({"error": "Passwords not matching!"}), 401))


@functions_framework.http
def cloud_function_entry_point(request):
    # Get the HTTP method
    method = request.method
    
    # Check the URL path
    path = request.path

    if path == "/insert_user" and method == 'POST':
        return insert_user(request)
    if path == "/login_user" and method == 'POST':
        return login_user(request)
    else:
         return add_cors_headers(make_response(json.dumps({"error": "Not Found or Invalid Method"}), 404))
    