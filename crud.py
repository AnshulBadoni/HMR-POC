from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, func
from typing import Optional, List
from datetime import date
from models import Employee, Attendance, AttendanceStatus
from schemas import EmployeeCreate, AttendanceCreate


class EmployeeCRUD:
    @staticmethod
    def create(db: Session, employee: EmployeeCreate) -> Employee:
        db_employee = Employee(
            employee_id=employee.employee_id,
            full_name=employee.full_name,
            email=employee.email.lower(),
            department=employee.department
        )
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        return db_employee

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Employee]:
        return db.query(Employee).order_by(Employee.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_id(db: Session, employee_id: int) -> Optional[Employee]:
        return db.query(Employee).filter(Employee.id == employee_id).first()

    @staticmethod
    def get_by_employee_id(db: Session, employee_id: str) -> Optional[Employee]:
        return db.query(Employee).filter(Employee.employee_id == employee_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[Employee]:
        return db.query(Employee).filter(Employee.email == email.lower()).first()

    @staticmethod
    def delete(db: Session, employee_id: int) -> bool:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if employee:
            db.delete(employee)
            db.commit()
            return True
        return False

    @staticmethod
    def count(db: Session) -> int:
        return db.query(Employee).count()

    @staticmethod
    def search(db: Session, query: str) -> List[Employee]:
        search_pattern = f"%{query}%"
        return db.query(Employee).filter(
            (Employee.full_name.ilike(search_pattern)) |
            (Employee.employee_id.ilike(search_pattern)) |
            (Employee.department.ilike(search_pattern))
        ).all()


class AttendanceCRUD:
    @staticmethod
    def create(db: Session, attendance: AttendanceCreate) -> Attendance:
        db_attendance = Attendance(
            employee_id=attendance.employee_id,
            date=attendance.date,
            status=attendance.status
        )
        db.add(db_attendance)
        db.commit()
        db.refresh(db_attendance)
        return db_attendance

    @staticmethod
    def get_by_employee(
        db: Session, 
        employee_id: int, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Attendance]:
        query = db.query(Attendance).filter(Attendance.employee_id == employee_id)
        
        if start_date:
            query = query.filter(Attendance.date >= start_date)
        if end_date:
            query = query.filter(Attendance.date <= end_date)
        
        return query.order_by(Attendance.date.desc()).all()

    @staticmethod
    def get_by_date(db: Session, target_date: date) -> List[Attendance]:
        return db.query(Attendance).filter(Attendance.date == target_date).all()

    @staticmethod
    def get_existing(db: Session, employee_id: int, target_date: date) -> Optional[Attendance]:
        return db.query(Attendance).filter(
            and_(
                Attendance.employee_id == employee_id,
                Attendance.date == target_date
            )
        ).first()

    @staticmethod
    def update_status(db: Session, attendance_id: int, status: AttendanceStatus) -> Optional[Attendance]:
        attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
        if attendance:
            attendance.status = status
            db.commit()
            db.refresh(attendance)
        return attendance

    @staticmethod
    def delete(db: Session, attendance_id: int) -> bool:
        attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
        if attendance:
            db.delete(attendance)
            db.commit()
            return True
        return False

    @staticmethod
    def get_all(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        target_date: Optional[date] = None
    ) -> List[Attendance]:
        query = db.query(Attendance)
        if target_date:
            query = query.filter(Attendance.date == target_date)
        return query.order_by(Attendance.date.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_summary(db: Session, employee_id: int) -> dict:
        total = db.query(Attendance).filter(Attendance.employee_id == employee_id).count()
        present = db.query(Attendance).filter(
            and_(
                Attendance.employee_id == employee_id,
                Attendance.status == AttendanceStatus.PRESENT
            )
        ).count()
        absent = total - present
        
        return {
            "total_days": total,
            "present_days": present,
            "absent_days": absent,
            "attendance_percentage": round((present / total * 100), 2) if total > 0 else 0
        }

    @staticmethod
    def get_today_stats(db: Session) -> dict:
        today = date.today()
        total_employees = db.query(Employee).count()
        present_today = db.query(Attendance).filter(
            and_(
                Attendance.date == today,
                Attendance.status == AttendanceStatus.PRESENT
            )
        ).count()
        absent_today = db.query(Attendance).filter(
            and_(
                Attendance.date == today,
                Attendance.status == AttendanceStatus.ABSENT
            )
        ).count()
        
        return {
            "total_employees": total_employees,
            "present_today": present_today,
            "absent_today": absent_today,
            "not_marked": total_employees - present_today - absent_today
        }