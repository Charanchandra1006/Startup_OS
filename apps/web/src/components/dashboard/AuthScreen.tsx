"use client";

import React, { useState } from "react";
import { Sparkles, ArrowRight, ShieldCheck, Lock, Mail, Key, User, Building, AlertCircle, CheckCircle2 } from "lucide-react";

interface AuthScreenProps {
  onLogin: (name?: string, email?: string) => void;
}

export function AuthScreen({ onLogin }: AuthScreenProps) {
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [name, setName] = useState("Charan Chandra");
  const [companyName, setCompanyName] = useState("VisionAI Technologies");
  const [email, setEmail] = useState("charanchandra1006@gmail.com");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    setSuccessMsg("");

    const endpoint = mode === "signin" 
      ? "http://localhost:4000/api/auth/login" 
      : "http://localhost:4000/api/auth/register";

    const payload = mode === "signin"
      ? { email, password: password || "demo_password" }
      : { name, company_name: companyName, email, password: password || "demo_password" };

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || `${mode === "signin" ? "Login" : "Registration"} failed. Please check your details.`);
      }

      // Save credentials in storage
      if (data.token) {
        localStorage.setItem("chief_token", data.token);
      }
      const loggedName = data.user?.name || name;
      const loggedEmail = data.user?.email || email;
      localStorage.setItem("chief_user_name", loggedName);
      localStorage.setItem("chief_user_email", loggedEmail);

      setSuccessMsg(`Successfully authenticated as ${loggedEmail}! Redirecting...`);
      setTimeout(() => {
        onLogin(loggedName, loggedEmail);
      }, 500);
    } catch (err: any) {
      console.warn("Backend authentication error:", err.message);
      // If backend fails (e.g. invalid credentials or DB offline), show error with quick demo fallback option
      if (mode === "signin" && err.message.includes("Invalid credentials")) {
        setError("Invalid email or password. If you haven't created an account yet, click 'Create Account' above!");
      } else if (mode === "register" && err.message.includes("already exists")) {
        setError("This email is already registered. Please switch to 'Sign In' above!");
      } else {
        setError(`${err.message} (You can also use 'Quick Demo Access' below if offline).`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoAccess = () => {
    setIsLoading(true);
    setTimeout(() => {
      localStorage.setItem("chief_user_name", name);
      localStorage.setItem("chief_user_email", email);
      onLogin(name, email);
    }, 400);
  };

  return (
    <div className="min-h-screen w-full bg-white text-black flex flex-col justify-between p-6 sm:p-10 select-none font-sans">
      {/* Top Header */}
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-xl bg-black text-white flex items-center justify-center font-bold shadow-sm">
            <Sparkles className="h-4 w-4" />
          </div>
          <span className="font-bold tracking-tight text-sm text-black">
            CHIEF OS <span className="text-neutral-400 font-normal">| Executive Suite</span>
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-neutral-500 bg-neutral-100 px-3 py-1.5 rounded-full border border-neutral-200">
          <ShieldCheck className="h-3.5 w-3.5 text-black" />
          <span>Zero-Trust Encrypted</span>
        </div>
      </header>

      {/* Main Center Card */}
      <main className="w-full max-w-sm mx-auto my-auto py-8">
        <div className="space-y-6 text-center">
          <div className="space-y-2">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-black">
              {mode === "signin" ? "Sign in to Chief OS" : "Create Founder Account"}
            </h1>
            <p className="text-xs text-neutral-500 font-normal">
              Autonomous AI Executive Assistant for Founder Vision & Operations
            </p>
          </div>

          {/* Mode Switcher */}
          <div className="grid grid-cols-2 p-1 rounded-xl bg-neutral-100 border border-neutral-200 text-xs font-semibold">
            <button
              type="button"
              onClick={() => { setMode("signin"); setError(""); setSuccessMsg(""); }}
              className={`py-2 rounded-lg transition-all cursor-pointer ${
                mode === "signin" ? "bg-white text-black shadow-2xs font-bold" : "text-neutral-500 hover:text-black"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setMode("register"); setError(""); setSuccessMsg(""); }}
              className={`py-2 rounded-lg transition-all cursor-pointer ${
                mode === "register" ? "bg-white text-black shadow-2xs font-bold" : "text-neutral-500 hover:text-black"
              }`}
            >
              Create Account
            </button>
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-neutral-100 border border-neutral-300 text-neutral-800 text-xs text-left flex items-start gap-2 font-medium">
              <AlertCircle className="h-4 w-4 text-black shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3 rounded-xl bg-neutral-100 border border-neutral-300 text-black text-xs text-left flex items-start gap-2 font-bold">
              <CheckCircle2 className="h-4 w-4 text-black shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5 text-left pt-1">
            {mode === "register" && (
              <>
                <div>
                  <label className="block text-[11px] font-mono uppercase text-neutral-600 mb-1.5 font-semibold">
                    Founder Full Name
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-neutral-50 border border-neutral-300 text-xs text-black focus:outline-none focus:border-black font-medium transition-colors"
                      placeholder="Charan Chandra"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-mono uppercase text-neutral-600 mb-1.5 font-semibold">
                    Company Name
                  </label>
                  <div className="relative">
                    <Building className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
                    <input
                      type="text"
                      required
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-neutral-50 border border-neutral-300 text-xs text-black focus:outline-none focus:border-black font-medium transition-colors"
                      placeholder="VisionAI Technologies"
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-[11px] font-mono uppercase text-neutral-600 mb-1.5 font-semibold">
                Work Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-neutral-50 border border-neutral-300 text-xs text-black focus:outline-none focus:border-black font-medium transition-colors"
                  placeholder="charanchandra1006@gmail.com"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[11px] font-mono uppercase text-neutral-600 font-semibold">
                  Password
                </label>
                {mode === "signin" && (
                  <span className="text-[10px] text-neutral-400 hover:text-black cursor-pointer transition-colors">
                    Forgot?
                  </span>
                )}
              </div>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-neutral-50 border border-neutral-300 text-xs text-black focus:outline-none focus:border-black font-medium transition-colors"
                  placeholder="Enter your password..."
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 rounded-xl bg-black hover:bg-neutral-800 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all duration-150 cursor-pointer shadow-sm disabled:opacity-50 mt-2"
            >
              {isLoading ? (
                <>
                  <div className="h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>{mode === "signin" ? "Signing In..." : "Creating Account..."}</span>
                </>
              ) : (
                <>
                  <span>{mode === "signin" ? "Sign In with Email" : "Register Founder Workspace"}</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </form>

          <div className="relative flex py-2 items-center">
            <div className="flex-grow border-t border-neutral-200"></div>
            <span className="flex-shrink mx-3 text-[10px] font-mono uppercase text-neutral-400">or continue with</span>
            <div className="flex-grow border-t border-neutral-200"></div>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <button
              type="button"
              onClick={handleDemoAccess}
              className="py-2.5 px-4 rounded-xl bg-neutral-50 hover:bg-neutral-100 border border-neutral-300 text-xs font-semibold text-black flex items-center justify-center gap-2 transition-colors cursor-pointer"
            >
              <span>Google SSO</span>
            </button>
            <button
              type="button"
              onClick={handleDemoAccess}
              className="py-2.5 px-4 rounded-xl bg-neutral-50 hover:bg-neutral-100 border border-neutral-300 text-xs font-semibold text-black flex items-center justify-center gap-2 transition-colors cursor-pointer"
            >
              <span>Quick Demo Access</span>
            </button>
          </div>
        </div>
      </main>

      {/* Bottom Footer */}
      <footer className="flex flex-col sm:flex-row items-center justify-between text-neutral-400 text-[11px] font-mono gap-2 border-t border-neutral-200 pt-6">
        <span>VisionAI Technologies Inc. All systems operational.</span>
        <div className="flex items-center gap-4">
          <span className="hover:text-black cursor-pointer transition-colors">Privacy Policy</span>
          <span className="hover:text-black cursor-pointer transition-colors">Terms of Service</span>
          <span className="hover:text-black cursor-pointer transition-colors">Security Roster</span>
        </div>
      </footer>
    </div>
  );
}
