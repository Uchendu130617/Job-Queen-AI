import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Briefcase, Search, MapPin, DollarSign, ExternalLink, ArrowLeft, Filter, Sparkles } from "lucide-react";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const JobsPage = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [showJobDialog, setShowJobDialog] = useState(false);
  
  // Filters
  const [dateFilter, setDateFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetchJobs();
  }, [dateFilter, sourceFilter, typeFilter, locationFilter]);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (dateFilter) params.append('date_posted_days', dateFilter);
      if (sourceFilter) params.append('source', sourceFilter);
      if (typeFilter) params.append('employment_type', typeFilter);
      if (locationFilter) params.append('location', locationFilter);
      params.append('limit', '50');

      const response = await axios.get(`${API}/jobs/all?${params.toString()}`);
      setJobs(response.data);
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
      toast.error("Failed to load jobs. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const filteredJobs = searchQuery
    ? jobs.filter(job => {
        const title = job.title || job.job_title || "";
        const company = job.company_name || "";
        const description = job.description || job.short_description || "";
        const search = searchQuery.toLowerCase();
        return title.toLowerCase().includes(search) ||
               company.toLowerCase().includes(search) ||
               description.toLowerCase().includes(search);
      })
    : jobs;

  const handleApply = async (job) => {
    if (job.is_external) {
      // Track external apply
      try {
        await axios.post(
          `${API}/tracking/external-apply`,
          null,
          {
            params: {
              job_id: job.id,
              source: job.source
            },
            headers: { Authorization: `Bearer ${token}` }
          }
        );
      } catch (error) {
        console.error("Tracking error:", error);
      }
      
      // Redirect to original source
      window.open(job.original_job_url, '_blank');
      toast.success(`Opening job on ${job.source}`);
    } else {
      // Internal job - navigate to application
      setSelectedJob(job);
      setShowJobDialog(true);
    }
  };

  const handleInternalApply = async (coverLetter) => {
    try {
      await axios.post(
        `${API}/applications`,
        {
          job_id: selectedJob.id,
          cover_letter: coverLetter
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success("Application submitted successfully!");
      setShowJobDialog(false);
      setSelectedJob(null);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || "Failed to apply";
      toast.error(errorMsg);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      {/* Header */}
      <nav className="bg-white border-b border-[#E2E8F0]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                onClick={() => navigate('/jobseeker/dashboard')}
                className="text-[#64748B] hover:text-[#0F172A]"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
              </Button>
              <div className="border-l border-[#E2E8F0] h-6" />
              <div className="flex items-center gap-2">
                <Briefcase className="h-6 w-6 text-[#0F172A]" />
                <span className="text-lg font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>Browse Jobs</span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search & Filters */}
        <div className="mb-6 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[#64748B]" />
            <Input
              type="text"
              placeholder="Search jobs by title, company, or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 py-6 text-lg"
            />
          </div>

          <div className="flex flex-wrap gap-4">
            <Select value={dateFilter} onValueChange={setDateFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Date posted" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">Last 24 hours</SelectItem>
                <SelectItem value="3">Last 3 days</SelectItem>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="14">Last 14 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sourceFilter} onValueChange={setSourceFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Source" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="jobquick">JobQuick</SelectItem>
                <SelectItem value="linkedin">LinkedIn</SelectItem>
                <SelectItem value="indeed">Indeed</SelectItem>
                <SelectItem value="glassdoor">Glassdoor</SelectItem>
              </SelectContent>
            </Select>

            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Job type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="full-time">Full-time</SelectItem>
                <SelectItem value="part-time">Part-time</SelectItem>
                <SelectItem value="contract">Contract</SelectItem>
                <SelectItem value="remote">Remote</SelectItem>
              </SelectContent>
            </Select>

            {(dateFilter || sourceFilter || typeFilter) && (
              <Button
                variant="outline"
                onClick={() => {
                  setDateFilter("");
                  setSourceFilter("");
                  setTypeFilter("");
                  setLocationFilter("");
                }}
              >
                Clear Filters
              </Button>
            )}
          </div>
        </div>

        {/* Results count */}
        <div className="mb-4">
          <p className="text-[#64748B]">
            Showing {filteredJobs.length} {filteredJobs.length === 1 ? 'job' : 'jobs'}
          </p>
        </div>

        {/* Jobs List */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="animate-spin h-8 w-8 border-4 border-[#3B82F6] border-t-transparent rounded-full mx-auto mb-4"></div>
              <p className="text-[#64748B]">Loading jobs...</p>
            </div>
          </div>
        ) : filteredJobs.length === 0 ? (
          <Card className="p-12 text-center border-[#E2E8F0]">
            <Briefcase className="h-16 w-16 text-[#CBD5E1] mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-[#0F172A] mb-2">No jobs found</h3>
            <p className="text-[#64748B] mb-4">
              {searchQuery || dateFilter || sourceFilter || typeFilter
                ? "Try adjusting your filters or search query"
                : "Check back soon for new opportunities"}
            </p>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredJobs.map((job) => (
              <Card
                key={job.id}
                className="border-[#E2E8F0] hover:border-[#3B82F6] transition-all cursor-pointer"
                onClick={() => {
                  setSelectedJob(job);
                  setShowJobDialog(true);
                }}
              >
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <CardTitle className="text-xl">{job.title || job.job_title}</CardTitle>
                        {job.is_external && (
                          <Badge variant="outline" className="bg-[#EFF6FF] text-[#2563EB] border-[#2563EB]">
                            <ExternalLink className="h-3 w-3 mr-1" />
                            {job.source}
                          </Badge>
                        )}
                      </div>
                      <CardDescription className="text-base mb-3">{job.company_name}</CardDescription>
                      <p className="text-sm text-[#64748B] mb-3 line-clamp-2">
                        {job.description || job.short_description}
                      </p>
                      <div className="flex flex-wrap gap-3 text-sm text-[#64748B]">
                        <span className="flex items-center gap-1">
                          <MapPin className="h-4 w-4" />
                          {job.location}
                        </span>
                        <span className="flex items-center gap-1">
                          <Briefcase className="h-4 w-4" />
                          {job.job_type || job.employment_type}
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
        )}
      </div>

      {/* Job Detail Dialog */}
      <Dialog open={showJobDialog} onOpenChange={setShowJobDialog}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selectedJob && (
            <JobDetailDialog 
              job={selectedJob}
              onApply={handleApply}
              onInternalApply={handleInternalApply}
              onClose={() => setShowJobDialog(false)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Job Detail Dialog Component
const JobDetailDialog = ({ job, onApply, onInternalApply, onClose }) => {
  const [coverLetter, setCoverLetter] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (job.is_external) {
      onApply(job);
      onClose();
    } else {
      onInternalApply(coverLetter);
    }
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle className="text-2xl">{job.title || job.job_title}</DialogTitle>
        <DialogDescription className="text-lg">{job.company_name}</DialogDescription>
      </DialogHeader>

      <div className="space-y-6 mt-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">{job.job_type || job.employment_type}</Badge>
          <Badge variant="outline">{job.location}</Badge>
          {job.salary_range && <Badge variant="outline">{job.salary_range}</Badge>}
          {job.is_external && (
            <Badge className="bg-[#2563EB] text-white">
              <ExternalLink className="h-3 w-3 mr-1" />
              External - {job.source}
            </Badge>
          )}
        </div>

        <div>
          <h3 className="font-semibold mb-2">Description</h3>
          <p className="text-[#64748B]">{job.description || job.short_description}</p>
        </div>

        {(job.requirements || job.skills_keywords) && (
          <div>
            <h3 className="font-semibold mb-2">Requirements</h3>
            <ul className="list-disc list-inside text-[#64748B] space-y-1">
              {(job.requirements || job.skills_keywords).map((req, idx) => (
                <li key={idx}>{req}</li>
              ))}
            </ul>
          </div>
        )}

        {job.is_external && (
          <div className="p-4 bg-[#EFF6FF] border border-[#2563EB] rounded-md">
            <p className="text-sm text-[#1E40AF]">
              <strong>External Job:</strong> This job will open on {job.source}. 
              You'll be redirected to apply directly on their platform.
            </p>
          </div>
        )}

        {!job.is_external && (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label>Cover Letter (Optional)</Label>
              <Textarea
                value={coverLetter}
                onChange={(e) => setCoverLetter(e.target.value)}
                placeholder="Why are you interested in this position?"
                rows={4}
              />
            </div>
          </form>
        )}

        <div className="flex gap-4">
          <Button
            onClick={handleSubmit}
            className="flex-1 bg-[#0F172A] hover:bg-[#1E293B] text-white"
          >
            {job.is_external ? `Apply on ${job.source}` : "Submit Application"}
          </Button>
          <Button
            onClick={onClose}
            variant="outline"
            className="flex-1"
          >
            Cancel
          </Button>
        </div>
      </div>
    </>
  );
};

export default JobsPage;
