# Job Aggregation Service
# Simulates fetching jobs from external sources

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)

# Simulated external job sources
# In production, these would be actual API integrations or scraping services

SAMPLE_AGGREGATED_JOBS = [
    {
        "source": "linkedin",
        "company_name": "Google",
        "job_title": "Senior Software Engineer - Cloud Platform",
        "location": "Remote",
        "employment_type": "full-time",
        "short_description": "Join Google Cloud team to build scalable infrastructure",
        "skills_keywords": ["Python", "Kubernetes", "GCP", "Microservices"],
        "original_job_url": "https://linkedin.com/jobs/view/12345",
        "date_posted": datetime.now(timezone.utc) - timedelta(days=2)
    },
    {
        "source": "indeed",
        "company_name": "Amazon",
        "job_title": "Frontend Developer - React",
        "location": "Seattle, WA",
        "employment_type": "full-time",
        "short_description": "Build customer-facing applications for AWS Console",
        "skills_keywords": ["React", "TypeScript", "AWS", "JavaScript"],
        "original_job_url": "https://indeed.com/viewjob?jk=abc123",
        "date_posted": datetime.now(timezone.utc) - timedelta(hours=12)
    },
    {
        "source": "glassdoor",
        "company_name": "Microsoft",
        "job_title": "DevOps Engineer",
        "location": "Hybrid - Redmond, WA",
        "employment_type": "full-time",
        "short_description": "Manage CI/CD pipelines for Azure services",
        "skills_keywords": ["Azure", "Docker", "Jenkins", "Terraform"],
        "original_job_url": "https://glassdoor.com/job-listing/abc",
        "date_posted": datetime.now(timezone.utc) - timedelta(days=5)
    },
    {
        "source": "linkedin",
        "company_name": "Meta",
        "job_title": "Machine Learning Engineer",
        "location": "Remote",
        "employment_type": "full-time",
        "short_description": "Work on recommendation systems and AI models",
        "skills_keywords": ["Python", "TensorFlow", "PyTorch", "ML"],
        "original_job_url": "https://linkedin.com/jobs/view/67890",
        "date_posted": datetime.now(timezone.utc) - timedelta(days=1)
    },
    {
        "source": "indeed",
        "company_name": "Stripe",
        "job_title": "Backend Engineer - Payments",
        "location": "San Francisco, CA",
        "employment_type": "full-time",
        "short_description": "Build payment processing infrastructure",
        "skills_keywords": ["Ruby", "Go", "PostgreSQL", "Distributed Systems"],
        "original_job_url": "https://indeed.com/viewjob?jk=xyz789",
        "date_posted": datetime.now(timezone.utc) - timedelta(days=7)
    },
]


class JobAggregationService:
    """Service to aggregate jobs from external sources"""
    
    def __init__(self, db):
        self.db = db
        self.enabled_sources = ["linkedin", "indeed", "glassdoor"]
    
    async def fetch_from_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Simulate fetching jobs from an external source.
        In production, this would call actual APIs or scraping services.
        """
        logger.info(f"Fetching jobs from {source}")
        
        # Filter sample jobs by source
        jobs = [job for job in SAMPLE_AGGREGATED_JOBS if job["source"] == source]
        
        return jobs
    
    async def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize job data into unified schema"""
        
        job_id = str(uuid.uuid4())
        
        normalized = {
            "id": job_id,
            "source": raw_job["source"],
            "original_job_url": raw_job["original_job_url"],
            "company_name": raw_job["company_name"],
            "job_title": raw_job["job_title"],
            "location": raw_job["location"],
            "employment_type": raw_job["employment_type"],
            "short_description": raw_job["short_description"],
            "skills_keywords": raw_job["skills_keywords"],
            "date_posted": raw_job["date_posted"].isoformat() if isinstance(raw_job["date_posted"], datetime) else raw_job["date_posted"],
            "date_fetched": datetime.now(timezone.utc).isoformat(),
            "is_external": True,
            "status": "active"
        }
        
        return normalized
    
    async def check_duplicate(self, job: Dict[str, Any]) -> bool:
        """Check if job already exists (by company + title + URL)"""
        existing = await self.db.aggregated_jobs.find_one({
            "company_name": job["company_name"],
            "job_title": job["job_title"],
            "original_job_url": job["original_job_url"]
        })
        
        return existing is not None
    
    async def ingest_jobs(self, source: str = None):
        """Ingest jobs from specified source or all enabled sources"""
        sources = [source] if source else self.enabled_sources
        
        total_fetched = 0
        total_inserted = 0
        
        for src in sources:
            try:
                raw_jobs = await self.fetch_from_source(src)
                
                for raw_job in raw_jobs:
                    normalized = await self.normalize_job(raw_job)
                    
                    # Check for duplicates
                    if not await self.check_duplicate(normalized):
                        await self.db.aggregated_jobs.insert_one(normalized)
                        total_inserted += 1
                    
                    total_fetched += 1
                
                logger.info(f"Fetched {len(raw_jobs)} jobs from {src}")
            
            except Exception as e:
                logger.error(f"Error fetching from {src}: {str(e)}")
        
        logger.info(f"Ingestion complete: {total_fetched} fetched, {total_inserted} inserted")
        
        return {
            "total_fetched": total_fetched,
            "total_inserted": total_inserted,
            "sources": sources
        }
    
    async def get_aggregated_jobs(
        self,
        source: str = None,
        date_posted_days: int = None,
        location: str = None,
        employment_type: str = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get aggregated jobs with filters"""
        
        query = {"is_external": True, "status": "active"}
        
        if source:
            query["source"] = source
        
        if date_posted_days:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=date_posted_days)
            query["date_posted"] = {"$gte": cutoff_date.isoformat()}
        
        if location:
            query["location"] = {"$regex": location, "$options": "i"}
        
        if employment_type:
            query["employment_type"] = employment_type
        
        jobs = await self.db.aggregated_jobs.find(query, {"_id": 0}) \
            .sort("date_posted", -1) \
            .skip(skip) \
            .limit(limit) \
            .to_list(limit)
        
        return jobs


async def run_aggregation_job(db):
    """Background job to run aggregation"""
    service = JobAggregationService(db)
    result = await service.ingest_jobs()
    return result
