from fastapi import FastAPI, Depends, status
from sqlalchemy.orm import Session
from datetime import date
from fastapi.middleware.cors import CORSMiddleware
import models, database
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Annotated

app = FastAPI()

origins = ["http://localhost", "http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CustomerCreate(BaseModel):
    full_name: Annotated[str, Field(..., min_length=3, max_length=100)]
    email: EmailStr
    phone: Annotated[str, Field(..., pattern=r"^[6-9]\d{9}$")]
    dob: date
    pan: Annotated[str, Field(..., min_length=10, max_length=10, pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")]
    employment_type: Annotated[str, Field(..., min_length=2, max_length=50)]
    salary: Annotated[float, Field(..., gt=0)]
    departmentName: str | None = None
    designationName: str | None = None
    companyName: str | None = None
    designation: str | None = None
    city: str
    pincode: Annotated[str, Field(..., pattern=r"^\d{6}$")]

    @field_validator("dob")
    def validate_dob(cls, value: date):
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 18:
            raise ValueError("Customer must be at least 18 years old")
        return value


@app.post("/customers/with-eligible-banks", status_code=status.HTTP_201_CREATED)
def add_or_update_customer_and_get_banks(customer: CustomerCreate, db: Session = Depends(get_db)):
    existing_customer = db.query(models.Customer).filter(
        (models.Customer.email == customer.email) | (models.Customer.phone == customer.phone)
    ).first()

    if existing_customer:
        for key, value in customer.dict().items():
            setattr(existing_customer, key, value)
        new_customer = existing_customer
    else:
        new_customer = models.Customer(**customer.dict())
        db.add(new_customer)

    new_customer.annualIncome = new_customer.salary * 12
    db.commit()
    db.refresh(new_customer)

    # Age calculate
    today = date.today()
    age = today.year - new_customer.dob.year - (
        (today.month, today.day) < (new_customer.dob.month, new_customer.dob.day)
    )

    # Banks eligibility
    banks = db.query(models.Bank).filter(models.Bank.pincode == new_customer.pincode).all()
    eligible_banks = []
    for bank in banks:
        rules = db.query(models.LoanRule).filter(models.LoanRule.bank_id == bank.bank_id).all()
        for rule in rules:
            if (
                float(new_customer.salary) >= float(rule.min_salary)
                and new_customer.employment_type.lower() == rule.job_type.lower()
                and rule.min_age <= age <= rule.max_age
            ):
                max_loan = float(new_customer.salary) * 5
                eligible_banks.append({
                    "bank_name": bank.bank_name,
                    "interest_rate": float(rule.interest_rate),
                    "min_salary_required": float(rule.min_salary),
                    "job_type": rule.job_type,
                    "age_limit": f"{rule.min_age}-{rule.max_age}",
                    "max_loan_amount": f"Up to ₹{max_loan:,.0f}"
                })

    # Employment type ke hisaab se response fields filter
    customer_data = {
        "id": new_customer.id,
        "full_name": new_customer.full_name,
        "email": new_customer.email,
        "phone": new_customer.phone,
        "dob": new_customer.dob.isoformat(),
        "pan": new_customer.pan,
        "employment_type": new_customer.employment_type,
        "city": new_customer.city,
        "pincode": new_customer.pincode,
        "age": age,
    }

    if new_customer.employment_type.lower() == "private employee":
        customer_data.update({
            "net_monthly_salary": float(new_customer.salary),
            "departmentName": new_customer.departmentName,
            "designationName": new_customer.designationName,
            "companyName": new_customer.companyName
        })

    elif new_customer.employment_type.lower() == "government":
        customer_data.update({
            "net_monthly_salary": float(new_customer.salary),
            "departmentName": new_customer.departmentName,
            "designationName": new_customer.designationName
        })

    elif new_customer.employment_type.lower() == "self employed":
        customer_data.update({
            "net_annual_income": float(new_customer.annualIncome)
        })

    elif new_customer.employment_type.lower() == "self employed professional":
        customer_data.update({
            "net_annual_income": float(new_customer.annualIncome)
        })

    return {
        "message": "Customer added/updated successfully",
        "customer": customer_data,
        "eligible_banks": eligible_banks
    }
