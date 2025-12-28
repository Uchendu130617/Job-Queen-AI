from emergentintegrations.llm.chat import LlmChat, UserMessage
import json
import uuid
import os
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class AIProvider:
    OPENAI = "openai"
    CLAUDE = "anthropic"
    GEMINI = "gemini"


class AIService:
    """Abstracted AI service supporting multiple providers"""
    
    def __init__(self, api_key: str, provider: str = AIProvider.OPENAI, model: str = None):
        self.api_key = api_key
        self.provider = provider
        self.model = model or self._get_default_model(provider)
        
    def _get_default_model(self, provider: str) -> str:
        """Get default model for provider"""
        defaults = {
            AIProvider.OPENAI: "gpt-5.2",
            AIProvider.CLAUDE: "claude-sonnet-4-5-20250929",
            AIProvider.GEMINI: "gemini-3-flash-preview"
        }
        return defaults.get(provider, "gpt-5.2")
    
    async def _create_chat(self, session_id: str, system_message: str) -> LlmChat:
        """Create configured chat instance"""
        chat = LlmChat(
            api_key=self.api_key,
            session_id=session_id,
            system_message=system_message
        ).with_model(self.provider, self.model)
        return chat
    
    async def parse_resume(self, resume_text: str, user_id: str) -> Dict[str, Any]:
        """Parse resume and extract structured data"""
        try:
            chat = await self._create_chat(
                f"parse_{user_id}_{uuid.uuid4()}",
                "You are an expert resume parser. Extract key information accurately."
            )
            
            prompt = f"""Parse this resume and extract:
1. List of skills (as JSON array)
2. Years of experience (as integer)
3. Education level
4. Brief professional summary (2-3 sentences)
5. Key achievements (list)

Resume text:
{resume_text}

Respond ONLY with valid JSON in this exact format:
{{
  "skills": ["skill1", "skill2"],
  "experience_years": 5,
  "education": "Bachelor's in Computer Science",
  "summary": "Professional summary here",
  "achievements": ["achievement1", "achievement2"]
}}"""
            
            message = UserMessage(text=prompt)
            response = await chat.send_message(message)
            
            # Clean response if needed
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            
            parsed_data = json.loads(response.strip())
            return parsed_data
        except Exception as e:
            logger.error(f"Resume parsing error: {str(e)}")
            raise
    
    async def match_jobs(self, resume_data: Dict[str, Any], jobs: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
        """Match candidate with jobs and provide detailed breakdown"""
        try:
            chat = await self._create_chat(
                f"match_{user_id}_{uuid.uuid4()}",
                "You are an expert job matching AI. Provide detailed, objective assessments."
            )
            
            jobs_summary = "\n".join([
                f"{i+1}. {job['title']} - {job.get('description', '')[:200]} | Requirements: {', '.join(job.get('requirements', [])[:3])}"
                for i, job in enumerate(jobs)
            ])
            
            prompt = f"""Candidate Profile:
Skills: {', '.join(resume_data.get('parsed_skills', []))}
Experience: {resume_data.get('experience_years', 0)} years
Education: {resume_data.get('education', 'Not specified')}

Available Jobs:
{jobs_summary}

For each job, provide:
1. Overall match score (0-100)
2. Skills match score (0-100)
3. Experience match score (0-100)
4. Location/remote fit (0-100)
5. Brief reason

Respond ONLY with valid JSON array:
[
  {{
    "job_index": 0,
    "overall_score": 85,
    "skills_score": 90,
    "experience_score": 80,
    "location_score": 85,
    "reason": "Strong technical match with relevant experience"
  }}
]"""
            
            message = UserMessage(text=prompt)
            response = await chat.send_message(message)
            
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            
            matches = json.loads(response.strip())
            return matches
        except Exception as e:
            logger.error(f"Job matching error: {str(e)}")
            raise
    
    async def screen_candidate(self, job_data: Dict[str, Any], resume_data: Dict[str, Any], app_id: str) -> Dict[str, Any]:
        """Screen candidate with detailed breakdown"""
        try:
            chat = await self._create_chat(
                f"screen_{app_id}_{uuid.uuid4()}",
                "You are an expert recruitment screener. Evaluate candidates objectively and fairly."
            )
            
            prompt = f"""Job Requirements:
Title: {job_data['title']}
Requirements: {', '.join(job_data.get('requirements', []))}
Experience Level: {job_data.get('experience_level', 'Not specified')}

Candidate Profile:
Skills: {', '.join(resume_data.get('parsed_skills', []))}
Experience: {resume_data.get('experience_years', 0)} years
Education: {resume_data.get('education', 'Not specified')}

Provide detailed screening as JSON:
{{
  "overall_score": 75,
  "skills_match": 80,
  "experience_match": 70,
  "education_match": 75,
  "strengths": ["strength1", "strength2"],
  "concerns": ["concern1"],
  "recommendation": "Recommend for interview / Not recommended / Needs more info",
  "detailed_analysis": "Brief explanation of the assessment"
}}"""
            
            message = UserMessage(text=prompt)
            response = await chat.send_message(message)
            
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            
            screening = json.loads(response.strip())
            return screening
        except Exception as e:
            logger.error(f"Screening error: {str(e)}")
            raise
    
    async def optimize_resume(self, resume_text: str, target_job: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Provide resume optimization suggestions (Premium feature)"""
        try:
            chat = await self._create_chat(
                f"optimize_{uuid.uuid4()}",
                "You are an expert career coach specializing in resume optimization."
            )
            
            job_context = ""
            if target_job:
                job_context = f"\n\nTarget Job: {target_job.get('title', '')}\nRequirements: {', '.join(target_job.get('requirements', []))}"
            
            prompt = f"""Analyze this resume and provide optimization suggestions:{job_context}

Resume:
{resume_text}

Provide suggestions as JSON:
{{
  "missing_keywords": ["keyword1", "keyword2"],
  "improvements": [
    {{"section": "Experience", "suggestion": "Add quantifiable achievements"}}
  ],
  "ats_score": 75,
  "overall_feedback": "Brief summary of main improvements needed"
}}"""
            
            message = UserMessage(text=prompt)
            response = await chat.send_message(message)
            
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            
            optimization = json.loads(response.strip())
            return optimization
        except Exception as e:
            logger.error(f"Optimization error: {str(e)}")
            raise
    
    async def generate_interview_prep(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate interview preparation questions (Premium feature)"""
        try:
            chat = await self._create_chat(
                f"interview_{uuid.uuid4()}",
                "You are an expert interview coach."
            )
            
            prompt = f"""Generate interview preparation for this job:

Job: {job_data['title']}
Requirements: {', '.join(job_data.get('requirements', []))}
Description: {job_data.get('description', '')[:300]}

Provide as JSON:
{{
  "technical_questions": ["question1", "question2"],
  "behavioral_questions": ["question1", "question2"],
  "tips": ["tip1", "tip2"],
  "key_talking_points": ["point1", "point2"]
}}"""
            
            message = UserMessage(text=prompt)
            response = await chat.send_message(message)
            
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            
            prep = json.loads(response.strip())
            return prep
        except Exception as e:
            logger.error(f"Interview prep error: {str(e)}")
            raise
