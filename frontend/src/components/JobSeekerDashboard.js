import React, { useState, useEffect } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Briefcase, Search, LogOut, Sparkles, FileText, Loader2, MapPin, DollarSign, Briefcase as BriefcaseIcon, Wand2, Mail } from "lucide-react";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const JobSeekerDashboard = () => {
  const { user, logout, token, fetchUser } = useAuth();
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [matchedJobs, setMatchedJobs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [resumeText, setResumeText] = useState("");
  const [resumeFile, setResumeFile] = useState(null);
  const [uploadMethod, setUploadMethod] = useState("file"); // "file" or "text"
  const [parsedResume, setParsedResume] = useState(null);
  const [showResumeDialog, setShowResumeDialog] = useState(false);
  const [showJobDialog, setShowJobDialog] = useState(false);
  const [showTailorDialog, setShowTailorDialog] = useState(false);
  const [showMessageDialog, setShowMessageDialog] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [isParsingResume, setIsParsingResume] = useState(false);
  const [isMatchingJobs, setIsMatchingJobs] = useState(false);
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchJobs();
    fetchApplications();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats/jobseeker`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setStats(response.data);
    } catch (error) {
      toast.error("Failed to load stats");
    }
  };

  const fetchJobs = async () => {
    try {
      const response = await axios.get(`${API}/jobs?status=active&limit=20`);
      setJobs(response.data);
    } catch (error) {
      toast.error("Failed to load jobs");
    }
  };

  const fetchApplications = async () => {
    try {
      const response = await axios.get(`${API}/applications/my-applications`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setApplications(response.data);
    } catch (error) {
      toast.error("Failed to load applications");
    }
  };

  const handleFileUpload = async () => {
    if (!resumeFile) {
      toast.error("Please select a file");
      return;
    }

    if (user.ai_credits <= 0) {
      setShowUpgradeDialog(true);
      return;
    }

    setIsParsingResume(true);
    try {
      const formData = new FormData();
      formData.append("file", resumeFile);

      const response = await axios.post(`${API}/resumes/upload`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data",
        },
      });

      setParsedResume(response.data);
      toast.success("Resume uploaded and parsed successfully!");
      setShowResumeDialog(false);
      fetchUser();
      fetchStats();
      setResumeFile(null);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || "Failed to upload resume";
      console.error("Resume upload error:", error.response?.data);
      toast.error(errorMsg);
    } finally {
      setIsParsingResume(false);
    }
  };

  const handleTextParse = async () => {
    if (!resumeText || resumeText.trim().length < 100) {
      toast.error("Please paste at least 100 characters of resume text");
      return;
    }

    if (user.ai_credits <= 0) {
      setShowUpgradeDialog(true);
      return;
    }

    setIsParsingResume(true);
    try {
      // Create a text file from the pasted content
      const blob = new Blob([resumeText], { type: "text/plain" });
      const file = new File([blob], "pasted-resume.txt", { type: "text/plain" });

      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(`${API}/resumes/upload`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data",
        },
      });

      setParsedResume(response.data);
      toast.success("Resume parsed successfully!");
      setShowResumeDialog(false);
      fetchUser();
      fetchStats();
      setResumeText("");
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || "Failed to parse resume";
      console.error("Resume parse error:", error.response?.data);
      toast.error(errorMsg);
    } finally {
      setIsParsingResume(false);
    }
  };

  const handleMatchJobs = async () => {
    if (user.ai_credits <= 0) {
      setShowUpgradeDialog(true);
      return;
    }

    if (!stats?.has_resume) {
      toast.error("Please upload your resume first");
      setShowResumeDialog(true);
      return;
    }

    // Check if we already have matched jobs (cache to prevent duplicate API calls)
    if (matchedJobs.length > 0 && !window.confirm("You already have matched jobs. Re-match to update results? This will use 1 AI credit.")) {
      return;
    }

    setIsMatchingJobs(true);
    try {
      const response = await axios.get(`${API}/ai/match-jobs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setMatchedJobs(response.data);
      toast.success(`Found ${response.data.length} matching jobs!`);
      fetchUser();
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || "Failed to match jobs";
      console.error("Match jobs error:", error.response?.data);
      toast.error(errorMsg);
    } finally {
      setIsMatchingJobs(false);
    }
  };

  const handleApply = async (jobId, coverLetter) => {
    try {
      await axios.post(`${API}/applications`, 
        { job_id: jobId, cover_letter: coverLetter },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success("Application submitted successfully!");
      setShowJobDialog(false);
      fetchApplications();
      fetchStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to apply");
    }
  };

  const handleUpgrade = async (tier) => {
    try {
      await axios.post(`${API}/users/upgrade`, null, {
        params: { tier },
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success(`Upgraded to ${tier} tier!`);
      setShowUpgradeDialog(false);
      fetchUser();
      fetchStats();
    } catch (error) {
      toast.error("Upgrade failed");
    }
  };

  return (
    <div data-testid="jobseeker-dashboard" className="min-h-screen bg-[#F8F9FA]">
      {/* Navigation */}
      <nav data-testid="jobseeker-nav" className="bg-white border-b border-[#E2E8F0]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Briefcase className="h-6 w-6 text-[#0F172A]" />
              <span className="text-lg font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>JobQuick AI</span>
            </div>
            <div className="flex items-center gap-4">
              <Badge data-testid="credits-badge" className="bg-gradient-to-r from-indigo-500 to-violet-500 text-white">
                <Sparkles className="h-3 w-3 mr-1" />
                {user?.ai_credits} Credits
              </Badge>
              <Button data-testid="logout-btn" variant="ghost" onClick={logout} size="sm">
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 data-testid="dashboard-title" className="text-3xl font-bold text-[#0F172A] mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Job Seeker Dashboard
          </h1>
          <p className="text-[#64748B]">Welcome back, {user?.full_name}</p>
        </div>

        {/* Quick Actions */}
        <div data-testid="quick-actions" className="grid md:grid-cols-3 gap-6 mb-8">
          <Card className="border-[#E2E8F0] hover:border-[#3B82F6] transition-colors cursor-pointer" onClick={() => setShowResumeDialog(true)}>
            <CardHeader>
              <FileText className="h-10 w-10 text-[#2563EB] mb-2" />
              <CardTitle className="text-lg">Upload Resume</CardTitle>
              <CardDescription>Let AI parse your skills and experience</CardDescription>
            </CardHeader>
          </Card>

          <Card className="border-[#E2E8F0] hover:border-[#3B82F6] transition-colors cursor-pointer" onClick={handleMatchJobs}>
            <CardHeader>
              <Sparkles className="h-10 w-10 text-[#8B5CF6] mb-2" />
              <CardTitle className="text-lg">AI Job Matching</CardTitle>
              <CardDescription>Find jobs that match your profile</CardDescription>
            </CardHeader>
          </Card>

          <Card className="border-[#E2E8F0] hover:border-[#3B82F6] transition-colors">
            <CardHeader>
              <Search className="h-10 w-10 text-[#10B981] mb-2" />
              <CardTitle className="text-lg">Browse Jobs</CardTitle>
              <CardDescription>{jobs.length} active opportunities</CardDescription>
            </CardHeader>
          </Card>
        </div>

        {/* AI Career Tools */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="h-6 w-6 text-[#8B5CF6]" />
            <h2 className="text-2xl font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>AI Career Tools</h2>
            {user.is_premium && <Badge className="bg-gradient-to-r from-indigo-500 to-violet-500 text-white">Premium</Badge>}
          </div>
          
          <div data-testid="ai-career-tools" className="grid md:grid-cols-2 gap-6">
            <Card 
              className="border-[#8B5CF6] hover:border-[#6D28D9] transition-colors cursor-pointer bg-gradient-to-br from-indigo-50 to-violet-50"
              onClick={() => setShowTailorDialog(true)}
            >
              <CardHeader>
                <div className="flex items-center justify-between">
                  <Wand2 className="h-10 w-10 text-[#8B5CF6] mb-2" />
                  <Badge className="bg-[#8B5CF6] text-white">15-25 Credits</Badge>
                </div>
                <CardTitle className="text-lg">Tailor My CV for a Job</CardTitle>
                <CardDescription>Optimize your CV to match a specific job posting. AI rewrites your experience to highlight relevant skills.</CardDescription>
              </CardHeader>
            </Card>

            <Card 
              className="border-[#3B82F6] hover:border-[#2563EB] transition-colors cursor-pointer bg-gradient-to-br from-blue-50 to-cyan-50"
              onClick={() => setShowMessageDialog(true)}
            >
              <CardHeader>
                <div className="flex items-center justify-between">
                  <Mail className="h-10 w-10 text-[#3B82F6] mb-2" />
                  <Badge className="bg-[#3B82F6] text-white">5 Credits</Badge>
                </div>
                <CardTitle className="text-lg">Message Recruiter (AI)</CardTitle>
                <CardDescription>Generate personalized outreach messages for LinkedIn, email, and follow-ups.</CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>

        {/* Stats */}
        <div data-testid="stats-grid" className="grid md:grid-cols-3 gap-6 mb-8">
          <Card className="border-[#E2E8F0]">
            <CardHeader className="pb-2">
              <CardDescription>Applications</CardDescription>
              <CardTitle className="text-3xl">{stats?.total_applications || 0}</CardTitle>
            </CardHeader>
          </Card>
          <Card className="border-[#E2E8F0]">
            <CardHeader className="pb-2">
              <CardDescription>Resume Status</CardDescription>
              <CardTitle className="text-lg">{stats?.has_resume ? "✓ Uploaded" : "Not uploaded"}</CardTitle>
            </CardHeader>
          </Card>
          <Card className="border-[#E2E8F0] bg-gradient-to-br from-indigo-50 to-violet-50">
            <CardHeader className="pb-2">
              <CardDescription>AI Credits</CardDescription>
              <CardTitle className="text-3xl">{stats?.ai_credits || 0}</CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Main Content */}
        <Tabs defaultValue="matched" className="space-y-6">
          <TabsList data-testid="tabs-list">
            <TabsTrigger data-testid="tab-matched" value="matched">AI Matched Jobs</TabsTrigger>
            <TabsTrigger data-testid="tab-all-jobs" value="all-jobs">All Jobs</TabsTrigger>
            <TabsTrigger data-testid="tab-applications" value="applications">My Applications</TabsTrigger>
            <TabsTrigger data-testid="tab-settings" value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="matched" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>AI Matched Jobs</h2>
              <Button data-testid="match-jobs-btn" onClick={handleMatchJobs} disabled={isMatchingJobs} className="btn-ai">
                {isMatchingJobs ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                {isMatchingJobs ? "Matching..." : "Find Matches"}
              </Button>
            </div>

            <div data-testid="matched-jobs-list" className="grid gap-4">
              {matchedJobs.length === 0 ? (
                <Card className="border-[#E2E8F0] p-12 text-center">
                  <Sparkles className="h-12 w-12 text-[#8B5CF6] mx-auto mb-4" />
                  <p className="text-[#64748B] mb-4">Click "Find Matches" to discover jobs that match your profile</p>
                </Card>
              ) : (
                matchedJobs.map((match) => (
                  <Card key={match.job.id} data-testid={`matched-job-${match.job.id}`} className="border-[#E2E8F0] hover:border-[#3B82F6] transition-colors cursor-pointer" onClick={() => { setSelectedJob(match.job); setShowJobDialog(true); }}>
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <CardTitle className="text-xl">{match.job.title}</CardTitle>
                            <Badge className="bg-gradient-to-r from-indigo-500 to-violet-500 text-white">
                              {Math.round(match.match_score)}% Match
                            </Badge>
                          </div>
                          <CardDescription className="mb-2">{match.job.company_name || match.job.employer_name}</CardDescription>
                          <p className="text-sm text-[#64748B] mb-3">{match.match_reason}</p>
                          <div className="flex flex-wrap gap-2 text-sm text-[#64748B]">
                            <span className="flex items-center gap-1">
                              <MapPin className="h-4 w-4" />
                              {match.job.location}
                            </span>
                            <span className="flex items-center gap-1">
                              <BriefcaseIcon className="h-4 w-4" />
                              {match.job.job_type}
                            </span>
                            {match.job.salary_range && (
                              <span className="flex items-center gap-1">
                                <DollarSign className="h-4 w-4" />
                                {match.job.salary_range}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          <TabsContent value="all-jobs" className="space-y-6">
            <h2 className="text-2xl font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>All Jobs</h2>
            <div data-testid="all-jobs-list" className="grid gap-4">
              {jobs.map((job) => (
                <Card key={job.id} data-testid={`job-card-${job.id}`} className="border-[#E2E8F0] hover:border-[#3B82F6] transition-colors cursor-pointer" onClick={() => { setSelectedJob(job); setShowJobDialog(true); }}>
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-xl">{job.title}</CardTitle>
                        <CardDescription className="mt-2">{job.company_name || job.employer_name}</CardDescription>
                        <div className="flex flex-wrap gap-2 mt-3 text-sm text-[#64748B]">
                          <span className="flex items-center gap-1">
                            <MapPin className="h-4 w-4" />
                            {job.location}
                          </span>
                          <span className="flex items-center gap-1">
                            <BriefcaseIcon className="h-4 w-4" />
                            {job.job_type}
                          </span>
                          {job.salary_range && (
                            <span className="flex items-center gap-1">
                              <DollarSign className="h-4 w-4" />
                              {job.salary_range}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="applications" className="space-y-6">
            <h2 className="text-2xl font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>My Applications</h2>
            <div data-testid="applications-list" className="grid gap-4">
              {applications.length === 0 ? (
                <Card className="border-[#E2E8F0] p-12 text-center">
                  <p className="text-[#64748B]">No applications yet. Start applying to jobs!</p>
                </Card>
              ) : (
                applications.map((app) => (
                  <Card key={app.id} data-testid={`application-${app.id}`} className="border-[#E2E8F0]">
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle className="text-lg">{app.job_id}</CardTitle>
                          <CardDescription className="mt-2">
                            Applied on {new Date(app.created_at).toLocaleDateString()}
                          </CardDescription>
                        </div>
                        <Badge className={
                          app.status === 'pending' ? 'bg-[#F59E0B]' :
                          app.status === 'reviewed' ? 'bg-[#3B82F6]' :
                          app.status === 'accepted' ? 'bg-[#10B981]' :
                          'bg-[#64748B]'
                        }>
                          {app.status}
                        </Badge>
                      </div>
                    </CardHeader>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          <TabsContent value="settings">
            <Card className="border-[#E2E8F0]">
              <CardHeader>
                <CardTitle>Subscription & Credits</CardTitle>
                <CardDescription>Current Plan: <strong>{user?.subscription_tier}</strong></CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span>AI Credits Remaining</span>
                  <Badge className="bg-gradient-to-r from-indigo-500 to-violet-500 text-white">{user?.ai_credits}</Badge>
                </div>
                <Button data-testid="upgrade-btn" onClick={() => setShowUpgradeDialog(true)} className="w-full bg-[#2563EB] hover:bg-[#1D4ED8]">
                  Upgrade Plan
                </Button>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Resume Upload Dialog */}
      <Dialog open={showResumeDialog} onOpenChange={(open) => {
        setShowResumeDialog(open);
        if (!open) {
          setResumeFile(null);
          setResumeText("");
          setParsedResume(null);
        }
      }}>
        <DialogContent data-testid="resume-dialog" className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-2xl" style={{ fontFamily: 'Manrope, sans-serif' }}>Upload Your Resume</DialogTitle>
            <DialogDescription>Upload a PDF/DOCX file or paste your resume text. AI will extract your skills and experience.</DialogDescription>
          </DialogHeader>

          <Tabs value={uploadMethod} onValueChange={setUploadMethod} className="mt-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="file">Upload File</TabsTrigger>
              <TabsTrigger value="text">Paste Text</TabsTrigger>
            </TabsList>

            <TabsContent value="file" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Select Resume File</Label>
                <Input
                  data-testid="resume-file-input"
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => setResumeFile(e.target.files[0])}
                  disabled={isParsingResume}
                  className="cursor-pointer"
                />
                <p className="text-xs text-[#64748B]">Supported formats: PDF, DOCX, TXT (Max 5MB)</p>
              </div>

              {resumeFile && (
                <div className="p-3 bg-[#F1F5F9] rounded-md">
                  <p className="text-sm font-medium">{resumeFile.name}</p>
                  <p className="text-xs text-[#64748B]">{(resumeFile.size / 1024).toFixed(1)} KB</p>
                </div>
              )}

              <Button
                data-testid="upload-resume-btn"
                onClick={handleFileUpload}
                disabled={isParsingResume || !resumeFile}
                className="w-full btn-ai"
              >
                {isParsingResume ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                {isParsingResume ? "Uploading & Parsing..." : "Upload & Parse with AI"}
              </Button>
            </TabsContent>

            <TabsContent value="text" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Resume Text</Label>
                <Textarea
                  data-testid="resume-textarea"
                  value={resumeText}
                  onChange={(e) => setResumeText(e.target.value)}
                  placeholder="Paste your resume text here (minimum 100 characters)..."
                  rows={12}
                  disabled={isParsingResume}
                  className="font-mono text-sm"
                />
                <p className="text-xs text-[#64748B]">
                  {resumeText.length} characters
                  {resumeText.length < 100 && ` (${100 - resumeText.length} more needed)`}
                </p>
              </div>

              <Button
                data-testid="parse-resume-btn"
                onClick={handleTextParse}
                disabled={isParsingResume || !resumeText || resumeText.trim().length < 100}
                className="w-full btn-ai"
              >
                {isParsingResume ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                {isParsingResume ? "Parsing..." : "Parse with AI"}
              </Button>
            </TabsContent>
          </Tabs>

          {parsedResume && (
            <Card className="bg-[#F1F5F9] border-[#E2E8F0] mt-4">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Parsed Results</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div>
                  <strong>Skills:</strong> {parsedResume.skills?.join(", ") || "None detected"}
                </div>
                <div>
                  <strong>Experience:</strong> {parsedResume.experience_years || 0} years
                </div>
                <div>
                  <strong>Education:</strong> {parsedResume.education || "Not specified"}
                </div>
              </CardContent>
            </Card>
          )}
        </DialogContent>
      </Dialog>

      {/* Job Details Dialog */}
      <Dialog open={showJobDialog} onOpenChange={setShowJobDialog}>
        <DialogContent data-testid="job-details-dialog" className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selectedJob && (
            <>
              <DialogHeader>
                <DialogTitle className="text-2xl" style={{ fontFamily: 'Manrope, sans-serif' }}>{selectedJob.title}</DialogTitle>
                <DialogDescription>{selectedJob.company_name || selectedJob.employer_name}</DialogDescription>
              </DialogHeader>
              <div className="space-y-6 mt-4">
                <div className="flex flex-wrap gap-2">
                  <Badge>{selectedJob.job_type}</Badge>
                  <Badge>{selectedJob.experience_level}</Badge>
                  <Badge variant="outline">{selectedJob.location}</Badge>
                  {selectedJob.salary_range && <Badge variant="outline">{selectedJob.salary_range}</Badge>}
                </div>
                
                <div>
                  <h3 className="font-semibold mb-2">Description</h3>
                  <p className="text-[#64748B]">{selectedJob.description}</p>
                </div>
                
                <div>
                  <h3 className="font-semibold mb-2">Requirements</h3>
                  <ul className="list-disc list-inside text-[#64748B] space-y-1">
                    {selectedJob.requirements.map((req, idx) => (
                      <li key={idx}>{req}</li>
                    ))}
                  </ul>
                </div>
                
                <ApplyForm jobId={selectedJob.id} onSubmit={handleApply} />
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Upgrade Dialog */}
      <Dialog open={showUpgradeDialog} onOpenChange={setShowUpgradeDialog}>
        <DialogContent data-testid="upgrade-dialog">
          <DialogHeader>
            <DialogTitle>Upgrade Your Plan</DialogTitle>
            <DialogDescription>Get more AI credits to unlock advanced features</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <Button data-testid="upgrade-professional-btn" onClick={() => handleUpgrade('professional')} className="w-full bg-[#2563EB]" size="lg">
              Professional - $49/month (100 credits)
            </Button>
            <Button data-testid="upgrade-enterprise-btn" onClick={() => handleUpgrade('enterprise')} className="w-full bg-[#0F172A]" size="lg">
              Enterprise - $199/month (500 credits)
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const ApplyForm = ({ jobId, onSubmit }) => {
  const [coverLetter, setCoverLetter] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(jobId, coverLetter);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label>Cover Letter (Optional)</Label>
        <Textarea
          data-testid="cover-letter-input"
          value={coverLetter}
          onChange={(e) => setCoverLetter(e.target.value)}
          placeholder="Why are you interested in this position?"
          rows={4}
        />
      </div>
      <Button data-testid="submit-application-btn" type="submit" className="w-full bg-[#0F172A] hover:bg-[#1E293B]">
        Submit Application
      </Button>
    </form>
  );
};

export default JobSeekerDashboard;
