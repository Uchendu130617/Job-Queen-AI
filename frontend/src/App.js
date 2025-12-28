import React, { useState, useEffect, createContext, useContext } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast, Toaster } from "sonner";
import { Briefcase, Users, Zap, TrendingUp, Search, Plus, FileText, BarChart, Settings, LogOut, Sparkles, CheckCircle, ArrowRight, Menu, X } from "lucide-react";
import EmployerDashboard from "@/components/EmployerDashboard";
import JobSeekerDashboard from "@/components/JobSeekerDashboard";
import AdminDashboard from "@/components/AdminDashboard";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUser(response.data);
    } catch (error) {
      console.error("Failed to fetch user", error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = (token, userData) => {
    localStorage.setItem("token", token);
    setToken(token);
    setUser(userData);
    toast.success("Welcome back!");
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
    toast.success("Logged out successfully");
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading, fetchUser }}>
      {children}
    </AuthContext.Provider>
  );
};

const LandingPage = () => {
  const [showAuth, setShowAuth] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      if (user.role === "admin") {
        navigate("/admin/dashboard");
      } else if (user.role === "employer") {
        navigate("/employer/dashboard");
      } else {
        navigate("/jobseeker/dashboard");
      }
    }
  }, [user]);

  return (
    <div data-testid="landing-page" className="min-h-screen bg-[#F8F9FA]">
      {/* Navigation */}
      <nav data-testid="nav-bar" className="bg-white border-b border-[#E2E8F0] sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Briefcase className="h-8 w-8 text-[#0F172A]" />
              <span className="text-xl font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>JobQuick AI</span>
            </div>
            
            <div className="hidden md:flex items-center gap-6">
              <a href="#features" className="text-[#64748B] hover:text-[#0F172A] transition-colors">Features</a>
              <a href="#pricing" className="text-[#64748B] hover:text-[#0F172A] transition-colors">Pricing</a>
              <Button data-testid="get-started-btn" onClick={() => setShowAuth(true)} className="bg-[#0F172A] hover:bg-[#1E293B] text-white">
                Get Started
              </Button>
            </div>

            <button data-testid="mobile-menu-btn" className="md:hidden" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
              {mobileMenuOpen ? <X /> : <Menu />}
            </button>
          </div>
        </div>
        
        {mobileMenuOpen && (
          <div data-testid="mobile-menu" className="md:hidden bg-white border-t border-[#E2E8F0] p-4">
            <div className="flex flex-col gap-4">
              <a href="#features" className="text-[#64748B] hover:text-[#0F172A]">Features</a>
              <a href="#pricing" className="text-[#64748B] hover:text-[#0F172A]">Pricing</a>
              <Button onClick={() => setShowAuth(true)} className="bg-[#0F172A] hover:bg-[#1E293B] text-white w-full">
                Get Started
              </Button>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section data-testid="hero-section" className="relative bg-gradient-to-tr from-blue-50 to-indigo-50 py-20 lg:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <Badge data-testid="ai-badge" className="ai-badge mb-6">
                <Sparkles className="h-3 w-3" />
                AI-Powered Matching
              </Badge>
              <h1 data-testid="hero-title" className="text-4xl sm:text-5xl lg:text-6xl font-bold text-[#0F172A] mb-6" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Find Your Perfect Match in Seconds
              </h1>
              <p data-testid="hero-subtitle" className="text-lg text-[#64748B] mb-8 leading-relaxed">
                JobQuick AI uses advanced algorithms to match job seekers with ideal opportunities and helps employers find top talent—all powered by intelligent automation.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Button data-testid="hero-cta-employer" onClick={() => setShowAuth(true)} size="lg" className="bg-[#0F172A] hover:bg-[#1E293B] text-white px-8">
                  For Employers <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
                <Button data-testid="hero-cta-jobseeker" onClick={() => setShowAuth(true)} size="lg" variant="outline" className="border-[#E2E8F0] hover:bg-[#F1F5F9] px-8">
                  For Job Seekers
                </Button>
              </div>
            </div>
            <div className="relative">
              <img data-testid="hero-image" src="https://images.unsplash.com/photo-1765366417046-f46361a7f26f?crop=entropy&cs=srgb&fm=jpg&q=85" alt="Modern workspace" className="rounded-lg shadow-xl" />
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" data-testid="features-section" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A] mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>Powered by Intelligence</h2>
            <p className="text-lg text-[#64748B] max-w-2xl mx-auto">Our AI technology streamlines recruitment, making hiring faster and smarter.</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <Card data-testid="feature-card-resume" className="bg-white border-[#E2E8F0] hover:border-[#3B82F6] transition-all duration-200">
              <CardHeader>
                <FileText className="h-10 w-10 text-[#2563EB] mb-4" />
                <CardTitle className="text-xl">AI Resume Parsing</CardTitle>
                <CardDescription>Instantly extract skills, experience, and qualifications from any resume format.</CardDescription>
              </CardHeader>
            </Card>
            
            <Card data-testid="feature-card-matching" className="bg-white border-[#E2E8F0] hover:border-[#3B82F6] transition-all duration-200">
              <CardHeader>
                <Zap className="h-10 w-10 text-[#2563EB] mb-4" />
                <CardTitle className="text-xl">Smart Job Matching</CardTitle>
                <CardDescription>Our algorithm matches candidates with jobs based on skills, experience, and preferences.</CardDescription>
              </CardHeader>
            </Card>
            
            <Card data-testid="feature-card-screening" className="bg-white border-[#E2E8F0] hover:border-[#3B82F6] transition-all duration-200">
              <CardHeader>
                <Users className="h-10 w-10 text-[#2563EB] mb-4" />
                <CardTitle className="text-xl">Automated Screening</CardTitle>
                <CardDescription>Save hours with AI-powered candidate screening and instant qualification assessments.</CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" data-testid="pricing-section" className="py-20 bg-[#F8F9FA]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A] mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>Simple, Transparent Pricing</h2>
            <p className="text-lg text-[#64748B]">Start free and upgrade as you grow</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <Card data-testid="pricing-card-free" className="bg-white border-[#E2E8F0]">
              <CardHeader>
                <CardTitle className="text-2xl">Free</CardTitle>
                <div className="mt-4">
                  <span className="text-4xl font-bold">$0</span>
                  <span className="text-[#64748B]">/month</span>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-[#64748B]">
                  <li className="flex items-center gap-2"><CheckCircle className="h-5 w-5 text-[#10B981]" /> 10 AI credits/month</li>
                  <li className="flex items-center gap-2"><CheckCircle className="h-5 w-5 text-[#10B981]" /> Basic job posting</li>
                  <li className="flex items-center gap-2"><CheckCircle className="h-5 w-5 text-[#10B981]" /> Limited applications</li>
                </ul>
              </CardContent>
            </Card>
            
            <Card data-testid="pricing-card-professional" className="bg-white border-[#2563EB] shadow-lg relative">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                <Badge className="bg-[#2563EB] text-white">Popular</Badge>
              </div>
              <CardHeader>
                <CardTitle className="text-2xl">Professional</CardTitle>
                <div className="mt-4">
                  <span className="text-4xl font-bold">$49</span>
                  <span className="text-[#64748B]">/month</span>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-[#64748B]">
                  <li className="flex items-center gap-2"><CheckCircle className="h-5 w-5 text-[#10B981]" /> 100 AI credits/month</li>
                  <li className="flex items-center gap-2"><CheckCircle className="h-5 w-5 text-[#10B981]" /> Unlimited job postings</li>
                  <li className="flex items-center gap-2"><CheckCircle className="h-5 w-5 text-[#10B981]" /> Priority support</li>
                  <li className="flex items-center gap-2"><CheckCircle className="h-5 w-5 text-[#10B981]" /> Advanced analytics</li>
                </ul>
              </CardContent>
            </Card>
            
            <Card data-testid="pricing-card-enterprise" className="bg-white border-[#E2E8F0]">
              <CardHeader>
                <CardTitle className="text-2xl">Enterprise</CardTitle>
                <div className="mt-4">
                  <span className="text-4xl font-bold">$199</span>
                  <span className="text-[#64748B]">/month</span>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-[#64748B]">
                  <li className="flex items-center gap-2"><CheckCircle className="h-5 w-5 text-[#10B981]" /> 500 AI credits/month</li>
                  <li className="flex items-center gap-2"><CheckCircle className="h-5 w-5 text-[#10B981]" /> Everything in Pro</li>
                  <li className="flex items-center gap-2"><CheckCircle className="h-5 w-5 text-[#10B981]" /> Dedicated support</li>
                  <li className="flex items-center gap-2"><CheckCircle className="h-5 w-5 text-[#10B981]" /> Custom integrations</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer data-testid="footer" className="bg-[#0F172A] text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Briefcase className="h-6 w-6" />
            <span className="text-lg font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>JobQuick AI</span>
          </div>
          <p className="text-[#94A3B8] text-sm">© 2025 JobQuick AI. Powered by intelligent automation.</p>
        </div>
      </footer>

      {/* Auth Dialog */}
      <Dialog open={showAuth} onOpenChange={setShowAuth}>
        <DialogContent data-testid="auth-dialog" className="sm:max-w-md">
          <AuthForm onClose={() => setShowAuth(false)} />
        </DialogContent>
      </Dialog>
    </div>
  );
};

const AuthForm = ({ onClose }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [role, setRole] = useState("employer");
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    full_name: "",
    company_name: ""
  });
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const endpoint = isLogin ? `${API}/auth/login` : `${API}/auth/register`;
      const payload = isLogin 
        ? { email: formData.email, password: formData.password }
        : { ...formData, role };
      
      const response = await axios.post(endpoint, payload);
      login(response.data.access_token, response.data.user);
      onClose();
      navigate(role === "employer" ? "/employer/dashboard" : "/jobseeker/dashboard");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Authentication failed");
    }
  };

  return (
    <div data-testid="auth-form">
      <DialogHeader>
        <DialogTitle className="text-2xl" style={{ fontFamily: 'Manrope, sans-serif' }}>
          {isLogin ? "Welcome Back" : "Create Account"}
        </DialogTitle>
        <DialogDescription>
          {isLogin ? "Sign in to your account" : "Join JobQuick AI today"}
        </DialogDescription>
      </DialogHeader>
      
      <form onSubmit={handleSubmit} className="space-y-4 mt-4">
        {!isLogin && (
          <div data-testid="role-selector" className="space-y-2">
            <Label>I am a...</Label>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger data-testid="role-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem data-testid="role-employer" value="employer">Employer (Hiring)</SelectItem>
                <SelectItem data-testid="role-jobseeker" value="job_seeker">Job Seeker</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}
        
        {!isLogin && (
          <div className="space-y-2">
            <Label>Full Name</Label>
            <Input
              data-testid="input-fullname"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              required
            />
          </div>
        )}
        
        {!isLogin && role === "employer" && (
          <div className="space-y-2">
            <Label>Company Name</Label>
            <Input
              data-testid="input-company"
              value={formData.company_name}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
            />
          </div>
        )}
        
        <div className="space-y-2">
          <Label>Email</Label>
          <Input
            data-testid="input-email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
          />
        </div>
        
        <div className="space-y-2">
          <Label>Password</Label>
          <Input
            data-testid="input-password"
            type="password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required
          />
        </div>
        
        <Button data-testid="submit-auth-btn" type="submit" className="w-full bg-[#0F172A] hover:bg-[#1E293B] text-white">
          {isLogin ? "Sign In" : "Create Account"}
        </Button>
        
        <p className="text-center text-sm text-[#64748B]">
          {isLogin ? "Don't have an account?" : "Already have an account?"}
          <button
            data-testid="toggle-auth-mode"
            type="button"
            onClick={() => setIsLogin(!isLogin)}
            className="ml-2 text-[#2563EB] hover:underline"
          >
            {isLogin ? "Sign up" : "Sign in"}
          </button>
        </p>
      </form>
    </div>
  );
};

const ProtectedRoute = ({ children, requiredRole }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div data-testid="loading-spinner" className="flex items-center justify-center h-screen">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/" />;
  }

  if (requiredRole && user.role !== requiredRole) {
    return <Navigate to="/" />;
  }

  return children;
};

function App() {
  return (
    <AuthProvider>
      <Toaster position="top-right" />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/employer/dashboard"
            element={
              <ProtectedRoute requiredRole="employer">
                <EmployerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/jobseeker/dashboard"
            element={
              <ProtectedRoute requiredRole="job_seeker">
                <JobSeekerDashboard />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
