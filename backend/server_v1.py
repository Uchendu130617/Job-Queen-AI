from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from ai_service import AIService, AIProvider
from file_utils import extract_text_from_file
import json


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'openai')
AI_MODEL = os.environ.get('AI_MODEL', 'gpt-5.2')

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()


# ========== MODELS ==========

class UserRole(str):
    EMPLOYER = "employer"
    JOB_SEEKER = "job_seeker"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    role: str
    full_name: str
    company_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    subscription_tier: str = "free"
    ai_credits: int = 10
    is_premium: bool = False
    is_approved: bool = True
    is_suspended: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


class JobCreate(BaseModel):
    title: str
    description: str
    requirements: List[str]
    location: str
    salary_range: Optional[str] = None
    job_type: str
    experience_level: str
    is_featured: bool = False


class Job(JobCreate):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employer_id: str
    employer_name: str
    company_name: Optional[str] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    application_count: int = 0
    is_featured: bool = False


class ApplicationCreate(BaseModel):
    job_id: str
    cover_letter: Optional[str] = None


class Application(ApplicationCreate):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    candidate_id: str
    candidate_name: str
    candidate_email: str
    status: str = "pending"
    ai_match_score: Optional[float] = None
    match_breakdown: Optional[Dict[str, Any]] = None
    screening_result: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResumeData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    raw_text: str
    file_name: Optional[str] = None
    parsed_skills: List[str] = []
    experience_years: Optional[int] = None
    education: Optional[str] = None
    summary: Optional[str] = None
    achievements: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MatchedJob(BaseModel):
    job: Job
    match_score: float
    match_breakdown: Dict[str, Any]
    match_reason: str


class ScreeningResult(BaseModel):
    overall_score: float
    skills_match: float
    experience_match: float
    education_match: float
    strengths: List[str]
    concerns: List[str]
    recommendation: str
    detailed_analysis: str


# ========== AUTH UTILITIES ==========

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=7)):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user_doc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
        if isinstance(user_doc['created_at'], str):
            user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
        
        return User(**user_doc)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ========== AI SERVICE INSTANCE ==========

def get_ai_service() -> AIService:
    return AIService(EMERGENT_LLM_KEY, AI_PROVIDER, AI_MODEL)


# ========== AUTH ROUTES ==========

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_data.model_dump(exclude={'password'})
    user_obj = User(**user_dict)
    
    # Jobs require approval by default
    if user_obj.role == UserRole.EMPLOYER:
        user_obj.is_approved = False
    
    doc = user_obj.model_dump()
    doc['password_hash'] = hash_password(user_data.password)
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    
    access_token = create_access_token(data={"sub": user_obj.id})
    
    return TokenResponse(access_token=access_token, user=user_obj)


@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(credentials.password, user_doc['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user_doc.get('is_suspended', False):
        raise HTTPException(status_code=403, detail="Account suspended")
    
    if isinstance(user_doc['created_at'], str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    user_obj = User(**user_doc)
    access_token = create_access_token(data={"sub": user_obj.id})
    
    return TokenResponse(access_token=access_token, user=user_obj)


# ========== USER ROUTES ==========

@api_router.get("/users/me", response_model=User)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@api_router.put("/users/profile")
async def update_profile(update_data: Dict[str, Any], current_user: User = Depends(get_current_user)):
    allowed_fields = ['full_name', 'company_name']
    update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
    
    if update_fields:
        await db.users.update_one({"id": current_user.id}, {"$set": update_fields})
    
    return {"message": "Profile updated successfully"}


@api_router.post("/users/upgrade")
async def upgrade_subscription(tier: str, current_user: User = Depends(get_current_user)):
    if tier not in ['free', 'professional', 'enterprise']:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    credits_map = {'free': 10, 'professional': 100, 'enterprise': 500}
    is_premium = tier != 'free'
    
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {
            "subscription_tier": tier,
            "ai_credits": credits_map[tier],
            "is_premium": is_premium
        }}
    )
    
    return {"message": f"Upgraded to {tier} tier", "credits": credits_map[tier]}


# ========== RESUME ROUTES (WITH FILE UPLOAD) ==========

@api_router.post("/resumes/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload and parse PDF/DOCX/TXT resume"""
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(status_code=403, detail="Only job seekers can upload resumes")
    
    if current_user.ai_credits <= 0:
        raise HTTPException(status_code=403, detail="No AI credits remaining")
    
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.txt']
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="File must be PDF, DOCX, or TXT")
    
    try:
        # Read file
        file_bytes = await file.read()
        
        # Extract text
        resume_text = extract_text_from_file(file_bytes, file.filename)
        
        # Parse with AI
        ai_service = get_ai_service()
        parsed_data = await ai_service.parse_resume(resume_text, current_user.id)
        
        # Store resume
        resume_obj = ResumeData(
            user_id=current_user.id,
            raw_text=resume_text,
            file_name=file.filename,
            parsed_skills=parsed_data.get('skills', []),
            experience_years=parsed_data.get('experience_years'),
            education=parsed_data.get('education'),
            summary=parsed_data.get('summary'),
            achievements=parsed_data.get('achievements', [])
        )
        
        doc = resume_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        
        await db.resumes.update_one(
            {"user_id": current_user.id},
            {"$set": doc},
            upsert=True
        )
        
        # Decrement credits
        await db.users.update_one({"id": current_user.id}, {"$inc": {"ai_credits": -1}})
        
        return parsed_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Resume upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process resume")


@api_router.get("/resumes/optimize")
async def optimize_resume(
    job_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get resume optimization suggestions (Premium feature)"""
    if not current_user.is_premium:
        raise HTTPException(status_code=403, detail="Premium feature - upgrade required")
    
    if current_user.ai_credits <= 0:
        raise HTTPException(status_code=403, detail="No AI credits remaining")
    
    resume = await db.resumes.find_one({"user_id": current_user.id}, {"_id": 0})
    if not resume:
        raise HTTPException(status_code=404, detail="Please upload your resume first")
    
    target_job = None
    if job_id:
        job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
        if job:
            target_job = job
    
    try:
        ai_service = get_ai_service()
        optimization = await ai_service.optimize_resume(resume['raw_text'], target_job)
        
        await db.users.update_one({"id": current_user.id}, {"$inc": {"ai_credits": -1}})
        
        return optimization
    except Exception as e:
        logging.error(f"Optimization error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to optimize resume")


# ========== JOB ROUTES ==========

@api_router.post("/jobs", response_model=Job)
async def create_job(job_data: JobCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.EMPLOYER:
        raise HTTPException(status_code=403, detail="Only employers can create jobs")
    
    if not current_user.is_approved:
        raise HTTPException(status_code=403, detail="Account pending approval")
    
    job_dict = job_data.model_dump()
    job_dict['employer_id'] = current_user.id
    job_dict['employer_name'] = current_user.full_name
    job_dict['company_name'] = current_user.company_name
    job_dict['status'] = 'pending'  # Requires admin approval
    
    job_obj = Job(**job_dict)
    doc = job_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.jobs.insert_one(doc)
    
    return job_obj


@api_router.get("/jobs", response_model=List[Job])
async def get_jobs(
    status: Optional[str] = "active",
    skip: int = 0,
    limit: int = 20,
    featured_only: bool = False
):
    query = {}
    if status:
        query['status'] = status
    if featured_only:
        query['is_featured'] = True
    
    # Featured jobs first
    sort_order = [("is_featured", -1), ("created_at", -1)]
    
    jobs = await db.jobs.find(query, {"_id": 0}).sort(sort_order).skip(skip).limit(limit).to_list(limit)
    
    for job in jobs:
        if isinstance(job['created_at'], str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
    
    return jobs


@api_router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if isinstance(job['created_at'], str):
        job['created_at'] = datetime.fromisoformat(job['created_at'])
    
    return Job(**job)


@api_router.get("/jobs/employer/my-jobs", response_model=List[Job])
async def get_my_jobs(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.EMPLOYER:
        raise HTTPException(status_code=403, detail="Only employers can view their jobs")
    
    jobs = await db.jobs.find({"employer_id": current_user.id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for job in jobs:
        if isinstance(job['created_at'], str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
    
    return jobs


@api_router.post("/jobs/{job_id}/feature")
async def feature_job(job_id: str, current_user: User = Depends(get_current_user)):
    """Feature a job posting (Monetization feature)"""
    job = await db.jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job['employer_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # In production, integrate payment here
    # For now, simulate payment success
    
    await db.jobs.update_one({"id": job_id}, {"$set": {"is_featured": True}})
    
    return {"message": "Job featured successfully", "note": "Payment integration pending"}


@api_router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, current_user: User = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job['employer_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.jobs.delete_one({"id": job_id})
    return {"message": "Job deleted successfully"}


# ========== CONTINUE IN NEXT MESSAGE DUE TO LENGTH ==========
