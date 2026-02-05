import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import date
from contextlib import asynccontextmanager

from database import engine, get_db, Base
from models import Employee, Attendance
from schemas import (
    EmployeeCreate, EmployeeResponse, EmployeeListResponse,
    AttendanceCreate, AttendanceUpdate, AttendanceResponse,
    AttendanceListResponse, AttendanceWithEmployeeResponse,
    EmployeeAttendanceResponse, ErrorResponse, AttendanceStatus
)
from crud import EmployeeCRUD, AttendanceCRUD


@asynccontextmanager
async def lifespan(app: FastAPI):
    # to create tables on startup in sqllite
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="HRMS Lite API",
    description="A lightweight Human Resource Management System API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": f"ERR_{exc.status_code}"}
    )


# Health Check
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "HRMS Lite API"}


# Dashboard Stats
@app.get("/api/dashboard/stats", tags=["Dashboard"])
async def get_dashboard_stats(db: Session = Depends(get_db)):
    total_employees = EmployeeCRUD.count(db)
    attendance_stats = AttendanceCRUD.get_today_stats(db)
    
    return {
        "total_employees": total_employees,
        "present_today": attendance_stats["present_today"],
        "absent_today": attendance_stats["absent_today"],
        "not_marked": attendance_stats["not_marked"]
    }


# ==================== EMPLOYEE ENDPOINTS ====================

@app.post(
    "/api/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Employees"],
    responses={
        400: {"model": ErrorResponse, "description": "Validation Error"},
        409: {"model": ErrorResponse, "description": "Duplicate Employee"}
    }
)
async def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    """Create a new employee record."""
    
    # Check for duplicate employee_id
    existing = EmployeeCRUD.get_by_employee_id(db, employee.employee_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee with ID '{employee.employee_id}' already exists"
        )
    
    # Check for duplicate email
    existing_email = EmployeeCRUD.get_by_email(db, employee.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee with email '{employee.email}' already exists"
        )
    
    try:
        db_employee = EmployeeCRUD.create(db, employee)
        return db_employee
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An employee with this ID or email already exists"
        )


@app.get(
    "/api/employees",
    response_model=EmployeeListResponse,
    tags=["Employees"]
)
async def list_employees(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max records to return"),
    search: Optional[str] = Query(None, description="Search query"),
    db: Session = Depends(get_db)
):
    """Get a list of all employees."""
    
    if search:
        employees = EmployeeCRUD.search(db, search)
    else:
        employees = EmployeeCRUD.get_all(db, skip=skip, limit=limit)
    
    total = EmployeeCRUD.count(db)
    
    return EmployeeListResponse(employees=employees, total=total)


@app.get(
    "/api/employees/{employee_id}",
    response_model=EmployeeResponse,
    tags=["Employees"],
    responses={404: {"model": ErrorResponse, "description": "Employee Not Found"}}
)
async def get_employee(employee_id: int, db: Session = Depends(get_db)):
    """Get a specific employee by ID."""
    
    employee = EmployeeCRUD.get_by_id(db, employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )
    return employee


@app.delete(
    "/api/employees/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Employees"],
    responses={404: {"model": ErrorResponse, "description": "Employee Not Found"}}
)
async def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    """Delete an employee and their attendance records."""
    
    if not EmployeeCRUD.delete(db, employee_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )
    return None



@app.post(
    "/api/attendance",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Attendance"],
    responses={
        400: {"model": ErrorResponse, "description": "Validation Error"},
        404: {"model": ErrorResponse, "description": "Employee Not Found"},
        409: {"model": ErrorResponse, "description": "Duplicate Attendance"}
    }
)
async def mark_attendance(attendance: AttendanceCreate, db: Session = Depends(get_db)):
    """Mark attendance for an employee."""
    
    employee = EmployeeCRUD.get_by_id(db, attendance.employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {attendance.employee_id} not found"
        )
    
    existing = AttendanceCRUD.get_existing(db, attendance.employee_id, attendance.date)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Attendance for this employee on {attendance.date} already exists"
        )
    
    try:
        db_attendance = AttendanceCRUD.create(db, attendance)
        return db_attendance
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attendance record already exists for this date"
        )


@app.get(
    "/api/attendance",
    response_model=AttendanceListResponse,
    tags=["Attendance"]
)
async def list_attendance(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    date_filter: Optional[date] = Query(None, description="Filter by date"),
    db: Session = Depends(get_db)
):
    """Get all attendance records."""
    
    records = AttendanceCRUD.get_all(db, skip=skip, limit=limit, target_date=date_filter)
    
    result = []
    for record in records:
        employee = EmployeeCRUD.get_by_id(db, record.employee_id)
        if employee:
            result.append(AttendanceWithEmployeeResponse(
                id=record.id,
                employee_id=record.employee_id,
                date=record.date,
                status=record.status,
                created_at=record.created_at,
                employee_name=employee.full_name,
                employee_code=employee.employee_id,
                department=employee.department
            ))
    
    return AttendanceListResponse(records=result, total=len(result))


@app.get(
    "/api/attendance/employee/{employee_id}",
    response_model=EmployeeAttendanceResponse,
    tags=["Attendance"],
    responses={404: {"model": ErrorResponse, "description": "Employee Not Found"}}
)
async def get_employee_attendance(
    employee_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """Get attendance records for a specific employee."""
    
    employee = EmployeeCRUD.get_by_id(db, employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )
    
    records = AttendanceCRUD.get_by_employee(db, employee_id, start_date, end_date)
    summary = AttendanceCRUD.get_summary(db, employee_id)
    
    return EmployeeAttendanceResponse(
        employee=employee,
        attendance_records=records,
        summary=summary
    )


@app.put(
    "/api/attendance/{attendance_id}",
    response_model=AttendanceResponse,
    tags=["Attendance"],
    responses={404: {"model": ErrorResponse, "description": "Attendance Not Found"}}
)
async def update_attendance(
    attendance_id: int,
    update: AttendanceUpdate,
    db: Session = Depends(get_db)
):
    """Update an attendance record status."""
    
    attendance = AttendanceCRUD.update_status(db, attendance_id, update.status)
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attendance record with ID {attendance_id} not found"
        )
    return attendance


@app.delete(
    "/api/attendance/{attendance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Attendance"],
    responses={404: {"model": ErrorResponse, "description": "Attendance Not Found"}}
)
async def delete_attendance(attendance_id: int, db: Session = Depends(get_db)):
    """Delete an attendance record."""
    
    if not AttendanceCRUD.delete(db, attendance_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attendance record with ID {attendance_id} not found"
        )
    return None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)