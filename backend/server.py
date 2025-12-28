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
from config import validate_environment, get_config, log_startup_info
from job_aggregation import JobAggregationService, run_aggregation_job
import json


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Validate environment on startup
try:
    validate_environment()
    CONFIG = get_config()
except Exception as e:
    logging.error(f"Configuration error: {e}")
    raise

# MongoDB connection
mongo_url = CONFIG['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[CONFIG['DB_NAME']]

JWT_SECRET = CONFIG['JWT_SECRET']
EMERGENT_LLM_KEY = CONFIG['EMERGENT_LLM_KEY']
AI_PROVIDER = CONFIG['AI_PROVIDER']
AI_MODEL = CONFIG['AI_MODEL']

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

def validate_password_strength(password: str) -> bool:
    """Validate password meets minimum security requirements"""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    if not (has_upper and has_lower and has_digit):
        raise HTTPException(
            status_code=400,
            detail="Password must contain uppercase, lowercase, and numbers"
        )
    
    return True


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


# ========== HEALTH CHECK & MONITORING ==========

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        await db.command('ping')
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": "1.0.0",
        "environment": CONFIG['DB_NAME']
    }


@app.get("/api/health/detailed")
async def detailed_health_check(current_admin: User = Depends(get_current_admin)):
    """Detailed health check (admin only)"""
    checks = {}
    
    # Database
    try:
        await db.command('ping')
        user_count = await db.users.count_documents({})
        checks['database'] = {"status": "healthy", "users": user_count}
    except Exception as e:
        checks['database'] = {"status": "unhealthy", "error": str(e)}
    
    # AI Service
    try:
        ai_service = get_ai_service()
        checks['ai_service'] = {
            "status": "configured",
            "provider": AI_PROVIDER,
            "model": AI_MODEL
        }
    except Exception as e:
        checks['ai_service'] = {"status": "error", "error": str(e)}
    
    return checks


# ========== AUTH ROUTES ==========

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    if not CONFIG['ENABLE_SIGNUP']:
        raise HTTPException(status_code=403, detail="Signups are currently disabled")
    
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate password strength
    validate_password_strength(user_data.password)
    
    user_dict = user_data.model_dump(exclude={'password'})
    user_obj = User(**user_dict)
    
    # Jobs require approval by default (unless auto-approve is enabled)
    if user_obj.role == UserRole.EMPLOYER:
        user_obj.is_approved = CONFIG['AUTO_APPROVE_EMPLOYERS']
    
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
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in CONFIG['ALLOWED_EXTENSIONS']:
        raise HTTPException(
            status_code=400,
            detail=f"File must be one of: {', '.join(CONFIG['ALLOWED_EXTENSIONS'])}"
        )
    
    try:
        # Read file with size limit
        file_bytes = await file.read()
        max_size = CONFIG['MAX_UPLOAD_SIZE_MB'] * 1024 * 1024
        
        if len(file_bytes) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {CONFIG['MAX_UPLOAD_SIZE_MB']}MB"
            )
        
        # Extract text
        resume_text = extract_text_from_file(file_bytes, file.filename)
        
        if not resume_text or len(resume_text.strip()) < 100:
            raise HTTPException(
                status_code=400,
                detail="Resume appears to be empty or too short. Please upload a complete resume."
            )
        
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

# ========== APPLICATION ROUTES ==========

@api_router.post("/applications", response_model=Application)
async def create_application(app_data: ApplicationCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(status_code=403, detail="Only job seekers can apply")
    
    existing = await db.applications.find_one({"job_id": app_data.job_id, "candidate_id": current_user.id})
    if existing:
        raise HTTPException(status_code=400, detail="Already applied to this job")
    
    job = await db.jobs.find_one({"id": app_data.job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    app_dict = app_data.model_dump()
    app_dict['candidate_id'] = current_user.id
    app_dict['candidate_name'] = current_user.full_name
    app_dict['candidate_email'] = current_user.email
    
    app_obj = Application(**app_dict)
    doc = app_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.applications.insert_one(doc)
    await db.jobs.update_one({"id": app_data.job_id}, {"$inc": {"application_count": 1}})
    
    return app_obj


@api_router.get("/applications/my-applications", response_model=List[Application])
async def get_my_applications(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(status_code=403, detail="Only job seekers can view their applications")
    
    apps = await db.applications.find({"candidate_id": current_user.id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for app in apps:
        if isinstance(app['created_at'], str):
            app['created_at'] = datetime.fromisoformat(app['created_at'])
    
    return apps


@api_router.get("/applications/job/{job_id}", response_model=List[Application])
async def get_job_applications(job_id: str, current_user: User = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job['employer_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    apps = await db.applications.find({"job_id": job_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for app in apps:
        if isinstance(app['created_at'], str):
            app['created_at'] = datetime.fromisoformat(app['created_at'])
    
    return apps


@api_router.put("/applications/{app_id}/status")
async def update_application_status(app_id: str, new_status: str, current_user: User = Depends(get_current_user)):
    app = await db.applications.find_one({"id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = await db.jobs.find_one({"id": app['job_id']})
    if job['employer_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.applications.update_one({"id": app_id}, {"$set": {"status": new_status}})
    return {"message": "Status updated successfully"}


# ========== AI ROUTES (WITH EXPLAINABILITY) ==========

@api_router.get("/ai/match-jobs", response_model=List[MatchedJob])
async def match_jobs(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(status_code=403, detail="Only job seekers can get matched jobs")
    
    if current_user.ai_credits <= 0:
        raise HTTPException(status_code=403, detail="No AI credits remaining")
    
    resume = await db.resumes.find_one({"user_id": current_user.id}, {"_id": 0})
    if not resume:
        raise HTTPException(status_code=404, detail="Please upload your resume first")
    
    jobs = await db.jobs.find({"status": "active"}, {"_id": 0}).limit(10).to_list(10)
    
    if not jobs:
        return []
    
    try:
        ai_service = get_ai_service()
        matches = await ai_service.match_jobs(resume, jobs, current_user.id)
        
        matched_jobs = []
        for match in matches:
            if match['overall_score'] >= 50:
                job_idx = match['job_index']
                if job_idx < len(jobs):
                    job_data = jobs[job_idx]
                    if isinstance(job_data['created_at'], str):
                        job_data['created_at'] = datetime.fromisoformat(job_data['created_at'])
                    
                    matched_jobs.append(MatchedJob(
                        job=Job(**job_data),
                        match_score=match['overall_score'],
                        match_breakdown={
                            "skills_score": match.get('skills_score', 0),
                            "experience_score": match.get('experience_score', 0),
                            "location_score": match.get('location_score', 0)
                        },
                        match_reason=match['reason']
                    ))
        
        matched_jobs.sort(key=lambda x: x.match_score, reverse=True)
        
        await db.users.update_one({"id": current_user.id}, {"$inc": {"ai_credits": -1}})
        
        return matched_jobs[:5]
    except Exception as e:
        logging.error(f"Job matching error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to match jobs")


@api_router.post("/ai/screen-candidate/{app_id}", response_model=ScreeningResult)
async def screen_candidate(app_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.EMPLOYER:
        raise HTTPException(status_code=403, detail="Only employers can screen candidates")
    
    if current_user.ai_credits <= 0:
        raise HTTPException(status_code=403, detail="No AI credits remaining")
    
    app = await db.applications.find_one({"id": app_id}, {"_id": 0})
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = await db.jobs.find_one({"id": app['job_id']}, {"_id": 0})
    if job['employer_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    resume = await db.resumes.find_one({"user_id": app['candidate_id']}, {"_id": 0})
    if not resume:
        raise HTTPException(status_code=404, detail="Candidate resume not found")
    
    try:
        ai_service = get_ai_service()
        screening = await ai_service.screen_candidate(job, resume, app_id)
        
        await db.applications.update_one(
            {"id": app_id},
            {"$set": {
                "ai_match_score": screening['overall_score'],
                "screening_result": screening
            }}
        )
        
        await db.users.update_one({"id": current_user.id}, {"$inc": {"ai_credits": -1}})
        
        return ScreeningResult(**screening)
    except Exception as e:
        logging.error(f"Screening error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to screen candidate")


@api_router.get("/ai/interview-prep/{job_id}")
async def get_interview_prep(job_id: str, current_user: User = Depends(get_current_user)):
    """Get interview preparation (Premium feature)"""
    if not current_user.is_premium:
        raise HTTPException(status_code=403, detail="Premium feature - upgrade required")
    
    if current_user.ai_credits <= 0:
        raise HTTPException(status_code=403, detail="No AI credits remaining")
    
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        ai_service = get_ai_service()
        prep = await ai_service.generate_interview_prep(job)
        
        await db.users.update_one({"id": current_user.id}, {"$inc": {"ai_credits": -1}})
        
        return prep
    except Exception as e:
        logging.error(f"Interview prep error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate interview prep")


# ========== PREMIUM FEATURES ==========

@api_router.post("/premium/auto-apply")
async def auto_apply_to_matches(current_user: User = Depends(get_current_user)):
    """Auto-apply to matched jobs (Premium feature)"""
    if not current_user.is_premium:
        raise HTTPException(status_code=403, detail="Premium feature - upgrade required")
    
    if current_user.ai_credits < 2:
        raise HTTPException(status_code=403, detail="Insufficient AI credits")
    
    # Get matched jobs
    resume = await db.resumes.find_one({"user_id": current_user.id}, {"_id": 0})
    if not resume:
        raise HTTPException(status_code=404, detail="Please upload your resume first")
    
    jobs = await db.jobs.find({"status": "active"}, {"_id": 0}).limit(10).to_list(10)
    
    try:
        ai_service = get_ai_service()
        matches = await ai_service.match_jobs(resume, jobs, current_user.id)
        
        applied_count = 0
        for match in matches:
            if match['overall_score'] >= 75:  # Only auto-apply to high matches
                job_idx = match['job_index']
                if job_idx < len(jobs):
                    job = jobs[job_idx]
                    
                    # Check if already applied
                    existing = await db.applications.find_one({
                        "job_id": job['id'],
                        "candidate_id": current_user.id
                    })
                    
                    if not existing:
                        app_obj = Application(
                            job_id=job['id'],
                            candidate_id=current_user.id,
                            candidate_name=current_user.full_name,
                            candidate_email=current_user.email,
                            cover_letter="Auto-applied based on AI match",
                            ai_match_score=match['overall_score']
                        )
                        
                        doc = app_obj.model_dump()
                        doc['created_at'] = doc['created_at'].isoformat()
                        
                        await db.applications.insert_one(doc)
                        await db.jobs.update_one({"id": job['id']}, {"$inc": {"application_count": 1}})
                        applied_count += 1
        
        await db.users.update_one({"id": current_user.id}, {"$inc": {"ai_credits": -2}})
        
        return {"message": f"Auto-applied to {applied_count} matching jobs"}
    except Exception as e:
        logging.error(f"Auto-apply error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to auto-apply")


# ========== STATS ROUTES ==========

@api_router.get("/stats/employer")
async def get_employer_stats(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.EMPLOYER:
        raise HTTPException(status_code=403, detail="Only employers can view stats")
    
    jobs_count = await db.jobs.count_documents({"employer_id": current_user.id})
    active_jobs = await db.jobs.count_documents({"employer_id": current_user.id, "status": "active"})
    
    all_jobs = await db.jobs.find({"employer_id": current_user.id}, {"_id": 0, "id": 1}).to_list(100)
    job_ids = [j['id'] for j in all_jobs]
    
    total_applications = await db.applications.count_documents({"job_id": {"$in": job_ids}})
    
    return {
        "total_jobs": jobs_count,
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "ai_credits": current_user.ai_credits,
        "subscription_tier": current_user.subscription_tier,
        "is_premium": current_user.is_premium
    }


@api_router.get("/stats/jobseeker")
async def get_jobseeker_stats(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(status_code=403, detail="Only job seekers can view stats")
    
    applications_count = await db.applications.count_documents({"candidate_id": current_user.id})
    has_resume = await db.resumes.find_one({"user_id": current_user.id}) is not None
    
    return {
        "total_applications": applications_count,
        "has_resume": has_resume,
        "ai_credits": current_user.ai_credits,
        "subscription_tier": current_user.subscription_tier,
        "is_premium": current_user.is_premium
    }


# ========== ADMIN ROUTES ==========

@api_router.get("/admin/users")
async def get_all_users(
    skip: int = 0,
    limit: int = 50,
    role: Optional[str] = None,
    current_admin: User = Depends(get_current_admin)
):
    """Get all users (Admin only)"""
    query = {}
    if role:
        query['role'] = role
    
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).skip(skip).limit(limit).to_list(limit)
    
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return users


@api_router.put("/admin/users/{user_id}/approve")
async def approve_user(user_id: str, current_admin: User = Depends(get_current_admin)):
    """Approve employer account"""
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_approved": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User approved"}


@api_router.put("/admin/users/{user_id}/suspend")
async def suspend_user(user_id: str, current_admin: User = Depends(get_current_admin)):
    """Suspend user account"""
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_suspended": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User suspended"}


@api_router.get("/admin/jobs/pending")
async def get_pending_jobs(current_admin: User = Depends(get_current_admin)):
    """Get jobs pending approval"""
    jobs = await db.jobs.find({"status": "pending"}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for job in jobs:
        if isinstance(job['created_at'], str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
    
    return jobs


@api_router.put("/admin/jobs/{job_id}/approve")
async def approve_job(job_id: str, current_admin: User = Depends(get_current_admin)):
    """Approve job posting"""
    result = await db.jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "active"}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": "Job approved"}


@api_router.put("/admin/jobs/{job_id}/reject")
async def reject_job(job_id: str, reason: str, current_admin: User = Depends(get_current_admin)):
    """Reject job posting"""
    result = await db.jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "rejected", "rejection_reason": reason}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": "Job rejected"}


@api_router.get("/admin/analytics")
async def get_admin_analytics(current_admin: User = Depends(get_current_admin)):
    """Get platform analytics"""
    total_users = await db.users.count_documents({})
    total_employers = await db.users.count_documents({"role": UserRole.EMPLOYER})
    total_jobseekers = await db.users.count_documents({"role": UserRole.JOB_SEEKER})
    premium_users = await db.users.count_documents({"is_premium": True})
    
    total_jobs = await db.jobs.count_documents({})
    active_jobs = await db.jobs.count_documents({"status": "active"})
    featured_jobs = await db.jobs.count_documents({"is_featured": True})
    
    total_applications = await db.applications.count_documents({})
    
    # Revenue calculation (simulated)
    professional_count = await db.users.count_documents({"subscription_tier": "professional"})
    enterprise_count = await db.users.count_documents({"subscription_tier": "enterprise"})
    monthly_revenue = (professional_count * 49) + (enterprise_count * 199) + (featured_jobs * 99)
    
    # AI usage
    users_with_credits = await db.users.find({}, {"_id": 0, "ai_credits": 1}).to_list(1000)
    total_credits_used = sum([10 - user.get('ai_credits', 10) for user in users_with_credits if user.get('ai_credits', 10) < 10])
    
    return {
        "users": {
            "total": total_users,
            "employers": total_employers,
            "job_seekers": total_jobseekers,
            "premium": premium_users
        },
        "jobs": {
            "total": total_jobs,
            "active": active_jobs,
            "featured": featured_jobs
        },
        "applications": {
            "total": total_applications
        },
        "revenue": {
            "monthly_recurring": monthly_revenue,
            "professional_subs": professional_count,
            "enterprise_subs": enterprise_count,
            "featured_jobs": featured_jobs
        },
        "ai_usage": {
            "total_credits_consumed": total_credits_used
        }
    }


# ========== JOB AGGREGATION & PREMIUM FEATURES (V1 EXTENSION) ==========

@api_router.post("/admin/jobs/aggregate")
async def trigger_aggregation(source: Optional[str] = None, current_admin: User = Depends(get_current_admin)):
    """Manually trigger job aggregation"""
    try:
        result = await run_aggregation_job(db)
        return result
    except Exception as e:
        logging.error(f"Aggregation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Aggregation failed")


@api_router.get("/jobs/all")
async def get_all_jobs_with_aggregated(
    source: Optional[str] = None,
    date_posted_days: Optional[int] = None,
    location: Optional[str] = None,
    employment_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "recent"
):
    """Get both internal and aggregated jobs"""
    all_jobs = []
    
    # Internal jobs
    internal_query = {"status": "active"}
    if location:
        internal_query["location"] = {"$regex": location, "$options": "i"}
    if date_posted_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=date_posted_days)
        internal_query["created_at"] = {"$gte": cutoff.isoformat()}
    
    internal = await db.jobs.find(internal_query, {"_id": 0}).to_list(50)
    for job in internal:
        if isinstance(job.get('created_at'), str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
        job['is_external'] = False
        job['source'] = 'jobquick'
        all_jobs.append(job)
    
    # Aggregated jobs
    service = JobAggregationService(db)
    aggregated = await service.get_aggregated_jobs(
        source=source if source != 'jobquick' else None,
        date_posted_days=date_posted_days,
        location=location,
        employment_type=employment_type,
        skip=0,
        limit=50
    )
    
    for job in aggregated:
        if isinstance(job.get('date_posted'), str):
            job['date_posted'] = datetime.fromisoformat(job['date_posted'])
        job['title'] = job.get('job_title', '')
        job['description'] = job.get('short_description', '')
        job['requirements'] = job.get('skills_keywords', [])
        all_jobs.append(job)
    
    # Sort
    if sort_by == "recent":
        all_jobs.sort(key=lambda x: x.get('date_posted') or x.get('created_at') or datetime.min, reverse=True)
    elif sort_by == "company":
        all_jobs.sort(key=lambda x: x.get('company_name', ''))
    
    return all_jobs[skip:skip+limit]


@api_router.post("/premium/boost-application")
async def boost_application(job_id: str, include_cover_letter: bool = False, current_user: User = Depends(get_current_user)):
    """Boost My Application - Tailor resume"""
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(status_code=403, detail="Only job seekers can use this")
    
    credits_needed = 25 if include_cover_letter else 15
    if current_user.ai_credits < credits_needed:
        raise HTTPException(status_code=403, detail=f"Need {credits_needed} credits")
    
    resume = await db.resumes.find_one({"user_id": current_user.id}, {"_id": 0})
    if not resume:
        raise HTTPException(status_code=404, detail="Upload resume first")
    
    # Check cache
    cache_key = f"{current_user.id}_{job_id}_{'cover' if include_cover_letter else 'basic'}"
    cached = await db.boost_cache.find_one({"cache_key": cache_key})
    if cached:
        return cached['result']
    
    # Get job
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        job = await db.aggregated_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        ai_service = get_ai_service()
        result = await ai_service.tailor_resume(resume, job, include_cover_letter)
        result['disclaimer'] = "AI-generated. Please review before using."
        
        # Cache
        await db.boost_cache.insert_one({
            "cache_key": cache_key,
            "user_id": current_user.id,
            "job_id": job_id,
            "result": result,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Deduct credits
        await db.users.update_one({"id": current_user.id}, {"$inc": {"ai_credits": -credits_needed}})
        
        return result
    except Exception as e:
        logging.error(f"Boost error: {str(e)}")
        raise HTTPException(status_code=500, detail="Boost failed")


@api_router.post("/premium/message-recruiter")
async def message_recruiter(job_id: str, tone: str = "professional", current_user: User = Depends(get_current_user)):
    """Generate recruiter messages"""
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(status_code=403, detail="Only job seekers")
    
    if current_user.ai_credits < 5:
        raise HTTPException(status_code=403, detail="Need 5 credits")
    
    if tone not in ['professional', 'friendly', 'confident']:
        raise HTTPException(status_code=400, detail="Invalid tone")
    
    resume = await db.resumes.find_one({"user_id": current_user.id}, {"_id": 0})
    if not resume:
        raise HTTPException(status_code=404, detail="Upload resume first")
    
    # Check cache
    cache_key = f"{current_user.id}_{job_id}_{tone}"
    cached = await db.message_cache.find_one({"cache_key": cache_key})
    if cached:
        return cached['result']
    
    # Get job
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        job = await db.aggregated_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        ai_service = get_ai_service()
        result = await ai_service.generate_recruiter_message(resume, job, tone)
        
        # Cache
        await db.message_cache.insert_one({
            "cache_key": cache_key,
            "user_id": current_user.id,
            "job_id": job_id,
            "tone": tone,
            "result": result,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Deduct credits
        await db.users.update_one({"id": current_user.id}, {"$inc": {"ai_credits": -5}})
        
        return result
    except Exception as e:
        logging.error(f"Message error: {str(e)}")
        raise HTTPException(status_code=500, detail="Message generation failed")


@api_router.post("/tracking/external-apply")
async def track_external_apply(job_id: str, source: str, current_user: User = Depends(get_current_user)):
    """Track external application clicks"""
    try:
        await db.external_applications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "job_id": job_id,
            "source": source,
            "clicked_at": datetime.now(timezone.utc).isoformat()
        })
        return {"message": "Tracked"}
    except:
        return {"message": "OK"}


@api_router.get("/admin/analytics/extended")
async def get_extended_analytics(current_admin: User = Depends(get_current_admin)):
    """Extended analytics"""
    base = await get_admin_analytics(current_admin)
    
    total_aggregated = await db.aggregated_jobs.count_documents({"is_external": True})
    aggregated_by_source = await db.aggregated_jobs.aggregate([
        {"$match": {"is_external": True}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]).to_list(10)
    
    external_clicks = await db.external_applications.count_documents({})
    boost_usage = await db.boost_cache.count_documents({})
    message_usage = await db.message_cache.count_documents({})
    
    extended = {
        **base,
        "aggregated_jobs": {
            "total": total_aggregated,
            "by_source": {item['_id']: item['count'] for item in aggregated_by_source}
        },
        "external_applications": {"total_clicks": external_clicks},
        "premium_features": {
            "boost_applications": boost_usage,
            "recruiter_messages": message_usage
        }
    }
    
    return extended


# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# Create admin user on startup
@app.on_event("startup")
async def create_admin_user():
    # Log startup info
    log_startup_info()
    
    admin_email = CONFIG['ADMIN_EMAIL']
    admin_password = CONFIG['ADMIN_PASSWORD']
    
    existing_admin = await db.users.find_one({"email": admin_email})
    if not existing_admin:
        admin_user = User(
            email=admin_email,
            role=UserRole.ADMIN,
            full_name="Admin User",
            subscription_tier="enterprise",
            ai_credits=999999,
            is_premium=True,
            is_approved=True
        )
        
        doc = admin_user.model_dump()
        doc['password_hash'] = hash_password(admin_password)
        doc['created_at'] = doc['created_at'].isoformat()
        
        await db.users.insert_one(doc)
        logger.info(f"✓ Admin user created: {admin_email}")
    else:
        logger.info(f"✓ Admin user exists: {admin_email}")
    
    # Create indexes for performance
    await db.users.create_index("email", unique=True)
    await db.jobs.create_index([("status", 1), ("created_at", -1)])
    await db.jobs.create_index([("is_featured", -1), ("created_at", -1)])
    await db.applications.create_index([("candidate_id", 1), ("created_at", -1)])
    await db.applications.create_index([("job_id", 1), ("created_at", -1)])
    await db.resumes.create_index("user_id", unique=True)
    logger.info("✓ Database indexes created")
    
    # Trigger initial job aggregation
    try:
        result = await run_aggregation_job(db)
        logger.info(f"✓ Initial job aggregation: {result['total_inserted']} jobs inserted")
    except Exception as e:
        logger.warning(f"⚠ Initial aggregation skipped: {str(e)}")
    
    logger.info("=" * 60)
    logger.info("🚀 JobQuick AI is ready!")
    logger.info("=" * 60)
