from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import json
import sqlite3
import os
from database import init_db, get_connection

# Асинхронне ініціалізування при запуску
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (if needed)

app = FastAPI(
    title="Grizzly Security API",
    description="API for Grizzly Security Guard Management System",
    version="1.0.0",
    lifespan=lifespan
)

# Налаштування CORS для мобільних клієнтів
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== HEALTH CHECKS ====================

@app.get("/health")
def health_check():
    """Базова перевірка здоров'я сервера"""
    return {
        "status": "ok",
        "service": "GrizzlyDispatchApi",
        "utc": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/healthcheck")
def health_check_v1():
    """Альтернативна перевірка здоров'я"""
    return {
        "status": "ok",
        "service": "GrizzlyDispatchApi",
        "utc": datetime.utcnow().isoformat()
    }

# ==================== ROOT ====================

@app.get("/")
def read_root():
    return {
        "message": "Grizzly Server is running!",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

# ==================== EVENTS API ====================

@app.post("/api/events")
def create_event(
    type: str = Query(...),
    object_id: int = Query(...),
    employee_id: int = Query(...),
    dispatcher: str = Query(...),
    description: str = Query(""),
    status: str = Query("pending")
):
    """Створити новий подію (подання від охоронця)"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events (datetime, type, object_id, employee_id, dispatcher, description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (datetime.utcnow().isoformat(), type, object_id, employee_id, dispatcher, description, status)
            )
            conn.commit()
            return {
                "success": True,
                "event_id": cursor.lastrowid,
                "message": "Event created successfully"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@app.post("/api/events")
async def create_event_json(body: dict):
    """Створити новий подію (JSON варіант)"""
    try:
        event_type = body.get("type", "unknown")
        object_id = body.get("object_id")
        employee_id = body.get("employee_id")
        dispatcher = body.get("dispatcher", "system")
        description = body.get("description", "")
        status = body.get("status", "pending")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events (datetime, type, object_id, employee_id, dispatcher, description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (datetime.utcnow().isoformat(), event_type, object_id, employee_id, dispatcher, description, status)
            )
            conn.commit()
            return {
                "success": True,
                "event_id": cursor.lastrowid,
                "message": "Event created successfully"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== DATABASE API ====================

@app.post("/api/db/query")
async def db_query(body: dict):
    """Виконати SELECT запит до БД"""
    try:
        sql = body.get("sql", "")
        parameters = body.get("parameters", {})
        
        if not sql:
            raise HTTPException(status_code=400, detail="SQL query is required")
        
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, parameters)
            rows = cursor.fetchall()
            
            # Перетворити на список dict'ів
            result = [dict(row) for row in rows]
            
            return {"data": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/db/execute")
async def db_execute(body: dict):
    """Виконати INSERT/UPDATE/DELETE команду до БД"""
    try:
        sql = body.get("sql", "")
        parameters = body.get("parameters", {})
        
        if not sql:
            raise HTTPException(status_code=400, detail="SQL query is required")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, parameters)
            conn.commit()
            
            return {
                "success": True,
                "rows_affected": cursor.rowcount,
                "message": "Query executed successfully"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== USERS API ====================

@app.get("/users")
def get_users():
    """Отримати всіх користувачів"""
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY id")
            users = [dict(row) for row in cursor.fetchall()]
            return {"data": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users")
async def create_user(body: dict):
    """Створити нового користувача"""
    try:
        name = body.get("name", "")
        email = body.get("email", "")
        
        if not name or not email:
            raise HTTPException(status_code=400, detail="Name and email are required")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                (name, email)
            )
            conn.commit()
            return {
                "success": True,
                "user_id": cursor.lastrowid,
                "message": "User created successfully"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== REPORTS API ====================

@app.get("/reports")
def get_reports(limit: int = Query(200, le=1000)):
    """Отримати звіти про подіїи"""
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events ORDER BY datetime DESC LIMIT ?", (limit,))
            events = [dict(row) for row in cursor.fetchall()]
            return {"data": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ALARMS API ====================

@app.post("/api/alarms")
async def create_alarm(body: dict):
    """Створити сигнал тривоги"""
    try:
        object_id = body.get("object_id")
        dispatcher = body.get("dispatcher", "system")
        description = body.get("description", "Alarm triggered")
        
        # Просто логуємо як подію тривоги
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events (datetime, type, object_id, dispatcher, description, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (datetime.utcnow().isoformat(), "alarm", object_id, dispatcher, description, "active")
            )
            conn.commit()
            return {
                "success": True,
                "alarm_id": cursor.lastrowid,
                "message": "Alarm created successfully"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== LOCATION PINGS ====================

@app.post("/api/location-pings")
async def create_location_ping(body: dict):
    """Зберегти геолокацію охоронця"""
    try:
        employee_id = body.get("employee_id")
        lat = body.get("lat")
        lon = body.get("lon")
        
        # Логуємо як подію локації
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events (datetime, type, employee_id, description, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (datetime.utcnow().isoformat(), "location_ping", employee_id, f"lat:{lat},lon:{lon}", "recorded")
            )
            conn.commit()
            return {
                "success": True,
                "ping_id": cursor.lastrowid,
                "message": "Location ping recorded successfully"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
