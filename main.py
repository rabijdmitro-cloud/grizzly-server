from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
import sqlite3
import logging
from database import init_db, get_connection


logger = logging.getLogger("grizzly.api")


def _coerce_param_value(value: Any) -> Any:
    """Convert common string payload values into DB-friendly Python values."""
    if value is None:
        return None

    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed == "":
            return None

        lowered = trimmed.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        if lowered in {"null", "none"}:
            return None

        try:
            if "." in trimmed:
                return float(trimmed)
            return int(trimmed)
        except ValueError:
            return trimmed

    return value


def _normalize_parameters(parameters: Any) -> Any:
    """Support positional params and named params with/without @/:/$ prefix."""
    if parameters is None:
        return []

    if isinstance(parameters, (list, tuple)):
        return [_coerce_param_value(item) for item in parameters]

    if isinstance(parameters, dict):
        normalized: dict[str, Any] = {}
        for raw_key, raw_value in parameters.items():
            key = str(raw_key)
            value = _coerce_param_value(raw_value)

            normalized[key] = value

            stripped = key.lstrip("@:$")
            normalized[stripped] = value
            normalized[f"@{stripped}"] = value
            normalized[f":{stripped}"] = value
            normalized[f"${stripped}"] = value

        return normalized

    raise HTTPException(status_code=400, detail="Parameters must be an object, array, or null")

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
async def create_event(request: Request):
    """Створити новий подію (подання від охоронця)"""
    try:
        body = await request.json()
        
        event_type = body.get("type", body.get("Type", "unknown"))
        object_id = body.get("object_id", body.get("ObjectId"))
        employee_id = body.get("employee_id", body.get("EmployeeId"))
        dispatcher = body.get("dispatcher", body.get("Dispatcher", "system"))
        description = body.get("description", body.get("Description", ""))
        status = body.get("status", body.get("Status", "pending"))
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("create_event failed")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== DATABASE API ====================

@app.post("/api/db/query")
async def db_query(request: Request):
    """Виконати SELECT запит до БД"""
    sql = ""
    parameters = None
    try:
        body = await request.json()
        sql = body.get("sql", "")
        parameters = body.get("parameters")
        
        if not sql:
            raise HTTPException(status_code=400, detail="SQL query is required")
        
        normalized_parameters = _normalize_parameters(parameters)

        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(sql, normalized_parameters)
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            return {"rows": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("db_query failed: sql=%r parameters=%r", sql, parameters)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/db/execute")
async def db_execute(request: Request):
    """Виконати INSERT/UPDATE/DELETE команду до БД"""
    sql = ""
    parameters = None
    try:
        body = await request.json()
        sql = body.get("sql", "")
        parameters = body.get("parameters")
        
        if not sql:
            raise HTTPException(status_code=400, detail="SQL query is required")
        
        normalized_parameters = _normalize_parameters(parameters)

        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(sql, normalized_parameters)
            conn.commit()
            
            return {
                "success": True,
                "rows_affected": cursor.rowcount,
                "message": "Query executed successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("db_execute failed: sql=%r parameters=%r", sql, parameters)
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
async def create_user(request: Request):
    """Створити нового користувача"""
    try:
        body = await request.json()
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== REPORTS API ====================

@app.get("/reports")
def get_reports(limit: int = 200):
    try:
        limit = min(limit, 1000)
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Повертаємо поля з назвами які очікує Windows EXE
            cursor.execute("""
                SELECT
                    e.id            AS external_id,
                    e.datetime      AS datetime,
                    e.type          AS entity_type,
                    COALESCE(o.name, CAST(e.object_id AS TEXT), '')   AS object_name,
                    COALESCE(emp.full_name, CAST(e.employee_id AS TEXT), '') AS employee_name,
                    e.dispatcher    AS client_name,
                    e.description   AS description,
                    e.status        AS status
                FROM events e
                LEFT JOIN objects  o   ON o.id   = e.object_id
                LEFT JOIN employees emp ON emp.id = e.employee_id
                ORDER BY e.datetime DESC
                LIMIT ?
            """, (limit,))
            return {"data": [dict(row) for row in cursor.fetchall()]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ALARMS API ====================

@app.post("/api/alarms")
async def create_alarm(request: Request):
    """Створити сигнал тривоги"""
    try:
        body = await request.json()
        object_id = body.get("object_id", body.get("ObjectId"))
        dispatcher = body.get("dispatcher", body.get("Dispatcher", "system"))
        description = body.get("description", body.get("Description", "Alarm triggered"))
        
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
async def create_location_ping(request: Request):
    """Зберегти геолокацію охоронця"""
    try:
        body = await request.json()
        employee_id = body.get("employee_id", body.get("EmployeeId"))
        lat = body.get("lat", body.get("Lat"))
        lon = body.get("lon", body.get("Lon"))
        
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

        raise HTTPException(status_code=500, detail=str(e))
