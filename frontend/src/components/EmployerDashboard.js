import React, { useState, useEffect } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Briefcase, Plus, BarChart, Settings, LogOut, Sparkles, Users, FileText, TrendingUp } from "lucide-react";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const EmployerDashboard = () => {
  const { user, logout, token, fetchUser } = useAuth();
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [showCreateJob, setShowCreateJob] = useState(false);
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchJobs();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats/employer`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setStats(response.data);
    } catch (error) {
      toast.error("Failed to load stats");
    }
  };

  const fetchJobs = async () => {
    try {
      const response = await axios.get(`${API}/jobs/employer/my-jobs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setJobs(response.data);
    } catch (error) {
      toast.error("Failed to load jobs");
    }
  };

  const fetchApplications = async (jobId) => {
    try {
      const response = await axios.get(`${API}/applications/job/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setApplications(response.data);
    } catch (error) {
      toast.error("Failed to load applications");
    }
  };

  const handleScreenCandidate = async (appId) => {
    if (user.ai_credits <= 0) {
      setShowUpgradeDialog(true);
      return;
    }

    try {
      const response = await axios.post(`${API}/ai/screen-candidate/${appId}`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success("Candidate screened successfully");
      fetchApplications(selectedJob);
      fetchUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Screening failed");
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
    <div data-testid="employer-dashboard" className="min-h-screen bg-[#F8F9FA]">
      {/* Navigation */}
      <nav data-testid="employer-nav" className="bg-white border-b border-[#E2E8F0]">
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
            Employer Dashboard
          </h1>
          <p className="text-[#64748B]">Welcome back, {user?.full_name}</p>
        </div>

        {/* Account Pending Approval Banner */}
        {!user?.is_approved && (
          <Card className="border-[#F59E0B] bg-[#FFFBEB] mb-6">
            <CardHeader>
              <CardTitle className="text-[#92400E] flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Account Pending Approval
              </CardTitle>
              <CardDescription className="text-[#92400E]">
                Your employer account is awaiting admin approval. You won't be able to post jobs until your account is approved. This usually takes 1-2 business days.
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {/* Stats */}
        <div data-testid="stats-grid" className="grid md:grid-cols-4 gap-6 mb-8">
          <Card className="border-[#E2E8F0]">
            <CardHeader className="pb-2">
              <CardDescription>Total Jobs</CardDescription>
              <CardTitle className="text-3xl">{stats?.total_jobs || 0}</CardTitle>
            </CardHeader>
          </Card>
          <Card className="border-[#E2E8F0]">
            <CardHeader className="pb-2">
              <CardDescription>Active Jobs</CardDescription>
              <CardTitle className="text-3xl">{stats?.active_jobs || 0}</CardTitle>
            </CardHeader>
          </Card>
          <Card className="border-[#E2E8F0]">
            <CardHeader className="pb-2">
              <CardDescription>Applications</CardDescription>
              <CardTitle className="text-3xl">{stats?.total_applications || 0}</CardTitle>
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
        <Tabs defaultValue="jobs" className="space-y-6">
          <TabsList data-testid="tabs-list">
            <TabsTrigger data-testid="tab-jobs" value="jobs">My Jobs</TabsTrigger>
            <TabsTrigger data-testid="tab-applications" value="applications">Applications</TabsTrigger>
            <TabsTrigger data-testid="tab-settings" value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="jobs" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>Job Postings</h2>
              <Button data-testid="create-job-btn" onClick={() => setShowCreateJob(true)} className="bg-[#0F172A] hover:bg-[#1E293B]">
                <Plus className="h-4 w-4 mr-2" />
                Create Job
              </Button>
            </div>

            {jobs.some(j => j.status === 'pending') && (
              <Card className="border-[#F59E0B] bg-[#FFFBEB]">
                <CardHeader className="pb-3">
                  <p className="text-sm text-[#92400E]">
                    ⏳ Some jobs are pending admin approval. They will become visible to candidates once approved.
                  </p>
                </CardHeader>
              </Card>
            )}

            <div data-testid="jobs-list" className="grid gap-4">
              {jobs.length === 0 ? (
                <Card className="border-[#E2E8F0] p-12 text-center">
                  <p className="text-[#64748B]">No jobs posted yet. Create your first job posting!</p>
                </Card>
              ) : (
                jobs.map((job) => (
                  <Card key={job.id} data-testid={`job-card-${job.id}`} className="border-[#E2E8F0] hover:border-[#3B82F6] transition-colors cursor-pointer" onClick={() => { setSelectedJob(job.id); fetchApplications(job.id); }}>
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle className="text-xl">{job.title}</CardTitle>
                          <CardDescription className="mt-2">{job.location} • {job.job_type}</CardDescription>
                        </div>
                        <Badge className={
                          job.status === 'active' ? 'bg-[#10B981] text-white' : 
                          job.status === 'pending' ? 'bg-[#F59E0B] text-white' :
                          job.status === 'rejected' ? 'bg-[#EF4444] text-white' :
                          'bg-[#64748B] text-white'
                        }>
                          {job.status}
                        </Badge>
                      </div>
                      <div className="mt-4 flex items-center gap-4 text-sm text-[#64748B]">
                        <span className="flex items-center gap-1">
                          <Users className="h-4 w-4" />
                          {job.application_count} applications
                        </span>
                      </div>
                    </CardHeader>
                  </Card>
                ))
              )}</div>
          </TabsContent>

          <TabsContent value="applications" className="space-y-6">
            {!selectedJob ? (
              <Card className="border-[#E2E8F0] p-12 text-center">
                <p className="text-[#64748B]">Select a job to view applications</p>
              </Card>
            ) : (
              <div data-testid="applications-list" className="space-y-4">
                {applications.length === 0 ? (
                  <Card className="border-[#E2E8F0] p-12 text-center">
                    <p className="text-[#64748B]">No applications yet</p>
                  </Card>
                ) : (
                  applications.map((app) => (
                    <Card key={app.id} data-testid={`application-card-${app.id}`} className="border-[#E2E8F0]">
                      <CardHeader>
                        <div className="flex justify-between items-start">
                          <div>
                            <CardTitle className="text-lg">{app.candidate_name}</CardTitle>
                            <CardDescription>{app.candidate_email}</CardDescription>
                          </div>
                          <div className="flex items-center gap-2">
                            {app.ai_match_score && (
                              <Badge className="bg-gradient-to-r from-indigo-500 to-violet-500 text-white">
                                Score: {Math.round(app.ai_match_score)}%
                              </Badge>
                            )}
                            <Badge>{app.status}</Badge>
                          </div>
                        </div>
                        {app.screening_result && (
                          <div className="mt-4 p-4 bg-[#F1F5F9] rounded-md">
                            <p className="font-semibold mb-2">AI Screening Result:</p>
                            <p className="text-sm text-[#64748B] mb-2">{app.screening_result.recommendation}</p>
                            {app.screening_result.strengths && (
                              <div className="text-sm">
                                <strong>Strengths:</strong> {app.screening_result.strengths.join(", ")}
                              </div>
                            )}
                          </div>
                        )}
                        {!app.screening_result && (
                          <Button data-testid={`screen-btn-${app.id}`} onClick={() => handleScreenCandidate(app.id)} className="mt-4 btn-ai" size="sm">
                            <Sparkles className="h-4 w-4 mr-2" />
                            Screen with AI
                          </Button>
                        )}
                      </CardHeader>
                    </Card>
                  ))
                )}
              </div>
            )}
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

      {/* Create Job Dialog */}
      <CreateJobDialog open={showCreateJob} onClose={() => setShowCreateJob(false)} onSuccess={() => { fetchJobs(); fetchStats(); }} token={token} />

      {/* Upgrade Dialog */}
      <Dialog open={showUpgradeDialog} onOpenChange={setShowUpgradeDialog}>
        <DialogContent data-testid="upgrade-dialog">
          <DialogHeader>
            <DialogTitle>Upgrade Your Plan</DialogTitle>
            <DialogDescription>Get more AI credits and unlock premium features</DialogDescription>
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

const CreateJobDialog = ({ open, onClose, onSuccess, token }) => {
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    requirements: "",
    location: "",
    salary_range: "",
    job_type: "full-time",
    experience_level: "mid-level"
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        requirements: formData.requirements.split(",").map(r => r.trim()).filter(r => r)
      };
      
      await axios.post(`${API}/jobs`, payload, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      toast.success("Job created! Awaiting admin approval.");
      onClose();
      onSuccess();
      setFormData({
        title: "",
        description: "",
        requirements: "",
        location: "",
        salary_range: "",
        job_type: "full-time",
        experience_level: "mid-level"
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create job");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent data-testid="create-job-dialog" className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl" style={{ fontFamily: 'Manrope, sans-serif' }}>Create Job Posting</DialogTitle>
          <DialogDescription>Fill in the details for your new job posting</DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label>Job Title *</Label>
            <Input
              data-testid="job-title-input"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="e.g. Senior Software Engineer"
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label>Description *</Label>
            <Textarea
              data-testid="job-description-input"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe the role, responsibilities, and ideal candidate..."
              rows={4}
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label>Requirements * (comma-separated)</Label>
            <Input
              data-testid="job-requirements-input"
              value={formData.requirements}
              onChange={(e) => setFormData({ ...formData, requirements: e.target.value })}
              placeholder="e.g. Python, React, 5+ years experience"
              required
            />
          </div>
          
          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Location *</Label>
              <Input
                data-testid="job-location-input"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                placeholder="e.g. Remote, New York, NY"
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label>Salary Range</Label>
              <Input
                data-testid="job-salary-input"
                value={formData.salary_range}
                onChange={(e) => setFormData({ ...formData, salary_range: e.target.value })}
                placeholder="e.g. $100k - $150k"
              />
            </div>
          </div>
          
          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Job Type *</Label>
              <Select value={formData.job_type} onValueChange={(value) => setFormData({ ...formData, job_type: value })}>
                <SelectTrigger data-testid="job-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="full-time">Full-time</SelectItem>
                  <SelectItem value="part-time">Part-time</SelectItem>
                  <SelectItem value="contract">Contract</SelectItem>
                  <SelectItem value="remote">Remote</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Experience Level *</Label>
              <Select value={formData.experience_level} onValueChange={(value) => setFormData({ ...formData, experience_level: value })}>
                <SelectTrigger data-testid="experience-level-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="entry-level">Entry Level</SelectItem>
                  <SelectItem value="mid-level">Mid Level</SelectItem>
                  <SelectItem value="senior">Senior</SelectItem>
                  <SelectItem value="lead">Lead</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <Button data-testid="submit-job-btn" type="submit" className="w-full bg-[#0F172A] hover:bg-[#1E293B]">
            Create Job Posting
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default EmployerDashboard;
