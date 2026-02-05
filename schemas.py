from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date, datetime
from typing import Optional, List
from enum import Enum
import re


class AttendanceStatus(str, Enum):
    PRESENT = "Present"
    ABSENT = "Absent"


class EmployeeBase(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=50, description="Unique Employee ID")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full Name")
    email: EmailStr = Field(..., description="Email Address")
    department: str = Field(..., min_length=1, max_length=50, description="Department")

    @field_validator('employee_id')
    @classmethod
    def validate_employee_id(cls, v):
        if not re.match(r'^[A-Za-z0-9-_]+$', v):
            raise ValueError('Employee ID can only contain letters, numbers, hyphens, and underscores')
        return v.strip()

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if not v.strip():
            raise ValueError('Full name cannot be empty')
        return v.strip()

    @field_validator('department')
    @classmethod
    def validate_department(cls, v):
        if not v.strip():
            raise ValueError('Department cannot be empty')
        return v.strip()


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeResponse(EmployeeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmployeeListResponse(BaseModel):
    employees: List[EmployeeResponse]
    total: int


class AttendanceBase(BaseModel):
    date: date
    status: AttendanceStatus


class AttendanceCreate(AttendanceBase):
    employee_id: int

    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        if v > date.today():
            raise ValueError('Cannot mark attendance for future dates')
        return v


class AttendanceUpdate(BaseModel):
    status: AttendanceStatus


class AttendanceResponse(AttendanceBase):
    id: int
    employee_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AttendanceWithEmployeeResponse(AttendanceResponse):
    employee_name: str
    employee_code: str
    department: str


class AttendanceListResponse(BaseModel):
    records: List[AttendanceWithEmployeeResponse]
    total: int


class EmployeeAttendanceResponse(BaseModel):
    employee: EmployeeResponse
    attendance_records: List[AttendanceResponse]
    summary: dict


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None