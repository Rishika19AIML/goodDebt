from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100))
    email = Column(String(100))
    phone = Column(String(20))
    dob = Column(Date)
    pan = Column(String(20))
    employment_type = Column(String(50))
    annualIncome = Column(Integer)
    salary = Column(Float)
    departmentName = Column(String(50))
    designationName = Column(String(50)) 
    companyName = Column(String(100))
    designation = Column(String(50))    
    city = Column(String(50))
    pincode = Column(String(10))
    existing_loan = Column(String(20))
        
class Bank(Base):
    __tablename__ = "banks"

    bank_id = Column(Integer, primary_key=True, index=True)
    bank_name = Column(String(100))
    state = Column(String(50))
    pincode = Column(String(10))

class LoanRule(Base):
    __tablename__ = "loan_rules"

    rule_id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("banks.bank_id"))
    min_salary = Column(Integer)
    job_type = Column(String(50))
    min_age = Column(Integer)
    max_age = Column(Integer)
    interest_rate = Column(Float)

    bank = relationship("Bank")