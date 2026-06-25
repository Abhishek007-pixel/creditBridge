import React, { useState, useEffect } from 'react';

import { Login } from './components/Login';
import { ApplicantPortal } from './components/ApplicantPortal';
import { BankDashboard } from './components/BankDashboard';
import { AdminPanel } from './components/AdminPanel';
import { CreditCard, LogOut, Sun, Moon, Sparkles, Scale, Terminal } from 'lucide-react';

interface LoggedInUser {
  uid: string;
  email: string;
  role: 'applicant' | 'officer' | 'admin';
  name?: string;
}

export default function App() {
  const [user, setUser] = useState<LoggedInUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [darkMode, setDarkMode] = useState<boolean>(true);

  // Sync Dark/Light Mode Tailwind class smoothly
  useEffect(() => {
    const root = window.document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
      root.style.backgroundColor = "#0a0a0a";
    } else {
      root.classList.remove('dark');
      root.style.backgroundColor = "#f5f5f5";
    }
  }, [darkMode]);

  // Firebase is removed. Use localStorage token to verify session on load
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          // Verify token against our backend (you could add a /api/auth/verify endpoint)
          const res = await fetch('http://localhost:3001/api/me', {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (res.ok) {
            const data = await res.json();
            // Try to parse from token for now if we stored it in localstorage
            // Or just use the backend data
            // Since we don't have a /verify, let's just rely on local state or decode JWT
            // This is simplified. The user needs to login again if refreshed for now, or decode JWT.
            // A quick JWT decode:
            const payload = JSON.parse(atob(token.split('.')[1]));
            setUser({
              uid: payload.uid,
              email: payload.email,
              role: payload.role || 'applicant',
              name: payload.name || payload.email.split('@')[0]
            });
          } else {
            localStorage.removeItem('token');
          }
        } catch (e) {
          localStorage.removeItem('token');
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  const handleLogout = async () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-950 flex flex-col justify-center items-center text-center text-neutral-200 select-none">
        <span className="p-3 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-xl shadow-lg border border-neutral-800 mb-4 animate-bounce">
          <CreditCard className="w-8 h-8 text-white animate-pulse" />
        </span>
        <h2 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-neutral-200 to-blue-400 bg-clip-text text-transparent animate-pulse font-display">
          Synchronizing Credit Ledger...
        </h2>
        <p className="text-xs text-neutral-500 mt-1 font-mono uppercase tracking-widest">CreditBridge Secure System</p>
      </div>
    );
  }

  if (!user) {
    return (
      <Login 
        onLoginSuccess={(userData) => setUser(userData)}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
      />
    );
  }

  return (
    <div className="min-h-screen bg-neutral-950 dark:bg-neutral-950 text-neutral-200 dark:text-neutral-200 Light:bg-neutral-50 Light:text-neutral-800 transition-colors duration-300 flex flex-col justify-between selection:bg-blue-600 selection:text-white">
      
      {/* Global Brand Header (Direct reference of slide 1 and 7 layout style) */}
      <header className="border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-md sticky top-0 z-50 px-4 sm:px-6 lg:px-8 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-xl shadow-lg shadow-blue-900/10 border border-neutral-700/30">
              <CreditCard className="w-5 h-5 text-white" />
            </span>
            <div className="text-left font-display">
              <p className="text-sm font-black tracking-tight text-white leading-none">CreditBridge</p>
              <p className="text-[9px] uppercase font-mono tracking-widest text-blue-400 mt-1 font-bold">Alternate credit scorer</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Quick dashboard tags */}
            <span className="hidden md:inline-flex items-center gap-1.5 px-3 py-1 bg-neutral-800/80 border border-neutral-700/60 text-xs rounded-full text-blue-400 font-mono tracking-wide font-bold">
              <Sparkles className="w-3.5 h-3.5" /> PSB Hackathon 2026
            </span>

            {/* Dark Mode toggle */}
            <button 
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 bg-neutral-850 hover:bg-neutral-800 border border-neutral-700/60 rounded-lg text-neutral-300 hover:text-white hover:border-neutral-600 transition-all cursor-pointer"
            >
              {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </header>

      {/* Main Container frame */}
      <main className="flex-grow flex flex-col justify-start px-4 sm:px-6 lg:px-8 py-6">
        {user.role === 'applicant' && <ApplicantPortal user={user} onLogout={handleLogout} />}
        {user.role === 'officer' && <BankDashboard user={user} onLogout={handleLogout} />}
        {user.role === 'admin' && <AdminPanel user={user} onLogout={handleLogout} />}
      </main>

      {/* System Invariant margin clutter (No AI Slop / humble Clean Footer) */}
      <footer className="border-t border-neutral-850 px-4 sm:px-6 lg:px-8 py-4 bg-neutral-900/40">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-2 text-xs text-neutral-500 font-mono print:hidden">
          <p>© 2026 CreditBridge alternate bureau. All rights reserved.</p>
          <p className="flex items-center gap-1">
            <span>🛡️ DPDP Act Compliant</span> • <span>🇮🇳 Ministry of Finance DFS</span>
          </p>
        </div>
      </footer>

    </div>
  );
}
