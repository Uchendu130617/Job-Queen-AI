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

    async def tailor_resume(self, resume_data: Dict[str, Any], job_data: Dict[str, Any], include_cover_letter: bool = False) -> Dict[str, Any]:
        """Tailor resume for specific job (Boost My Application feature)"""
        try:
            chat = await self._create_chat(
                f"tailor_{uuid.uuid4()}",
                "You are an expert career coach. Tailor resumes to match job requirements WITHOUT fabricating experience."
            )
            
            prompt = f"""Tailor this resume for the job:

Job Title: {job_data.get('title', job_data.get('job_title', ''))}
Company: {job_data.get('company_name', '')}
Requirements: {', '.join(job_data.get('requirements', job_data.get('skills_keywords', [])))}
Description: {job_data.get('description', job_data.get('short_description', ''))[:300]}

Current Resume:
Skills: {', '.join(resume_data.get('parsed_skills', []))}
Experience: {resume_data.get('experience_years', 0)} years
Education: {resume_data.get('education', '')}
Summary: {resume_data.get('summary', '')}

RULES:
1. DO NOT fabricate experience or skills
2. Reframe existing content to highlight relevant experience
3. Use keywords from job description
4. Keep it professional and honest

Provide as JSON:
{{
  "tailored_summary": "Professional summary highlighting relevant experience",
  "experience_bullets": ["Reframed achievement 1", "Reframed achievement 2"],
  "optimized_skills": ["skill1", "skill2"],
  "estimated_match_improvement": 15
}}"""
            
            message = UserMessage(text=prompt)
            response = await chat.send_message(message)
            
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            
            tailored = json.loads(response.strip())
            
            # Add cover letter if requested
            if include_cover_letter:
                cover_letter = await self._generate_cover_letter(resume_data, job_data)
                tailored['cover_letter'] = cover_letter
            
            return tailored
        
        except Exception as e:
            logger.error(f"Resume tailoring error: {str(e)}")
            raise
    
    async def _generate_cover_letter(self, resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> str:
        """Generate tailored cover letter"""
        try:
            chat = await self._create_chat(
                f"cover_{uuid.uuid4()}",
                "You are an expert career coach. Write compelling cover letters."
            )
            
            prompt = f"""Write a professional cover letter for:

Job: {job_data.get('title', job_data.get('job_title', ''))}
Company: {job_data.get('company_name', '')}

Candidate Profile:
Skills: {', '.join(resume_data.get('parsed_skills', [])[:5])}
Experience: {resume_data.get('experience_years', 0)} years
Summary: {resume_data.get('summary', '')}

Keep it:
- 3 paragraphs max
- Professional but personable
- Highlight 2-3 key qualifications
- Express genuine interest

Return only the cover letter text, no JSON.
"""
            
            message = UserMessage(text=prompt)
            response = await chat.send_message(message)
            
            return response.strip()
        
        except Exception as e:
            logger.error(f"Cover letter error: {str(e)}")
            return "Error generating cover letter"
    
    async def generate_recruiter_message(
        self,
        resume_data: Dict[str, Any],
        job_data: Dict[str, Any],
        tone: str = "professional"
    ) -> Dict[str, Any]:
        """Generate recruiter outreach messages (Message Recruiter feature)"""
        try:
            tone_guidance = {
                "professional": "formal, respectful, highlighting qualifications",
                "friendly": "warm, approachable, showing personality",
                "confident": "assertive, achievement-focused, direct"
            }
            
            chat = await self._create_chat(
                f"message_{uuid.uuid4()}",
                f"You are an expert career coach. Write {tone} outreach messages to recruiters."
            )
            
            prompt = f"""Generate 3 recruiter outreach messages ({tone} tone):

Job: {job_data.get('title', job_data.get('job_title', ''))}
Company: {job_data.get('company_name', '')}

Candidate:
Skills: {', '.join(resume_data.get('parsed_skills', [])[:5])}
Experience: {resume_data.get('experience_years', 0)} years

Generate:
1. LinkedIn DM (150 chars max)
2. Email subject + body (concise, 200 words max)
3. Follow-up message (100 chars max)

Tone: {tone_guidance.get(tone, 'professional')}

Respond as JSON:
{{
  "linkedin_dm": "...",
  "email_subject": "...",
  "email_body": "...",
  "follow_up": "..."
}}
"""
            
            message = UserMessage(text=prompt)
            response = await chat.send_message(message)
            
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            
            messages = json.loads(response.strip())
            
            return messages
        
        except Exception as e:
            logger.error(f"Recruiter message error: {str(e)}")
            raise
