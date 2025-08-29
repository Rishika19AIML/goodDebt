from sqlalchemy import Column, Integer, String, Date, Float, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Bank(Base):
    __tablename__ = "banks"
    bank_id = Column(Integer, primary_key=True, index=True)  
    bank_name = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=False)

    rules = relationship("LoanRule", back_populates="bank")


class LoanRule(Base):
    __tablename__ = "loan_rules"
    rule_id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("banks.bank_id"))
    min_salary = Column(DECIMAL(10,2), nullable=False)
    job_type = Column(String(50), nullable=False)
    min_age = Column(Integer, nullable=False)
    max_age = Column(Integer, nullable=False)
    interest_rate = Column(DECIMAL(5,2), nullable=False)

    bank = relationship("Bank", back_populates="rules")


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(15), unique=True, nullable=False)
    dob = Column(Date, nullable=False)
    pan = Column(String(15), unique=True, nullable=False)
    employment_type = Column(String(50), nullable=False)
    salary = Column(DECIMAL(10,2), nullable=False)
    city = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=False)
    existing_loan = Column(String(10), default="No")
    annualIncome = Column(DECIMAL(12,2))
    departmentName = Column(String(100))
    designationName = Column(String(100))
    companyName = Column(String(100))
    designation = Column(String(100))
