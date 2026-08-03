from fastapi import FastAPI
from database import init_db, add_user, list_users

app = FastAPI()

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
def read_root():
    return {"message": "Grizzly Server is running!"}

@app.get("/users")
def get_users():
    return list_users()
