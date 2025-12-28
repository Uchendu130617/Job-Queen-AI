from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
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
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()


# ========== MODELS ==========

class UserRole(str):
    EMPLOYER = "employer"
    JOB_SEEKER = "job_seeker"


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


class Job(JobCreate):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employer_id: str
    employer_name: str
    company_name: Optional[str] = None
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    application_count: int = 0


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
    screening_result: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResumeData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    raw_text: str
    parsed_skills: List[str] = []
    experience_years: Optional[int] = None
    education: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MatchedJob(BaseModel):
    job: Job
    match_score: float
    match_reason: str


class ScreeningResult(BaseModel):
    score: float
    strengths: List[str]
    concerns: List[str]
    recommendation: str


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


# ========== AUTH ROUTES ==========

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_data.model_dump(exclude={'password'})
    user_obj = User(**user_dict)
    
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
    
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"subscription_tier": tier, "ai_credits": credits_map[tier]}}
    )
    
    return {"message": f"Upgraded to {tier} tier", "credits": credits_map[tier]}


# ========== JOB ROUTES ==========

@api_router.post("/jobs", response_model=Job)
async def create_job(job_data: JobCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.EMPLOYER:
        raise HTTPException(status_code=403, detail="Only employers can create jobs")
    
    job_dict = job_data.model_dump()
    job_dict['employer_id'] = current_user.id
    job_dict['employer_name'] = current_user.full_name
    job_dict['company_name'] = current_user.company_name
    
    job_obj = Job(**job_dict)
    doc = job_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.jobs.insert_one(doc)
    
    return job_obj


@api_router.get("/jobs", response_model=List[Job])
async def get_jobs(status: Optional[str] = None, skip: int = 0, limit: int = 20):
    query = {}
    if status:
        query['status'] = status
    
    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
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


@api_router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, current_user: User = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job['employer_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.jobs.delete_one({"id": job_id})
    return {"message": "Job deleted successfully"}


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


# ========== AI ROUTES ==========

@api_router.post("/ai/parse-resume")
async def parse_resume(resume_text: str, current_user: User = Depends(get_current_user)):
    if current_user.ai_credits <= 0:
        raise HTTPException(status_code=403, detail="No AI credits remaining. Please upgrade.")
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"parse_{current_user.id}_{uuid.uuid4()}",
            system_message="You are an expert resume parser. Extract key information from resumes."
        ).with_model("openai", "gpt-5.2")
        
        prompt = f"""Parse this resume and extract:
1. List of skills (as JSON array)
2. Years of experience (as integer)
3. Education level
4. Brief professional summary (2-3 sentences)

Resume text:
{resume_text}

Respond ONLY with valid JSON in this format:
{{
  "skills": ["skill1", "skill2"],
  "experience_years": 5,
  "education": "Bachelor's in Computer Science",
  "summary": "Professional summary here"
}}"""
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        parsed_data = json.loads(response)
        
        resume_obj = ResumeData(
            user_id=current_user.id,
            raw_text=resume_text,
            parsed_skills=parsed_data.get('skills', []),
            experience_years=parsed_data.get('experience_years'),
            education=parsed_data.get('education'),
            summary=parsed_data.get('summary')
        )
        
        doc = resume_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        
        await db.resumes.update_one(
            {"user_id": current_user.id},
            {"$set": doc},
            upsert=True
        )
        
        await db.users.update_one({"id": current_user.id}, {"$inc": {"ai_credits": -1}})
        
        return parsed_data
    except Exception as e:
        logging.error(f"Resume parsing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to parse resume")


@api_router.get("/ai/match-jobs", response_model=List[MatchedJob])
async def match_jobs(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(status_code=403, detail="Only job seekers can get matched jobs")
    
    if current_user.ai_credits <= 0:
        raise HTTPException(status_code=403, detail="No AI credits remaining. Please upgrade.")
    
    resume = await db.resumes.find_one({"user_id": current_user.id}, {"_id": 0})
    if not resume:
        raise HTTPException(status_code=404, detail="Please upload your resume first")
    
    jobs = await db.jobs.find({"status": "active"}, {"_id": 0}).limit(10).to_list(10)
    
    if not jobs:
        return []
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"match_{current_user.id}_{uuid.uuid4()}",
            system_message="You are an expert job matching AI. Match candidates with relevant jobs."
        ).with_model("openai", "gpt-5.2")
        
        jobs_summary = "\n".join([f"{i+1}. {job['title']} - {job['description'][:200]}" for i, job in enumerate(jobs)])
        
        prompt = f"""Candidate Profile:
Skills: {', '.join(resume.get('parsed_skills', []))}
Experience: {resume.get('experience_years', 0)} years
Education: {resume.get('education', 'Not specified')}
Summary: {resume.get('summary', '')}

Available Jobs:
{jobs_summary}

For each job, provide a match score (0-100) and brief reason. Respond ONLY with valid JSON array:
[
  {{"job_index": 0, "score": 85, "reason": "Strong match because..."}},
  {{"job_index": 1, "score": 60, "reason": "Partial match because..."}}
]"""
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        matches = json.loads(response)
        
        matched_jobs = []
        for match in matches:
            if match['score'] >= 50:
                job_idx = match['job_index']
                if job_idx < len(jobs):
                    job_data = jobs[job_idx]
                    if isinstance(job_data['created_at'], str):
                        job_data['created_at'] = datetime.fromisoformat(job_data['created_at'])
                    
                    matched_jobs.append(MatchedJob(
                        job=Job(**job_data),
                        match_score=match['score'],
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
        raise HTTPException(status_code=403, detail="No AI credits remaining. Please upgrade.")
    
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
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"screen_{app_id}_{uuid.uuid4()}",
            system_message="You are an expert recruitment screener. Evaluate candidates objectively."
        ).with_model("openai", "gpt-5.2")
        
        prompt = f"""Job Requirements:
Title: {job['title']}
Requirements: {', '.join(job['requirements'])}
Experience Level: {job['experience_level']}

Candidate Profile:
Skills: {', '.join(resume.get('parsed_skills', []))}
Experience: {resume.get('experience_years', 0)} years
Education: {resume.get('education', 'Not specified')}

Provide screening result as JSON:
{{
  "score": 75,
  "strengths": ["strength1", "strength2"],
  "concerns": ["concern1"],
  "recommendation": "Recommend for interview / Not recommended / Needs more info"
}}"""
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        screening = json.loads(response)
        
        await db.applications.update_one(
            {"id": app_id},
            {"$set": {
                "ai_match_score": screening['score'],
                "screening_result": screening
            }}
        )
        
        await db.users.update_one({"id": current_user.id}, {"$inc": {"ai_credits": -1}})
        
        return ScreeningResult(**screening)
    except Exception as e:
        logging.error(f"Screening error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to screen candidate")


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
        "subscription_tier": current_user.subscription_tier
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
        "subscription_tier": current_user.subscription_tier
    }


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
