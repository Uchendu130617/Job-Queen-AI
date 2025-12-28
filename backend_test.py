import requests
import sys
import json
from datetime import datetime

class JobQuickAPITester:
    def __init__(self, base_url="https://jobquick-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.employer_token = None
        self.jobseeker_token = None
        self.employer_user = None
        self.jobseeker_user = None
        self.test_job_id = None
        self.test_application_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
            self.failed_tests.append({"test": name, "error": details})

    def make_request(self, method, endpoint, data=None, token=None, params=None):
        """Make HTTP request with error handling"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            
            return response
        except Exception as e:
            return None

    def test_user_registration(self):
        """Test user registration for both roles"""
        timestamp = datetime.now().strftime('%H%M%S')
        
        # Test employer registration
        employer_data = {
            "email": f"employer_{timestamp}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Employer",
            "company_name": "Test Company",
            "role": "employer"
        }
        
        response = self.make_request('POST', 'auth/register', employer_data)
        if response and response.status_code == 200:
            data = response.json()
            self.employer_token = data['access_token']
            self.employer_user = data['user']
            self.log_test("Employer Registration", True)
        else:
            self.log_test("Employer Registration", False, f"Status: {response.status_code if response else 'No response'}")

        # Test job seeker registration
        jobseeker_data = {
            "email": f"jobseeker_{timestamp}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Job Seeker",
            "role": "job_seeker"
        }
        
        response = self.make_request('POST', 'auth/register', jobseeker_data)
        if response and response.status_code == 200:
            data = response.json()
            self.jobseeker_token = data['access_token']
            self.jobseeker_user = data['user']
            self.log_test("Job Seeker Registration", True)
        else:
            self.log_test("Job Seeker Registration", False, f"Status: {response.status_code if response else 'No response'}")

    def test_user_login(self):
        """Test user login"""
        if not self.employer_user:
            self.log_test("Employer Login", False, "No employer user to test")
            return

        login_data = {
            "email": self.employer_user['email'],
            "password": "TestPass123!"
        }
        
        response = self.make_request('POST', 'auth/login', login_data)
        success = response and response.status_code == 200
        self.log_test("User Login", success, f"Status: {response.status_code if response else 'No response'}")

    def test_get_user_profile(self):
        """Test getting user profile"""
        if not self.employer_token:
            self.log_test("Get User Profile", False, "No token available")
            return

        response = self.make_request('GET', 'users/me', token=self.employer_token)
        success = response and response.status_code == 200
        self.log_test("Get User Profile", success, f"Status: {response.status_code if response else 'No response'}")

    def test_job_creation(self):
        """Test job creation by employer"""
        if not self.employer_token:
            self.log_test("Job Creation", False, "No employer token")
            return

        job_data = {
            "title": "Senior Software Engineer",
            "description": "We are looking for a senior software engineer with experience in Python and React.",
            "requirements": ["Python", "React", "5+ years experience"],
            "location": "Remote",
            "salary_range": "$100k - $150k",
            "job_type": "full-time",
            "experience_level": "senior"
        }
        
        response = self.make_request('POST', 'jobs', job_data, self.employer_token)
        if response and response.status_code == 200:
            self.test_job_id = response.json()['id']
            self.log_test("Job Creation", True)
        else:
            self.log_test("Job Creation", False, f"Status: {response.status_code if response else 'No response'}")

    def test_get_jobs(self):
        """Test getting all jobs"""
        response = self.make_request('GET', 'jobs')
        success = response and response.status_code == 200
        self.log_test("Get All Jobs", success, f"Status: {response.status_code if response else 'No response'}")

    def test_get_employer_jobs(self):
        """Test getting employer's jobs"""
        if not self.employer_token:
            self.log_test("Get Employer Jobs", False, "No employer token")
            return

        response = self.make_request('GET', 'jobs/employer/my-jobs', token=self.employer_token)
        success = response and response.status_code == 200
        self.log_test("Get Employer Jobs", success, f"Status: {response.status_code if response else 'No response'}")

    def test_job_application(self):
        """Test job application by job seeker"""
        if not self.jobseeker_token or not self.test_job_id:
            self.log_test("Job Application", False, "Missing jobseeker token or job ID")
            return

        app_data = {
            "job_id": self.test_job_id,
            "cover_letter": "I am very interested in this position and believe my skills align well."
        }
        
        response = self.make_request('POST', 'applications', app_data, self.jobseeker_token)
        if response and response.status_code == 200:
            self.test_application_id = response.json()['id']
            self.log_test("Job Application", True)
        else:
            self.log_test("Job Application", False, f"Status: {response.status_code if response else 'No response'}")

    def test_get_applications(self):
        """Test getting applications"""
        if not self.jobseeker_token:
            self.log_test("Get Job Seeker Applications", False, "No jobseeker token")
            return

        response = self.make_request('GET', 'applications/my-applications', token=self.jobseeker_token)
        success = response and response.status_code == 200
        self.log_test("Get Job Seeker Applications", success, f"Status: {response.status_code if response else 'No response'}")

        # Test employer getting applications for their job
        if not self.employer_token or not self.test_job_id:
            self.log_test("Get Job Applications (Employer)", False, "Missing employer token or job ID")
            return

        response = self.make_request('GET', f'applications/job/{self.test_job_id}', token=self.employer_token)
        success = response and response.status_code == 200
        self.log_test("Get Job Applications (Employer)", success, f"Status: {response.status_code if response else 'No response'}")

    def test_ai_resume_parsing(self):
        """Test AI resume parsing"""
        if not self.jobseeker_token:
            self.log_test("AI Resume Parsing", False, "No jobseeker token")
            return

        resume_text = """
        John Doe
        Senior Software Engineer
        
        Experience:
        - 5 years of Python development
        - 3 years of React experience
        - Led team of 5 developers
        
        Education:
        Bachelor's in Computer Science
        
        Skills: Python, React, JavaScript, SQL, Docker
        """
        
        response = self.make_request('POST', 'ai/parse-resume', None, self.jobseeker_token, params={'resume_text': resume_text})
        success = response and response.status_code == 200
        self.log_test("AI Resume Parsing", success, f"Status: {response.status_code if response else 'No response'}")

    def test_ai_job_matching(self):
        """Test AI job matching"""
        if not self.jobseeker_token:
            self.log_test("AI Job Matching", False, "No jobseeker token")
            return

        response = self.make_request('GET', 'ai/match-jobs', token=self.jobseeker_token)
        success = response and response.status_code in [200, 404]  # 404 if no resume uploaded
        self.log_test("AI Job Matching", success, f"Status: {response.status_code if response else 'No response'}")

    def test_ai_candidate_screening(self):
        """Test AI candidate screening"""
        if not self.employer_token or not self.test_application_id:
            self.log_test("AI Candidate Screening", False, "Missing employer token or application ID")
            return

        response = self.make_request('POST', f'ai/screen-candidate/{self.test_application_id}', {}, self.employer_token)
        success = response and response.status_code in [200, 404]  # 404 if no resume found
        self.log_test("AI Candidate Screening", success, f"Status: {response.status_code if response else 'No response'}")

    def test_subscription_upgrade(self):
        """Test subscription upgrade"""
        if not self.employer_token:
            self.log_test("Subscription Upgrade", False, "No employer token")
            return

        response = self.make_request('POST', 'users/upgrade', None, self.employer_token, params={'tier': 'professional'})
        success = response and response.status_code == 200
        self.log_test("Subscription Upgrade", success, f"Status: {response.status_code if response else 'No response'}")

    def test_employer_stats(self):
        """Test employer stats"""
        if not self.employer_token:
            self.log_test("Employer Stats", False, "No employer token")
            return

        response = self.make_request('GET', 'stats/employer', token=self.employer_token)
        success = response and response.status_code == 200
        self.log_test("Employer Stats", success, f"Status: {response.status_code if response else 'No response'}")

    def test_jobseeker_stats(self):
        """Test job seeker stats"""
        if not self.jobseeker_token:
            self.log_test("Job Seeker Stats", False, "No jobseeker token")
            return

        response = self.make_request('GET', 'stats/jobseeker', token=self.jobseeker_token)
        success = response and response.status_code == 200
        self.log_test("Job Seeker Stats", success, f"Status: {response.status_code if response else 'No response'}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting JobQuick AI Backend Tests...")
        print(f"Testing against: {self.base_url}")
        print("=" * 50)

        # Authentication tests
        self.test_user_registration()
        self.test_user_login()
        self.test_get_user_profile()

        # Job management tests
        self.test_job_creation()
        self.test_get_jobs()
        self.test_get_employer_jobs()

        # Application tests
        self.test_job_application()
        self.test_get_applications()

        # AI feature tests
        self.test_ai_resume_parsing()
        self.test_ai_job_matching()
        self.test_ai_candidate_screening()

        # Subscription tests
        self.test_subscription_upgrade()

        # Stats tests
        self.test_employer_stats()
        self.test_jobseeker_stats()

        # Print results
        print("=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"  - {test['test']}: {test['error']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = JobQuickAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())