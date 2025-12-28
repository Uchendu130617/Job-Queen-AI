import React, { useState, useEffect } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Briefcase, Users, DollarSign, LogOut, CheckCircle, XCircle, Clock, TrendingUp, Sparkles } from "lucide-react";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const AdminDashboard = () => {
  const { user, logout, token } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [users, setUsers] = useState([]);
  const [pendingJobs, setPendingJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [showJobDialog, setShowJobDialog] = useState(false);

  useEffect(() => {
    fetchAnalytics();
    fetchUsers();
    fetchPendingJobs();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API}/admin/analytics`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setAnalytics(response.data);
    } catch (error) {
      toast.error("Failed to load analytics");
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/admin/users?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUsers(response.data);
    } catch (error) {
      toast.error("Failed to load users");
    }
  };

  const fetchPendingJobs = async () => {
    try {
      const response = await axios.get(`${API}/admin/jobs/pending`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setPendingJobs(response.data);
    } catch (error) {
      toast.error("Failed to load pending jobs");
    }
  };

  const handleApproveUser = async (userId) => {
    try {
      await axios.put(`${API}/admin/users/${userId}/approve`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success("User approved");
      fetchUsers();
    } catch (error) {
      toast.error("Failed to approve user");
    }
  };

  const handleSuspendUser = async (userId) => {
    try {
      await axios.put(`${API}/admin/users/${userId}/suspend`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success("User suspended");
      fetchUsers();
    } catch (error) {
      toast.error("Failed to suspend user");
    }
  };

  const handleApproveJob = async (jobId) => {
    try {
      await axios.put(`${API}/admin/jobs/${jobId}/approve`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success("Job approved");
      fetchPendingJobs();
      setShowJobDialog(false);
    } catch (error) {
      toast.error("Failed to approve job");
    }
  };

  const handleRejectJob = async (jobId) => {
    const reason = prompt("Rejection reason:");
    if (!reason) return;

    try {
      await axios.put(`${API}/admin/jobs/${jobId}/reject`, null, {
        params: { reason },
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success("Job rejected");
      fetchPendingJobs();
      setShowJobDialog(false);
    } catch (error) {
      toast.error("Failed to reject job");
    }
  };

  return (
    <div data-testid="admin-dashboard" className="min-h-screen bg-[#F8F9FA]">
      {/* Navigation */}
      <nav data-testid="admin-nav" className="bg-[#0F172A] text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Briefcase className="h-6 w-6" />
              <span className="text-lg font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>Admin Panel</span>
            </div>
            <Button data-testid="logout-btn" variant="ghost" onClick={logout} size="sm" className="text-white hover:bg-[#1E293B]">
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 data-testid="dashboard-title" className="text-3xl font-bold text-[#0F172A] mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Platform Overview
          </h1>
          <p className="text-[#64748B]">Welcome, {user?.full_name}</p>
        </div>

        {/* Analytics Cards */}
        {analytics && (
          <div data-testid="analytics-grid" className="grid md:grid-cols-4 gap-6 mb-8">
            <Card className="border-[#E2E8F0]">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardDescription>Total Users</CardDescription>
                  <Users className="h-5 w-5 text-[#64748B]" />
                </div>
                <CardTitle className="text-3xl">{analytics.users.total}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-[#64748B]">
                  <div>Employers: {analytics.users.employers}</div>
                  <div>Job Seekers: {analytics.users.job_seekers}</div>
                  <div>Premium: {analytics.users.premium}</div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#E2E8F0]">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardDescription>Jobs</CardDescription>
                  <Briefcase className="h-5 w-5 text-[#64748B]" />
                </div>
                <CardTitle className="text-3xl">{analytics.jobs.active}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-[#64748B]">
                  <div>Total: {analytics.jobs.total}</div>
                  <div>Featured: {analytics.jobs.featured}</div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#E2E8F0] bg-gradient-to-br from-green-50 to-emerald-50">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardDescription>Monthly Revenue</CardDescription>
                  <DollarSign className="h-5 w-5 text-[#10B981]" />
                </div>
                <CardTitle className="text-3xl">${analytics.revenue.monthly_recurring}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-[#64748B]">
                  <div>Pro: {analytics.revenue.professional_subs}</div>
                  <div>Enterprise: {analytics.revenue.enterprise_subs}</div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#E2E8F0] bg-gradient-to-br from-indigo-50 to-violet-50">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardDescription>AI Credits Used</CardDescription>
                  <Sparkles className="h-5 w-5 text-[#8B5CF6]" />
                </div>
                <CardTitle className="text-3xl">{analytics.ai_usage.total_credits_consumed}</CardTitle>
              </CardHeader>
            </Card>
          </div>
        )}

        {/* Main Tabs */}
        <Tabs defaultValue="users" className="space-y-6">
          <TabsList data-testid="tabs-list">
            <TabsTrigger data-testid="tab-users" value="users">Users</TabsTrigger>
            <TabsTrigger data-testid="tab-jobs" value="jobs">Pending Jobs</TabsTrigger>
          </TabsList>

          <TabsContent value="users" className="space-y-4">
            <h2 className="text-2xl font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>User Management</h2>
            
            <div data-testid="users-list" className="space-y-4">
              {users.map((u) => (
                <Card key={u.id} data-testid={`user-card-${u.id}`} className="border-[#E2E8F0]">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg">{u.full_name}</CardTitle>
                        <CardDescription>{u.email}</CardDescription>
                        <div className="flex gap-2 mt-2">
                          <Badge variant={u.role === 'employer' ? 'default' : 'secondary'}>{u.role}</Badge>
                          <Badge variant="outline">{u.subscription_tier}</Badge>
                          {u.is_premium && <Badge className="bg-gradient-to-r from-indigo-500 to-violet-500 text-white">Premium</Badge>}
                          {!u.is_approved && <Badge variant="destructive">Pending Approval</Badge>}
                          {u.is_suspended && <Badge variant="destructive">Suspended</Badge>}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {!u.is_approved && u.role === 'employer' && (
                          <Button
                            data-testid={`approve-user-${u.id}`}
                            onClick={() => handleApproveUser(u.id)}
                            size="sm"
                            className="bg-[#10B981] hover:bg-[#059669]"
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Approve
                          </Button>
                        )}
                        {!u.is_suspended && u.role !== 'admin' && (
                          <Button
                            data-testid={`suspend-user-${u.id}`}
                            onClick={() => handleSuspendUser(u.id)}
                            size="sm"
                            variant="destructive"
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            Suspend
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="jobs" className="space-y-4">
            <h2 className="text-2xl font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>Pending Job Approvals</h2>
            
            <div data-testid="pending-jobs-list" className="space-y-4">
              {pendingJobs.length === 0 ? (
                <Card className="border-[#E2E8F0] p-12 text-center">
                  <p className="text-[#64748B]">No pending jobs</p>
                </Card>
              ) : (
                pendingJobs.map((job) => (
                  <Card
                    key={job.id}
                    data-testid={`pending-job-${job.id}`}
                    className="border-[#E2E8F0] hover:border-[#3B82F6] transition-colors cursor-pointer"
                    onClick={() => {
                      setSelectedJob(job);
                      setShowJobDialog(true);
                    }}
                  >
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle className="text-xl">{job.title}</CardTitle>
                          <CardDescription>{job.company_name || job.employer_name}</CardDescription>
                          <div className="mt-2">
                            <Badge variant="outline"><Clock className="h-3 w-3 mr-1" />Pending</Badge>
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Job Review Dialog */}
      <Dialog open={showJobDialog} onOpenChange={setShowJobDialog}>
        <DialogContent data-testid="job-review-dialog" className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selectedJob && (
            <>
              <DialogHeader>
                <DialogTitle className="text-2xl" style={{ fontFamily: 'Manrope, sans-serif' }}>{selectedJob.title}</DialogTitle>
                <DialogDescription>{selectedJob.company_name || selectedJob.employer_name}</DialogDescription>
              </DialogHeader>
              <div className="space-y-6 mt-4">
                <div>
                  <h3 className="font-semibold mb-2">Description</h3>
                  <p className="text-[#64748B]">{selectedJob.description}</p>
                </div>
                
                <div>
                  <h3 className="font-semibold mb-2">Requirements</h3>
                  <ul className="list-disc list-inside text-[#64748B]">
                    {selectedJob.requirements.map((req, idx) => (
                      <li key={idx}>{req}</li>
                    ))}
                  </ul>
                </div>
                
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <strong>Location:</strong> {selectedJob.location}
                  </div>
                  <div>
                    <strong>Type:</strong> {selectedJob.job_type}
                  </div>
                  <div>
                    <strong>Experience:</strong> {selectedJob.experience_level}
                  </div>
                  {selectedJob.salary_range && (
                    <div>
                      <strong>Salary:</strong> {selectedJob.salary_range}
                    </div>
                  )}
                </div>
                
                <div className="flex gap-4">
                  <Button
                    data-testid="approve-job-btn"
                    onClick={() => handleApproveJob(selectedJob.id)}
                    className="flex-1 bg-[#10B981] hover:bg-[#059669]"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Approve Job
                  </Button>
                  <Button
                    data-testid="reject-job-btn"
                    onClick={() => handleRejectJob(selectedJob.id)}
                    className="flex-1"
                    variant="destructive"
                  >
                    <XCircle className="h-4 w-4 mr-2" />
                    Reject Job
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
