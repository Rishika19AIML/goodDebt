from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from fastapi.middleware.cors import CORSMiddleware
import models, database
from pydantic import BaseModel, EmailStr, Field
from typing import Annotated

app = FastAPI()

# configure CORS
origins = [
    "http://localhost",
    "http://localhost:5173",  # your frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables
models.Base.metadata.create_all(bind=database.engine)

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CustomerCreate(BaseModel):
    full_name: Annotated[str, Field(..., min_length=3, max_length=100)]
    email: EmailStr
    phone: Annotated[str, Field(..., pattern=r"^[6-9]\d{9}$")]  # Indian mobile
    dob: date
    pan: Annotated[str, Field(..., min_length=10, max_length=10, pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")]
    employment_type: Annotated[str, Field(..., min_length=2, max_length=50)]
    salary: Annotated[float, Field(..., gt=0)]
    departmentName: Annotated[str, Field(..., min_length=2, max_length=50)]
    designationName: Annotated[str, Field(..., min_length=2, max_length=50)]
    companyName: Annotated[str, Field(..., min_length=2, max_length=100)]
    designation: Annotated[str, Field(..., min_length=2, max_length=50)]
    city: Annotated[str, Field(..., min_length=2, max_length=50)]
    pincode: Annotated[str, Field(..., pattern=r"^\d{6}$")]  # 6-digit pincode
    existing_loan: Annotated[str, Field(..., min_length=2, max_length=20)]

    # ✅ Age Validation
    @classmethod
    def validate_dob(cls, value: date) -> date:
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 18:
            raise ValueError("Customer must be at least 18 years old")
        return value

# ✅ API Endpoint
@app.post("/customers", status_code=status.HTTP_201_CREATED)
def add_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_email = db.query(models.Customer).filter(models.Customer.email == customer.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if phone already exists
    existing_phone = db.query(models.Customer).filter(models.Customer.phone == customer.phone).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )

    # Create new customer
    new_customer = models.Customer(**customer.dict())
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    return {
        "message": "Customer added successfully",
        "customer_id": new_customer.id,
        "data": {
            "full_name": new_customer.full_name,
            "email": new_customer.email,
            "phone": new_customer.phone,
            "dob": new_customer.dob.isoformat(),
            "pan": new_customer.pan,
            "employment_type": new_customer.employment_type,
            "salary": new_customer.salary,
            "departmentName": new_customer.departmentName,
            "designationName": new_customer.designationName,
            "companyName": new_customer.companyName,
            "designation": new_customer.designation,
            "city": new_customer.city,
            "pincode": new_customer.pincode,
            "existing_loan": new_customer.existing_loan
        }
    }

# Get eligible banks for a customer
@app.get("/customers/{customer_id}/eligible-banks")
def get_eligible_banks(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()

    if not customer:
        return {"error": "Customer not found"}

    # Calculate customer age
    today = date.today()
    age = today.year - customer.dob.year - (
        (today.month, today.day) < (customer.dob.month, customer.dob.day)
    )

    # 1. Find banks matching pincode
    banks = db.query(models.Bank).filter(models.Bank.pincode == customer.pincode).all()

    eligible_banks = []

    # 2. Check loan rules for each bank
    for bank in banks:
        rules = db.query(models.LoanRule).filter(models.LoanRule.bank_id == bank.bank_id).all()
        for rule in rules:
            if (
                customer.salary >= rule.min_salary
                and customer.employment_type == rule.job_type
                and rule.min_age <= age <= rule.max_age
            ):
                # Loan eligibility calculation: salary * 5 times (example formula)
                max_loan = customer.salary * 5

                eligible_banks.append({
                    "bank_name": bank.bank_name,
                    "interest_rate": rule.interest_rate,
                    "min_salary_required": rule.min_salary,
                    "job_type": rule.job_type,
                    "age_limit": f"{rule.min_age}-{rule.max_age}",
                    "max_loan_amount": f"Up to ₹{max_loan:,.0f}"
                })
    return {
        "customer": customer.full_name,
        "age": age,
        "salary": customer.salary,
        "eligible_banks": eligible_banks
    }
