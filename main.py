from fastapi import FastAPI, Depends, status, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from fastapi.middleware.cors import CORSMiddleware
import models, database
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Annotated, List, Dict, Any

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


def calculate_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def get_eligible_banks(db: Session, customer) -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns a dictionary with 'eligible_banks' and 'ineligible_banks'.
    Ineligible banks include the reason why the customer is not eligible.
    """
    age = calculate_age(customer.dob)
    banks = db.query(models.Bank).filter(models.Bank.pincode == customer.pincode).all()
    
    eligible_banks = []
    ineligible_banks = []
    
    for bank in banks:
        rules = db.query(models.LoanRule).filter(models.LoanRule.bank_id == bank.bank_id).all()
        bank_eligible = False

        for rule in rules:
            reasons = []
            # Check salary
            if float(customer.salary) < float(rule.min_salary):
                reasons.append(f"Minimum salary required is ₹{rule.min_salary:,.0f}")
            # Check employment type
            if customer.employment_type.lower() != rule.job_type.lower():
                reasons.append(f"Job type should be '{rule.job_type}'")
            # Check age
            if not (rule.min_age <= age <= rule.max_age):
                reasons.append(f"Age must be between {rule.min_age} and {rule.max_age}")

            if not reasons:
                # Eligible
                max_loan = float(customer.salary) * 5
                eligible_banks.append({
                    "bank_name": bank.bank_name,
                    "interest_rate": float(rule.interest_rate),
                    "min_salary_required": float(rule.min_salary),
                    "job_type": rule.job_type,
                    "age_limit": f"{rule.min_age}-{rule.max_age}",
                    "max_loan_amount": f"Up to ₹{max_loan:,.0f}"
                })
                bank_eligible = True
                break  # Stop checking other rules if eligible

        if not bank_eligible:
            ineligible_banks.append({
                "bank_name": bank.bank_name,
                "reasons": reasons if reasons else ["No matching loan rules for your profile"]
            })

    return {"eligible_banks": eligible_banks, "ineligible_banks": ineligible_banks}



def prepare_customer_response(customer) -> Dict[str, Any]:
    age = calculate_age(customer.dob)
    data = {
        "id": customer.id,
        "full_name": customer.full_name,
        "email": customer.email,
        "phone": customer.phone,
        "dob": customer.dob.isoformat(),
        "pan": customer.pan,
        "employment_type": customer.employment_type,
        "city": customer.city,
        "pincode": customer.pincode,
        "age": age,
    }

    employment_type = customer.employment_type.lower()
    if employment_type == "private employee":
        data.update({
            "net_monthly_salary": float(customer.salary),
            "departmentName": customer.departmentName,
            "designationName": customer.designationName,
            "companyName": customer.companyName
        })
    elif employment_type == "government":
        data.update({
            "net_monthly_salary": float(customer.salary),
            "departmentName": customer.departmentName,
            "designationName": customer.designationName
        })
    elif employment_type in ["self employed", "self employed professional"]:
        data.update({
            "net_annual_income": float(customer.salary) * 12
        })
    return data

@app.post("/customers/with-eligible-banks", status_code=status.HTTP_200_OK)
def add_or_get_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    try:
        # Normalize fields to avoid mismatch issues
        customer.employment_type = customer.employment_type.strip()
        customer.pincode = customer.pincode.strip()
        customer.salary = float(customer.salary)

        existing_customer = db.query(models.Customer).filter(
            (models.Customer.email == customer.email) | (models.Customer.phone == customer.phone)
        ).first()

        if existing_customer:
            message = "Customer already exists. Sending details and bank eligibility."
            customer_obj = existing_customer
        else:
            customer_obj = models.Customer(**customer.dict())
            customer_obj.annualIncome = customer_obj.salary * 12
            db.add(customer_obj)
            db.commit()
            db.refresh(customer_obj)
            message = "Customer added successfully."

        banks_info = get_eligible_banks(db, customer_obj)
        customer_data = prepare_customer_response(customer_obj)

        return {
            "message": message,
            "customer": customer_data,
            "eligible_banks": banks_info["eligible_banks"],
            "ineligible_banks": banks_info["ineligible_banks"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )
