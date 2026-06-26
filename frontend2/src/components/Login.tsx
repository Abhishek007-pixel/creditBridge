import React, { useState } from 'react';
import { Shield, Sparkles, User, CreditCard, ChevronRight, Moon, Sun, ArrowRight, UserCheck } from 'lucide-react';

interface LoginProps {
  onLoginSuccess: (user: { uid: string; email: string; role: 'applicant' | 'officer' | 'admin'; name?: string }) => void;
  darkMode: boolean;
  setDarkMode: (val: boolean) => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess, darkMode, setDarkMode }) => {
  const [role, setRole] = useState<'applicant' | 'officer' | 'admin'>('applicant');
  const [isRegister, setIsRegister] = useState<boolean>(false);
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [name, setName] = useState<string>('');
  const [phone, setPhone] = useState<string>('');
  const [aadhaarLast4, setAadhaarLast4] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  // Quick Seed Logins for pristine hackathon presentation
  const demoProfiles = [
    { name: "Priya Sharma (MSME)", userId: "demo-priya-002", email: "priya@creditbridge.com", pass: "password123", role: "applicant" as const },
    { name: "Ravi Kumar (Tea Seller)", userId: "demo-ravi-001", email: "ravi@creditbridge.com", pass: "password123", role: "applicant" as const },
    { name: "UCO Bank Officer", email: "officer@creditbridge.com", pass: "bankpass123", role: "officer" as const },
    { name: "Global Admin", email: "admin@creditbridge.com", pass: "admin123", role: "admin" as const }
  ];

  const handleQuickLogin = async (profile: typeof demoProfiles[0]) => {
    setError('');
    setLoading(true);
    try {
      // First try to sign in
      let res = await fetch('http://localhost:3001/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: profile.email, password: profile.pass })
      });
      
      let data = await res.json();
      
      if (!res.ok) {
        // If not found, register it
        res = await fetch('http://localhost:3001/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: profile.email, password: profile.pass, name: profile.name, role: profile.role })
        });
        data = await res.json();
        
        if (!res.ok) throw new Error(data.error || 'Failed to register demo user');
      }

      localStorage.setItem('token', data.token);

      onLoginSuccess({
        uid: data.user.uid,
        email: data.user.email,
        role: data.user.role,
        name: data.user.name || profile.name
      });
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Error executing quick login.');
    } finally {
      setLoading(false);
    }
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!email || !password) {
      setError('Please fill in all email and password fields.');
      setLoading(false);
      return;
    }

    try {
      const endpoint = isRegister ? 'http://localhost:3001/api/auth/register' : 'http://localhost:3001/api/auth/login';
      const payload: any = { email, password };
      
      if (isRegister) {
        if (!name) throw new Error('Name is required for registration.');
        if (role === 'applicant' && (!phone || !aadhaarLast4)) {
          throw new Error('Phone and Aadhaar Last 4 digits are required.');
        }
        payload.name = name;
        payload.role = role;
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Authentication failed');

      localStorage.setItem('token', data.token);

      if (isRegister && role === 'applicant') {
        // Pre-populate applicant registry via new API
        await fetch('http://localhost:3001/api/applicants', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${data.token}`
          },
          body: JSON.stringify({
            name,
            email,
            phone,
            aadhaar_last4: aadhaarLast4,
            aadhaar_hash: btoa(`cb-aadhaar-${aadhaarLast4}`).slice(0, 15)
          })
        });
      }

      onLoginSuccess({
        uid: data.user.uid,
        email: data.user.email,
        role: data.user.role || 'applicant',
        name: data.user.name || name || email.split('@')[0]
      });
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-12 bg-neutral-950 text-neutral-200 transition-colors duration-300">
      
      {/* Col 1: Marketing / Product Pitch Frame (Direct mapping of PDF slide 1 and 2) */}
      <div className="lg:col-span-12 xl:col-span-7 flex flex-col justify-between p-8 xl:p-12 relative overflow-hidden bg-gradient-to-br from-neutral-950 via-neutral-900 to-indigo-950 border-r border-neutral-800">
        
        {/* Subtle grid lines background overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#171717_1px,transparent_1px),linear-gradient(to_bottom,#171717_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-35"></div>
 
        {/* Brand Header */}
        <div className="flex items-center justify-between relative z-10 font-display">
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-xl shadow-lg shadow-blue-900/30">
              <CreditCard className="w-6 h-6 text-white" />
            </span>
            <span className="text-xl font-black tracking-tight bg-gradient-to-r from-white via-neutral-200 to-blue-400 bg-clip-text text-transparent">
              CreditBridge
            </span>
          </div>
          
          {/* Quick theme selector and meta tags */}
          <div className="flex items-center gap-4">
            <span className="text-xs bg-neutral-800/80 border border-neutral-700/60 px-3 py-1.5 rounded-full text-blue-400 font-mono tracking-wide font-bold">
              PSB Hackathon 2026
            </span>
            <button 
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 bg-neutral-800 hover:bg-neutral-700 rounded-lg text-neutral-300 hover:text-white transition-colors cursor-pointer"
            >
              {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Hero Pitch Frame (PDF Slide page 1 & 2) */}
        <div className="my-auto py-12 relative z-10 max-w-2xl text-left">
          <span className="px-3 py-1 bg-blue-500/10 border border-blue-400/20 text-blue-300 text-xs rounded-full font-medium uppercase tracking-wider mb-6 inline-flex font-mono">
            Alternate Credit Scoring System
          </span>
          <h1 className="text-4xl sm:text-5xl xl:text-6xl font-extrabold tracking-tight text-white leading-[1.08] mt-4 mb-6 font-display">
            AI-Powered Credit <br />
            for the <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">Invisible</span>
          </h1>
          <p className="text-neutral-300 text-base sm:text-lg leading-relaxed mb-8">
            Unlock fair bank loans for 190M+ borrowers who have no CIBIL score. 
            CreditBridge bypasses the bureau catch-22, scoring stability, integrity, 
            and cashflows dynamically through a consent-driven, secure Multi-Agent framework.
          </p>

          {/* Quick Stats Grid from slide 1 & 3 */}
          <div className="grid grid-cols-3 gap-4 border-t border-b border-neutral-800 py-6 mb-8">
            <div>
              <p className="text-xs text-neutral-400 font-mono uppercase tracking-wider font-semibold">Score Range</p>
              <p className="text-xl sm:text-2xl font-bold text-white mt-1">300-850</p>
              <p className="text-xs text-emerald-400 flex items-center gap-1 mt-0.5">
                <ChevronRight className="w-3 h-3 rotate-90" /> Like CIBIL scale
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-400 font-mono uppercase tracking-wider font-semibold">Processing Time</p>
              <p className="text-xl sm:text-2xl font-bold text-white mt-1">60s</p>
              <p className="text-xs text-blue-400 flex items-center gap-1 mt-0.5">
                ⚡ Fast response
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-400 font-mono uppercase tracking-wider font-semibold">Integrations</p>
              <p className="text-xl sm:text-2xl font-bold text-white mt-1">6 Channels</p>
              <p className="text-xs text-indigo-400 flex items-center gap-1 mt-0.5">
                🛡️ DPDP Compliant
              </p>
            </div>
          </div>

          {/* Value props tags */}
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="px-3 py-1.5 bg-neutral-900 border border-neutral-800 rounded-lg text-neutral-300">🛡️ Consent-first</span>
            <span className="px-3 py-1.5 bg-neutral-900 border border-neutral-800 rounded-lg text-neutral-300">🔒 AES-256 Encrypted</span>
            <span className="px-3 py-1.5 bg-neutral-900 border border-neutral-800 rounded-lg text-neutral-300">🧠 Explainable AI</span>
            <span className="px-3 py-1.5 bg-neutral-900 border border-neutral-800 rounded-lg text-neutral-300 font-mono">🇮🇳 DPDP Act 2023 Compliant</span>
          </div>
        </div>

        {/* Footer info */}
        <div className="relative z-10 flex flex-wrap gap-x-6 gap-y-2 text-neutral-500 text-xs border-t border-neutral-900 pt-4">
          <p>© 2026 CreditBridge • PSB Hackathon Pitch</p>
          <p>UCO Bank × Dept of Financial Services</p>
        </div>
      </div>

      {/* Col 2: High-Polish Auth Control panel */}
      <div className="lg:col-span-12 xl:col-span-5 flex flex-col justify-center p-8 sm:p-12 xl:p-16 relative z-10 bg-neutral-950">
        
        <div className="w-full max-w-md mx-auto text-left">
          {/* Persona selector tabs */}
          <div className="mb-8">
            <p className="text-xs text-neutral-400 uppercase tracking-widest font-semibold mb-3">Select System Entrance Portal</p>
            <div className="grid grid-cols-3 gap-1.5 bg-neutral-900 p-1.5 rounded-xl border border-neutral-800">
              <button
                type="button"
                onClick={() => setRole('applicant')}
                className={`py-2 px-1 text-xs sm:text-sm font-semibold rounded-lg transition-all cursor-pointer ${role === 'applicant' ? 'bg-blue-600 text-white shadow-md' : 'text-neutral-400 hover:text-white hover:bg-neutral-800/30'}`}
              >
                Applicant
              </button>
              <button
                type="button"
                onClick={() => setRole('officer')}
                className={`py-2 px-1 text-xs sm:text-sm font-semibold rounded-lg transition-all cursor-pointer ${role === 'officer' ? 'bg-blue-600 text-white shadow-md' : 'text-neutral-400 hover:text-white hover:bg-neutral-800/30'}`}
              >
                Bank Officer
              </button>
              <button
                type="button"
                onClick={() => setRole('admin')}
                className={`py-2 px-1 text-xs sm:text-sm font-semibold rounded-lg transition-all cursor-pointer ${role === 'admin' ? 'bg-blue-600 text-white shadow-md' : 'text-neutral-400 hover:text-white hover:bg-neutral-800/30'}`}
              >
                Admin
              </button>
            </div>
          </div>

          <div className="bg-neutral-900 border border-neutral-800 p-6 sm:p-8 rounded-2xl shadow-xl backdrop-blur-sm">
            <h2 className="text-2xl font-bold text-white mb-2 font-display">
              {isRegister ? 'Create Profile' : 'Authenticate User'}
            </h2>
            <p className="text-sm text-neutral-400 mb-6">
              {role === 'applicant' ? 'Enter Alternate Bureau' : 'Bank System Access Credential'}
            </p>

            {error && (
              <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs rounded-xl mb-4 line-clamp-3 leading-relaxed">
                {error}
              </div>
            )}

            <form onSubmit={handleAuth} className="space-y-4">
              {isRegister && (
                <div>
                  <label className="block text-xs uppercase tracking-wider font-semibold text-neutral-300 mb-1.5">Full Name</label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-neutral-950 border border-neutral-800 hover:border-neutral-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-3 text-sm text-white transition-all outline-none"
                    placeholder="e.g. Priya Sharma"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs uppercase tracking-wider font-semibold text-neutral-300 mb-1.5">Email Address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 hover:border-neutral-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-3 text-sm text-white transition-all outline-none"
                  placeholder="name@uco-bank.com"
                />
              </div>

              {isRegister && role === 'applicant' && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs uppercase tracking-wider font-semibold text-neutral-300 mb-1.5">Mobile No</label>
                    <input
                      type="tel"
                      required
                      maxLength={10}
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="w-full bg-neutral-950 border border-neutral-800 hover:border-neutral-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-3 text-sm text-white transition-all outline-none"
                      placeholder="9876543210"
                    />
                  </div>
                  <div>
                    <label className="block text-xs uppercase tracking-wider font-semibold text-neutral-300 mb-1.5">Aadhaar (Last 4)</label>
                    <input
                      type="text"
                      required
                      maxLength={4}
                      value={aadhaarLast4}
                      onChange={(e) => setAadhaarLast4(e.target.value)}
                      className="w-full bg-neutral-950 border border-neutral-800 hover:border-neutral-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-3 text-sm text-white transition-all outline-none"
                      placeholder="1234"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs uppercase tracking-wider font-semibold text-neutral-300 mb-1.5">Secret Key Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 hover:border-neutral-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-3 text-sm text-white transition-all outline-none"
                  placeholder="Min 6 characters"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-semibold shadow-lg active:scale-95 transition-all text-sm mt-2 relative overflow-hidden flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading ? 'Processing...' : isRegister ? 'Confirm Registration' : 'Access Dashboard'}
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>

            {/* Auth toggle */}
            <div className="mt-5 text-center text-xs">
              <span className="text-neutral-400">
                {isRegister ? 'Already have an entrance account?' : 'Invisible to the bank? Start your journey:'}
              </span>
              <button
                onClick={() => setIsRegister(!isRegister)}
                className="text-blue-400 font-semibold ml-1.5 hover:underline cursor-pointer"
              >
                {isRegister ? 'Sign In Here' : 'Create Profile Now'}
              </button>
            </div>
          </div>

          {/* Seed Logins Box - CRITICAL for presentation speed and ease */}
          <div className="mt-6 border border-neutral-800 bg-neutral-900 p-5 rounded-2xl relative overflow-hidden">
            <p className="text-[10px] text-neutral-400 font-mono uppercase tracking-wider mb-3.5 flex items-center gap-2 font-bold">
              <Sparkles className="w-3.5 h-3.5 text-blue-400" />
              PSB Hackathon Demo Quick Access
            </p>
            <div className="grid grid-cols-2 gap-2">
              {demoProfiles.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleQuickLogin(p)}
                  disabled={loading}
                  className="p-3 bg-neutral-950 hover:bg-neutral-800 border border-neutral-800 hover:border-blue-500 text-left rounded-xl transition-all cursor-pointer group disabled:opacity-50"
                >
                  <p className="text-xs text-white font-bold truncate group-hover:text-blue-400 transition-colors">
                    {p.name}
                  </p>
                  <p className="text-[10px] text-neutral-500 font-mono capitalize truncate mt-0.5">
                    {p.role === 'applicant' ? 'Applicant Profile' : p.role}
                  </p>
                </button>
              ))}
            </div>
          </div>

        </div>
      </div>
      
    </div>
  );
};
