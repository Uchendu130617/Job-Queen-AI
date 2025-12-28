# JobQuick AI V1 Extension - Job Aggregation & Premium Features
# This file extends the existing server.py with new endpoints

from job_aggregation import JobAggregationService, run_aggregation_job

# ========== JOB AGGREGATION ROUTES ==========

@api_router.post("/admin/jobs/aggregate")
async def trigger_aggregation(source: Optional[str] = None, current_admin: User = Depends(get_current_admin)):
    """Manually trigger job aggregation (Admin only)"""
    try:
        result = await run_aggregation_job(db)
        return result
    except Exception as e:
        logging.error(f"Aggregation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Aggregation failed")


@api_router.get("/jobs/aggregated")
async def get_aggregated_jobs(
    source: Optional[str] = None,
    date_posted_days: Optional[int] = None,
    location: Optional[str] = None,
    employment_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
):
    """Get aggregated external jobs with filters"""
    service = JobAggregationService(db)
    
    jobs = await service.get_aggregated_jobs(
        source=source,
        date_posted_days=date_posted_days,
        location=location,
        employment_type=employment_type,
        skip=skip,
        limit=limit
    )
    
    return jobs


@api_router.get("/jobs/all")
async def get_all_jobs(
    source: Optional[str] = None,
    date_posted_days: Optional[int] = None,
    location: Optional[str] = None,
    employment_type: Optional[str] = None,
    job_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "recent"
):
    """Get both internal and aggregated jobs with unified filters"""
    
    all_jobs = []
    
    # Get internal jobs
    internal_query = {"status": "active"}
    
    if location:
        internal_query["location"] = {"$regex": location, "$options": "i"}
    
    if employment_type:
        internal_query["job_type"] = employment_type
    
    if date_posted_days:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=date_posted_days)
        internal_query["created_at"] = {"$gte": cutoff_date.isoformat()}
    
    internal_jobs = await db.jobs.find(internal_query, {"_id": 0}).to_list(50)
    
    for job in internal_jobs:
        if isinstance(job.get('created_at'), str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
        job['is_external'] = False
        job['source'] = 'jobquick'
        all_jobs.append(job)
    
    # Get aggregated jobs
    service = JobAggregationService(db)
    aggregated_jobs = await service.get_aggregated_jobs(
        source=source if source != 'jobquick' else None,
        date_posted_days=date_posted_days,
        location=location,
        employment_type=employment_type,
        skip=0,
        limit=50
    )
    
    for job in aggregated_jobs:
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
    
    # Paginate
    paginated = all_jobs[skip:skip+limit]
    
    return paginated


# ========== BOOST MY APPLICATION ==========

@api_router.post("/premium/boost-application")
async def boost_application(
    job_id: str,
    include_cover_letter: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Boost My Application - Tailor resume for job (Premium feature)"""
    
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(status_code=403, detail="Only job seekers can use this feature")
    
    # Check credits
    credits_needed = 25 if include_cover_letter else 15
    if current_user.ai_credits < credits_needed:
        raise HTTPException(status_code=403, detail=f"Insufficient credits. Need {credits_needed}, have {current_user.ai_credits}")
    
    # Get resume
    resume = await db.resumes.find_one({"user_id": current_user.id}, {"_id": 0})
    if not resume:
        raise HTTPException(status_code=404, detail="Please upload your resume first")
    
    # Check cache
    cache_key = f"{current_user.id}_{job_id}_{'cover' if include_cover_letter else 'basic'}"
    cached = await db.boost_cache.find_one({"cache_key": cache_key})
    
    if cached:
        logger.info(f"Returning cached boost for {cache_key}")
        return cached['result']
    
    # Get job (internal or aggregated)
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        job = await db.aggregated_jobs.find_one({"id": job_id}, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        ai_service = get_ai_service()
        result = await ai_service.tailor_resume(resume, job, include_cover_letter)
        
        # Add disclaimer
        result['disclaimer'] = "This is AI-generated content based on your existing resume. Please review and edit before using."
        
        # Cache result
        await db.boost_cache.insert_one({
            "cache_key": cache_key,
            "user_id": current_user.id,
            "job_id": job_id,
            "result": result,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Deduct credits
        await db.users.update_one(
            {"id": current_user.id},
            {"$inc": {"ai_credits": -credits_needed}}
        )
        
        return result
    
    except Exception as e:
        logging.error(f"Boost application error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to boost application")


# ========== MESSAGE RECRUITER ==========

@api_router.post("/premium/message-recruiter")
async def message_recruiter(
    job_id: str,
    tone: str = "professional",
    current_user: User = Depends(get_current_user)
):
    """Generate recruiter outreach messages (Premium feature)"""
    
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(status_code=403, detail="Only job seekers can use this feature")
    
    # Check credits
    credits_needed = 5
    if current_user.ai_credits < credits_needed:
        raise HTTPException(status_code=403, detail=f"Insufficient credits. Need {credits_needed}, have {current_user.ai_credits}")
    
    # Validate tone
    if tone not in ['professional', 'friendly', 'confident']:
        raise HTTPException(status_code=400, detail="Tone must be: professional, friendly, or confident")
    
    # Get resume
    resume = await db.resumes.find_one({"user_id": current_user.id}, {"_id": 0})
    if not resume:
        raise HTTPException(status_code=404, detail="Please upload your resume first")
    
    # Check cache
    cache_key = f"{current_user.id}_{job_id}_{tone}"
    cached = await db.message_cache.find_one({"cache_key": cache_key})
    
    if cached:
        logger.info(f"Returning cached message for {cache_key}")
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
        
        # Cache result
        await db.message_cache.insert_one({
            "cache_key": cache_key,
            "user_id": current_user.id,
            "job_id": job_id,
            "tone": tone,
            "result": result,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Deduct credits
        await db.users.update_one(
            {"id": current_user.id},
            {"$inc": {"ai_credits": -credits_needed}}
        )
        
        return result
    
    except Exception as e:
        logging.error(f"Message recruiter error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate message")


# ========== TRACK EXTERNAL APPLICATIONS ==========

@api_router.post("/tracking/external-apply")
async def track_external_apply(
    job_id: str,
    source: str,
    current_user: User = Depends(get_current_user)
):
    """Track when user clicks 'Apply on Source' for aggregated jobs"""
    
    try:
        await db.external_applications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "job_id": job_id,
            "source": source,
            "clicked_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {"message": "Tracked"}
    
    except Exception as e:
        logging.error(f"Tracking error: {str(e)}")
        # Don't fail the request if tracking fails
        return {"message": "OK"}


# ========== ADMIN ANALYTICS EXTENSION ==========

@api_router.get("/admin/analytics/extended")
async def get_extended_analytics(current_admin: User = Depends(get_current_admin)):
    """Extended analytics including aggregation and premium features"""
    
    # Base analytics (existing)
    base = await get_admin_analytics(current_admin)
    
    # Aggregated jobs stats
    total_aggregated = await db.aggregated_jobs.count_documents({"is_external": True})
    aggregated_by_source = await db.aggregated_jobs.aggregate([
        {"$match": {"is_external": True}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]).to_list(10)
    
    # External apply clicks
    external_clicks = await db.external_applications.count_documents({})
    
    # Premium feature usage
    boost_usage = await db.boost_cache.count_documents({})
    message_usage = await db.message_cache.count_documents({})
    
    # Credits consumed by feature
    # This is approximate - actual tracking would need more detailed logs
    
    extended = {
        **base,
        "aggregated_jobs": {
            "total": total_aggregated,
            "by_source": {item['_id']: item['count'] for item in aggregated_by_source}
        },
        "external_applications": {
            "total_clicks": external_clicks
        },
        "premium_features": {
            "boost_applications": boost_usage,
            "recruiter_messages": message_usage
        }
    }
    
    return extended
