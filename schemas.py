from pydantic import BaseModel
from datetime import date
from typing import Optional

class CustomerCreate(BaseModel):
    full_name: str
    email: str
    phone: str
    dob: date
    pan: str
    employment_type: str
    salary: float
    city: str
    pincode: str
    # existing_loan: str
    departmentName: Optional[str] = None
    designationName: Optional[str] = None
    companyName: Optional[str] = None
    designation: Optional[str] = None
