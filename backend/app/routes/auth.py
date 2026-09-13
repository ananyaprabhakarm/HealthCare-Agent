import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import AuthenticatedUser, create_access_token, get_current_user, hash_password, verify_password
from ..db import get_db
from ..models import Doctor, Patient
from ..schemas import AuthResponse, LoginRequest, MeResponse, SignupRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing_doctor = db.query(Doctor).filter(Doctor.email == payload.email).first()
    existing_patient = db.query(Patient).filter(Patient.email == payload.email).first()
    if existing_doctor or existing_patient:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    password_hash = hash_password(payload.password)

    if payload.role == "doctor":
        user = Doctor(
            name=payload.name,
            email=payload.email,
            password_hash=password_hash,
            specialization=payload.specialization,
        )
    else:
        user = Patient(
            name=payload.name,
            email=payload.email,
            password_hash=password_hash,
            phone=payload.phone,
        )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, payload.role)
    logger.info(f"📝 New {payload.role} signup: {user.email}")
    return AuthResponse(access_token=token, role=payload.role, name=user.name, email=user.email)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.email == payload.email).first()
    patient = None if doctor else db.query(Patient).filter(Patient.email == payload.email).first()

    user, role = (doctor, "doctor") if doctor else (patient, "patient")

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id, role)
    logger.info(f"🔓 {role} login: {user.email}")
    return AuthResponse(access_token=token, role=role, name=user.name, email=user.email)


@router.get("/me", response_model=MeResponse)
def me(current_user: AuthenticatedUser = Depends(get_current_user())):
    return MeResponse(id=current_user.id, role=current_user.role, name=current_user.name, email=current_user.email)
