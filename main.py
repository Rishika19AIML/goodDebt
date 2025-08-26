from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import models, database
from datetime import date
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# configure CORS
origins=[
    "http://localhost",
    "http://localhost:8000", # your frontend URL
    # add more origins as needed
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

@app.post("/customers")
def add_customer(full_name: str, email: str, phone: str, dob: date, pan: str,
                 employment_type: str, salary: float, departmentName:str, 
                 designationName:str, companyName:str, designation:str, city: str, pincode: str,
                 existing_loan: str, db: Session = Depends(get_db)):

    new_customer = models.Customer(
        full_name=full_name,
        email=email,
        phone=phone,
        dob=dob,
        pan=pan,
        employment_type=employment_type,
        salary=salary,
        departmentName=departmentName,
        designationName=designationName,
        companyName=companyName,
        designation=designation,
        city=city,
        pincode=pincode,
        existing_loan=existing_loan
    )
    
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    return {"message": "Customer added successfully", "{customer_id}customer": new_customer}

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
