from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db, engine
import models, schemas
from datetime import date
import traceback
from fastapi.middleware.cors import CORSMiddleware
# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
origins=[
    "http://localhost",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.post("/customers/with-eligible-banks", status_code=status.HTTP_201_CREATED)
def add_or_update_customer_and_get_banks(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    try:
        # Check if customer already exists (phone OR email match)
        existing_customer = db.query(models.Customer).filter(
            (models.Customer.phone == customer.phone) | (models.Customer.email == customer.email)
        ).first()

        if existing_customer:
            # ✅ Update existing record
            for key, value in customer.dict().items():
                setattr(existing_customer, key, value)
            new_customer = existing_customer
        else:
            # ✅ Insert new record
            new_customer = models.Customer(**customer.dict())
            db.add(new_customer)

        # Annual income calculate
        new_customer.annualIncome = float(new_customer.salary) * 12

        db.commit()
        db.refresh(new_customer)

        # 🔹 Calculate age
        today = date.today()
        age = today.year - new_customer.dob.year - (
            (today.month, today.day) < (new_customer.dob.month, new_customer.dob.day)
        )

        # 🔹 Eligible banks
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

        # 🔹 Response
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
            "existing_loan": new_customer.existing_loan,
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
        elif new_customer.employment_type.lower() in ["self employed", "self employed professional"]:
            customer_data.update({
                "net_annual_income": float(new_customer.annualIncome)
            })

        return {
            "message": "Customer added/updated successfully",
            "customer": customer_data,
            "eligible_banks": eligible_banks
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected Error: {str(e)}\n{traceback.format_exc()}")

