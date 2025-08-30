from sqlalchemy import Column, Integer, String, Date, DECIMAL, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True)
    phone = Column(String(15), unique=True)
    dob = Column(Date)
    pan = Column(String(20), unique=True)
    employment_type = Column(String(50))
    salary = Column(DECIMAL(10,2))
    city = Column(String(50))
    pincode = Column(String(10))
    existing_loan = Column(String(10))
    annualIncome = Column(DECIMAL(12,2))
    departmentName = Column(String(100))
    designationName = Column(String(100))
    companyName = Column(String(100))
    designation = Column(String(100))


class Bank(Base):
    __tablename__ = "banks"

    bank_id = Column(Integer, primary_key=True, index=True)
    bank_name = Column(String(100), nullable=False)
    state = Column(String(50))
    pincode = Column(String(10))


class LoanRule(Base):
    __tablename__ = "loan_rules"

    rule_id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("banks.bank_id"))
    min_salary = Column(DECIMAL(10,2))
    job_type = Column(String(50))
    min_age = Column(Integer)
    max_age = Column(Integer)
    interest_rate = Column(Float)


class CustomerInterest(Base):
    __tablename__ = "customer_interests"

    interest_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    bank_id = Column(Integer, ForeignKey("banks.bank_id"))
