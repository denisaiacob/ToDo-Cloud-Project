from google.oauth2 import service_account
from google.cloud import bigquery
import functions_framework

client = bigquery.Client()
    
def get_user_by_email(request):
    if "email" not in request.form.keys():
        return "There is not 'email' field!"
    query = "SELECT username, password FROM `todo-454613.todo_users.users` WHERE email=\"{}\" LIMIT 1;".format(request.form["email"])
    query_job = client.query(query)
    results = query_job.result()
    if results.total_rows == 0:
        return {"users": 0} 
    users = [{"username": row.username, "password": row.password} for row in results]
    return {"users": users}


def insert_user(request):
    if "email" not in request.form.keys():
        return "There is not 'email' field!"
    if "username" not in request.form.keys():
        return "There is not 'username' field!"
    if "password" not in request.form.keys():
        return "There is not 'password' field!"
    
    user = get_user_by_email(request)
    if not user["users"] == 0:
        return "User with this email already exists!"
    
    query = "INSERT INTO `todo-454613.todo_users.users` VALUES (\"{}\", \"{}\", \"{}\")".format(request.form["username"], request.form["email"], request.form["password"])
    query_job = client.query(query)
    results = query_job.result()

    return "User created"

def login_user(request):
    if "email" not in request.form.keys():
        return "There is not 'email' field!"
    if "password" not in request.form.keys():
        return "There is not 'password' field!"
    
    user = get_user_by_email(request)
    if user["users"] == 0:
        return "This email does not exist in Database!"
    
    password = user["users"][0]["password"]
    if password == request.form["password"]:
       return {"user": user["users"][0]}

    return {"user": "Passwords not matching!"}


@functions_framework.http
def cloud_function_entry_point(request):
    method = request.method
    
    path = request.path

    if path == "/insert_user" and method == 'POST':
        return insert_user(request)
    if path == "/login_user" and method == 'POST':
        return login_user(request)
    else:
        return jsonify({"error": "Not Found or Invalid Method"}), 404
    