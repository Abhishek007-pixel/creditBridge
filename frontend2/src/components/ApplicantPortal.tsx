import React, { useState, useEffect } from 'react';
import { psychometricQuestions } from '../lib/questions';
import { evaluateCreditScore, ScoreReport } from '../lib/scoring';
import { 
  ShieldCheck, CheckCircle2, AlertCircle, FileText, ChevronRight, HelpCircle, 
  Settings, LogOut, Check, Smartphone, ShoppingBag, MapPin, Scale, Store, Landmark, Info
} from 'lucide-react';

interface ApplicantPortalProps {
  user: { uid: string; email: string; role: 'applicant' | 'officer' | 'admin'; name?: string };
  onLogout: () => void;
}

export const ApplicantPortal: React.FC<ApplicantPortalProps> = ({ user, onLogout }) => {
  const [step, setStep] = useState<number>(1);
  const [profile, setProfile] = useState({
    name: user.name || '',
    email: user.email || '',
    phone: '',
    aadhaar_last4: ''
  });

  const [consents, setConsents] = useState<{ [key: string]: boolean }>({
    phone_bill: true,
    ecommerce: true,
    geolocation: true,
    merchant: true,
    cashflow: true
  });

  const [answers, setAnswers] = useState<number[]>(new Array(10).fill(-1));
  const [loading, setLoading] = useState<boolean>(false);
  const [report, setReport] = useState<ScoreReport | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<number>(0);
  const [status, setStatus] = useState<'pending' | 'approved' | 'rejected' | 'none'>('pending');

  const channels = [
    { key: "phone_bill", name: "Phone Bill payment history", weight: "25%", desc: "Measures EMI compliance, late delays and mobile billing consistency.", icon: <Smartphone className="w-5 h-5 text-indigo-400" /> },
    { key: "cashflow", name: "Bank Cashflow patterns", weight: "20%", desc: "Analyzes digital credit/debit logs, balance cushion and transaction failures.", icon: <Landmark className="w-5 h-5 text-indigo-400" /> },
    { key: "geolocation", name: "Physical Geolocation stability", weight: "15%", desc: "Surrogates social rootedness, household history and flight risk indices.", icon: <MapPin className="w-5 h-5 text-indigo-400" /> },
    { key: "ecommerce", name: "E-commerce purchase behavior", weight: "12%", desc: "Evaluates prepaid usage ratios, product returns discipline and buyer age.", icon: <ShoppingBag className="w-5 h-5 text-indigo-400" /> },
    { key: "merchant", name: "Merchant ratings & trade ties", weight: "8%", desc: "Acquires supplier reliability logs and verified local trade standing.", icon: <Store className="w-5 h-5 text-indigo-400" /> },
  ];

  useEffect(() => {
    const fetchExistingData = async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem('token');
        if (!token) return;

        const res = await fetch('/api/me', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        if (data.applicant) {
          setProfile({
            name: data.applicant.name || user.name || '',
            email: data.applicant.email || user.email || '',
            phone: data.applicant.phone || '',
            aadhaar_last4: data.applicant.aadhaar_last4 || ''
          });
        }

        if (data.score) {
          setReport({
            final_score: data.score.final_score,
            risk_category: data.score.risk_category,
            decision: data.score.decision,
            loan_recommended: data.score.loan_recommended,
            interest_rate: data.score.interest_rate,
            weighted_average: data.score.weighted_average || 0,
            breakdown: data.score.breakdown || {},
            weights_used: data.score.weights_used || {},
            explanation: data.score.explanation
          });
          setStatus(data.score.status || 'pending');
          setStep(4);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchExistingData();
  }, [user.uid]);

  const handleRegisterProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile.phone || !profile.aadhaar_last4) return;
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      // Save consent to Python backend so agents can read consented sources
      await fetch('/api/consent', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          applicant_id: user.uid,
          phone_bill: consents.phone_bill,
          ecommerce: consents.ecommerce,
          geolocation: consents.geolocation,
          merchant: consents.merchant,
          cashflow: consents.cashflow,
        })
      });
      setStep(2);
    } catch (err) {
      console.error(err);
      setStep(2); // proceed even if consent save fails
    } finally {
      setLoading(false);
    }
  };


  const handleSaveConsent = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      // Save updated consent flags before moving to questionnaire
      await fetch('/api/consent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          applicant_id: user.uid,
          phone_bill: consents.phone_bill,
          ecommerce: consents.ecommerce,
          geolocation: consents.geolocation,
          merchant: consents.merchant,
          cashflow: consents.cashflow,
        })
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      setStep(3);
    }
  };

  const handleSelectAnswer = (qIdx: number, choiceIdx: number) => {
    const updated = [...answers];
    updated[qIdx] = choiceIdx;
    setAnswers(updated);
  };

  const handleSubmitQuestionnaire = async () => {
    if (answers.includes(-1)) return;
    setLoading(true);
    try {
      const token = localStorage.getItem('token');

      // POST only answers to Python — let Neuro SAN agents compute the score
      const res = await fetch('/api/score', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          applicant_id: user.uid,
          questionnaire_answers: answers,  // 10 psychometric answer indices [0-3]
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Score API error ${res.status}`);
      }

      const resultReport = await res.json();
      // resultReport shape from Python: {final_score, risk_category, loan_recommended,
      //   interest_rate, explanation, breakdown, weights_used, pipeline_mode, ...}
      setReport({
        final_score: resultReport.final_score,
        risk_category: resultReport.risk_category,
        decision: resultReport.risk_category,
        loan_recommended: resultReport.loan_recommended,
        interest_rate: resultReport.interest_rate,
        weighted_average: resultReport.final_score || 0,
        breakdown: resultReport.breakdown || {},
        weights_used: resultReport.weights_used || {},
        explanation: resultReport.explanation,
      });
      setStep(4);
    } catch (e: any) {
      console.error('Score submission error:', e);
      alert(`Scoring failed: ${e.message}. Check that the Python backend is running on port 8000.`);
    } finally {
      setLoading(false);
    }
  };

  const handlePrintCertificate = () => {
    window.print();
  };

  return (
    <div className="flex-grow flex flex-col justify-start relative max-w-4xl w-full mx-auto p-4 sm:p-6 lg:p-8 bg-neutral-900 border border-neutral-800 rounded-3xl shadow-xl mt-4 mb-12">
      
      {/* Top Navigation / Progress Indicator */}
      <div className="flex items-center justify-between border-b border-neutral-800 pb-5 mb-8">
        <div className="font-display">
          <span className="text-xs uppercase font-mono tracking-widest text-blue-400 font-bold">Applicant Portal</span>
          <h2 className="text-lg font-bold text-white mt-1">Hello, {profile.name || user.name || user.email.split('@')[0]}</h2>
        </div>
        <div className="flex items-center gap-4">
          <button 
            onClick={onLogout}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-neutral-800 hover:bg-neutral-750 text-xs font-semibold text-neutral-300 hover:text-white rounded-lg border border-neutral-700/60 transition-colors cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" /> Logout
          </button>
        </div>
      </div>

      {/* Progress Steps Header */}
      {step < 4 && (
        <div className="grid grid-cols-3 gap-2 mb-8 select-none">
          {[
            { id: 1, label: "Register Profile" },
            { id: 2, label: "Alternative Consent" },
            { id: 3, label: "Integrity Questions" }
          ].map((s) => (
            <div 
              key={s.id} 
              className={`pb-2 border-b-2 text-center transition-all ${step === s.id ? 'border-blue-500 text-blue-400 font-bold' : step > s.id ? 'border-indigo-600 text-neutral-400 font-medium' : 'border-neutral-800 text-neutral-500'}`}
            >
              <p className="text-xs uppercase font-mono tracking-wide">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Main Steps Content */}
      <div className="flex-grow">
        
        {/* Step 1: Profile Registry form */}
        {step === 1 && (
          <form onSubmit={handleRegisterProfile} className="space-y-6 text-left">
            <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850">
              <h3 className="text-lg font-bold text-white mb-2 font-display">Step 1: Create Alternate Credit Profile</h3>
              <p className="text-sm text-neutral-400 mb-6 font-sans">Confirm your personal identifiers. No formal credit history is required. All information is secured using AES-256 field encryption standards on the DB.</p>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs uppercase font-semibold tracking-wider text-neutral-300 mb-1.5">Official Name</label>
                  <input
                    type="text"
                    required
                    value={profile.name}
                    onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                    className="w-full bg-neutral-900 border border-neutral-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-3 text-sm text-white transition-all outline-none"
                    placeholder="Enter full name"
                  />
                </div>

                <div>
                  <label className="block text-xs uppercase font-semibold tracking-wider text-neutral-300 mb-1.5">Email Contact</label>
                  <input
                    type="email"
                    required
                    disabled
                    value={profile.email}
                    className="w-full bg-neutral-950 border border-neutral-850 text-neutral-500 rounded-xl px-4 py-3 text-sm cursor-not-allowed font-mono"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs uppercase font-semibold tracking-wider text-neutral-300 mb-1.5">Mobile No (UPI/Telem linked)</label>
                    <input
                      type="tel"
                      required
                      maxLength={10}
                      pattern="[0-9]{10}"
                      value={profile.phone}
                      onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                      className="w-full bg-neutral-900 border border-neutral-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-3 text-sm text-white transition-all outline-none"
                      placeholder="e.g. 9876543210"
                    />
                  </div>
                  <div>
                    <label className="block text-xs uppercase font-semibold tracking-wider text-neutral-300 mb-1.5">Aadhaar Card (Last 4 Digits)</label>
                    <input
                      type="text"
                      required
                      maxLength={4}
                      pattern="[0-9]{4}"
                      value={profile.aadhaar_last4}
                      onChange={(e) => setProfile({ ...profile, aadhaar_last4: e.target.value })}
                      className="w-full bg-neutral-900 border border-neutral-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-3 text-sm text-white transition-all outline-none"
                      placeholder="e.g. 5678"
                    />
                  </div>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-bold shadow-lg active:scale-95 transition-all text-sm flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              Configure Credit Channels <ChevronRight className="w-4 h-4" />
            </button>
          </form>
        )}

        {/* Step 2: Alternative Consent checklist */}
        {step === 2 && (
          <div className="space-y-6 text-left">
            <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850">
              <div className="flex items-center gap-2 text-emerald-400 mb-2">
                <ShieldCheck className="w-5 h-5 text-emerald-500" />
                <h3 className="text-lg font-bold text-white font-display">Step 2: DPDP Consent-First Data Integration</h3>
              </div>
              <p className="text-sm text-neutral-450 mb-6 leading-relaxed">In accordance with India's <strong>Digital Personal Data Protection (DPDP) Act 2023</strong>, you hold absolute rights to select which data pipelines to integrate. CreditBridge will dynamically redistribute weights so that rejecting a channel never zeroizes your score!</p>

              <div className="space-y-3.5">
                {channels.map((ch) => (
                  <div 
                    key={ch.key}
                    onClick={() => setConsents({ ...consents, [ch.key]: !consents[ch.key] })}
                    className={`flex items-start gap-4 p-4 rounded-xl border transition-all cursor-pointer select-none ${consents[ch.key] ? 'bg-neutral-900 border-blue-500 shadow-md' : 'bg-neutral-950 border-neutral-850 text-neutral-400'}`}
                  >
                    <div className="mt-1">
                      {ch.icon}
                    </div>
                    <div className="flex-grow">
                      <div className="flex items-center justify-between">
                        <p className={`text-sm font-bold ${consents[ch.key] ? 'text-white' : 'text-neutral-400'}`}>{ch.name}</p>
                        <span className="text-xs font-mono font-bold bg-neutral-800 text-blue-400 border border-neutral-700 px-2 py-0.5 rounded-md">
                          Weight: {ch.weight}
                        </span>
                      </div>
                      <p className="text-xs text-neutral-450 mt-1">{ch.desc}</p>
                    </div>
                    <div className="flex items-center h-full my-auto ml-2">
                      <span className={`w-5 h-5 rounded-md border flex items-center justify-center transition-colors ${consents[ch.key] ? 'bg-blue-600 border-blue-400 text-white' : 'border-neutral-800'}`}>
                        {consents[ch.key] && <Check className="w-3.5 h-3.5" />}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={handleSaveConsent}
              disabled={loading}
              className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-bold shadow-lg active:scale-95 transition-all text-sm flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              Fulfill Behavioral Questionnaire <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Step 3: Psychometric Questionnaire slider */}
        {step === 3 && (
          <div className="space-y-6 text-left">
            <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850">
              <div className="flex items-center justify-between mb-4 border-b border-neutral-850 pb-4">
                <div className="flex items-center gap-2">
                  <HelpCircle className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-lg font-bold text-white font-display">Step 3: Character & Moral Integrity Assessment</h3>
                </div>
                <span className="text-xs font-mono font-bold text-blue-400 bg-neutral-900 border border-neutral-800 px-2.5 py-1 rounded-md">
                  Q {currentQuestion + 1} of 10
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full h-1.5 bg-neutral-800 rounded-full mb-6 relative overflow-hidden">
                <div 
                  className="absolute h-full bg-blue-500 transition-all"
                  style={{ width: `${((currentQuestion + 1) / 10) * 100}%` }}
                ></div>
              </div>

              {/* Question display */}
              <div className="mb-6">
                <span className="px-2 py-0.5 bg-indigo-500/10 border border-indigo-400/20 text-indigo-300 text-[10px] uppercase font-mono tracking-wide rounded">
                  {psychometricQuestions[currentQuestion].category}
                </span>
                <h4 className="text-base sm:text-lg font-bold text-white mt-1.5 leading-snug">
                  {psychometricQuestions[currentQuestion].question}
                </h4>
                <p className="text-xs text-neutral-450 mt-2 italic flex items-center gap-1">
                  <Info className="w-3.5 h-3.5 text-neutral-500" /> {psychometricQuestions[currentQuestion].description}
                </p>
              </div>

              {/* Options selectors */}
              <div className="space-y-3">
                {psychometricQuestions[currentQuestion].options.map((opt, idx) => {
                  const isSelected = answers[currentQuestion] === idx;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleSelectAnswer(currentQuestion, idx)}
                      className={`w-full text-left p-4 rounded-xl border transition-all cursor-pointer ${isSelected ? 'bg-neutral-900 border-blue-500 text-white font-bold shadow-md' : 'bg-neutral-950 border-neutral-850 text-neutral-300 hover:bg-neutral-800/50'}`}
                    >
                      <div className="flex items-start gap-3">
                        <span className={`mt-0.5 w-4 h-4 rounded-full border flex items-center justify-center shrink-0 ${isSelected ? 'border-blue-400 bg-blue-600' : 'border-neutral-800'}`}>
                          {isSelected && <span className="w-1.5 h-1.5 bg-white rounded-full"></span>}
                        </span>
                        <div>
                          <p className="text-sm font-semibold">{opt.text}</p>
                          <p className={`text-xs mt-1 ${isSelected ? 'text-neutral-300' : 'text-neutral-400'}`}>{opt.description}</p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Steppers & Submit navigation */}
            <div className="flex items-center justify-between gap-4">
              <button
                disabled={currentQuestion === 0}
                onClick={() => setCurrentQuestion(currentQuestion - 1)}
                className="px-5 py-3.5 bg-neutral-800 hover:bg-neutral-750 disabled:opacity-30 rounded-xl text-sm text-neutral-300 hover:text-white font-bold transition-all cursor-pointer"
              >
                Previous
              </button>

              {currentQuestion < 9 ? (
                <button
                  disabled={answers[currentQuestion] === -1}
                  onClick={() => setCurrentQuestion(currentQuestion + 1)}
                  className="px-6 py-3.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-30 text-white rounded-xl text-sm font-bold shadow-md active:scale-95 transition-all flex items-center gap-1 cursor-pointer"
                >
                  Next Question <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  disabled={answers.includes(-1)}
                  onClick={handleSubmitQuestionnaire}
                  className="px-8 py-3.5 bg-gradient-to-r from-emerald-600 to-blue-600 hover:from-emerald-500 hover:to-blue-500 disabled:opacity-30 text-white rounded-xl text-sm font-bold shadow-lg active:scale-95 transition-all flex items-center gap-2 cursor-pointer"
                >
                  Generate Alternate score <ShieldCheck className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Step 4: Results screen with gorgeous credit score report details */}
        {step === 4 && report && (
          <div className="space-y-8 print:bg-white print:text-black print:p-0 text-left">
            
            {/* Header info */}
            <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 flex flex-col md:flex-row justify-between items-center gap-4">
              <div className="text-left font-display">
                <span className="text-xs uppercase tracking-widest text-[#3b82f6] font-extrabold">Alternate Credit Rating Report</span>
                <h3 className="text-2xl font-black text-white mt-1">{profileName(DEMO_APPLICANTS) || user.email}</h3>
                <p className="text-sm text-neutral-450 flex items-center gap-1.5 mt-1 font-mono">
                  ID: <span className="bg-neutral-900 border border-neutral-800 px-2 py-0.5 rounded text-neutral-300 select-all">{user.uid}</span>
                </p>
                <div className="flex items-center gap-2 mt-4 font-sans">
                  <span className={`px-2.5 py-1 text-xs font-bold rounded-lg ${
                    status === 'approved' ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' :
                    status === 'rejected' ? 'bg-rose-500/10 border border-rose-500/20 text-rose-400' :
                    'bg-amber-500/10 border border-amber-500/20 text-amber-400'
                  }`}>
                    Bank Status: {status === 'approved' ? 'Approved by Officer' : status === 'rejected' ? 'Rejected by Officer' : 'Decision Pending'}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={handlePrintCertificate}
                  className="px-4 py-2 bg-neutral-800 hover:bg-neutral-750 text-xs font-bold text-neutral-200 border border-neutral-700 hover:text-white rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <FileText className="w-4 h-4" /> Print Credit Certificate
                </button>
              </div>
            </div>

            {/* Dial & Loan Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
              
              {/* Score Gauge circular dial representation */}
              <div className="md:col-span-12 xl:col-span-5 bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 flex flex-col justify-center items-center text-center">
                <p className="text-xs uppercase font-mono text-neutral-500 tracking-wider mb-6 font-bold">Evaluation Rating</p>
                
                {/* SVG Gauge Circle */}
                <div className="relative w-44 h-44 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="88"
                      cy="88"
                      r="76"
                      stroke="#262626"
                      strokeWidth="12"
                      fill="transparent"
                    />
                    <circle
                      cx="88"
                      cy="88"
                      r="76"
                      stroke="url(#gradientScore)"
                      strokeWidth="12"
                      fill="transparent"
                      strokeDasharray="477.5"
                      strokeDashoffset={477.5 - (477.5 * ((report.final_score - 300) / (850 - 300)))}
                      strokeLinecap="round"
                    />
                    <defs>
                      <linearGradient id="gradientScore" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#ef4444" />
                        <stop offset="50%" stopColor="#f59e0b" />
                        <stop offset="100%" stopColor="#10b981" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute flex flex-col items-center">
                    <span className="text-4xl font-extrabold text-white tracking-tight font-display">{report.final_score}</span>
                    <span className="text-[10px] uppercase font-mono text-neutral-450 mt-1">/ 850 Rating</span>
                  </div>
                </div>

                {/* Score scale rating tags */}
                <div className="mt-4">
                  <span className={`px-3.5 py-1 text-xs font-extrabold rounded-full ${
                    report.final_score >= 750 ? 'bg-emerald-500/10 text-emerald-400' :
                    report.final_score >= 650 ? 'bg-emerald-500/10 text-emerald-400' :
                    report.final_score >= 550 ? 'bg-amber-500/10 text-amber-400' :
                    report.final_score >= 450 ? 'bg-orange-500/10 text-orange-400' :
                    'bg-rose-500/10 text-rose-400'
                  }`}>
                    {report.risk_category}
                  </span>
                </div>
              </div>

              {/* Loan Details Card */}
              <div className="md:col-span-12 xl:col-span-7 bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 flex flex-col justify-between">
                <div>
                  <span className="px-2.5 py-1 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] uppercase font-mono tracking-wider rounded font-bold">Pre-Qualified Limit</span>
                  <p className="text-xs text-neutral-450 mt-1">Assessed micro-commission recommended loan structure.</p>
                  
                  <div className="mt-6 flex items-baseline gap-2 font-display">
                    <span className="text-4xl sm:text-5xl font-black text-white tracking-tight">
                      ₹{report.loan_recommended ? report.loan_recommended.toLocaleString("en-IN") : '0'}
                    </span>
                    <span className="text-sm font-mono text-neutral-500">INR Max Limit</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 border-t border-neutral-800 pt-6 mt-6 font-mono">
                  <div>
                    <p className="text-[10px] uppercase tracking-wide text-neutral-500 font-bold">Interest Rate (APR)</p>
                    <p className="text-lg font-bold text-white mt-1">{report.interest_rate ? `${report.interest_rate}%` : 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wide text-neutral-500 font-bold">Decision Verdict</p>
                    <p className="text-lg font-bold text-white mt-1">{report.decision}</p>
                  </div>
                </div>
              </div>

            </div>

            {/* Signal Breakdowns per channel */}
            <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850">
              <p className="text-xs uppercase font-mono text-neutral-500 tracking-wider mb-6 font-bold">Alternate Channel score matrices</p>
              <div className="space-y-4">
                {Object.keys(report.breakdown).map((key) => {
                  const b = report.breakdown[key];
                  return (
                    <div key={key} className={`p-4 rounded-xl border ${b.consented ? 'bg-neutral-900 border-neutral-850' : 'bg-neutral-950/40 border-neutral-900 border-dashed text-neutral-500'}`}>
                      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
                        <div className="text-left">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-neutral-100 capitalize font-display">{key.replace("_", " ")}</span>
                            {b.consented && (
                              <span className="text-[10px] text-blue-400 font-mono bg-blue-950/30 border border-blue-500/20 px-1.5 py-0.5 rounded">
                                Weight: {b.weight_used}%
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-neutral-450 mt-1">{b.description}</p>
                        </div>
                        <div className="flex items-center gap-3 self-end sm:self-auto font-mono">
                          <span className={`text-xl font-extrabold ${b.score >= 80 ? 'text-emerald-400' : b.score >= 60 ? 'text-amber-400' : 'text-neutral-400'}`}>{b.score}/100</span>
                        </div>
                      </div>
                      <div className="w-full h-1.5 bg-neutral-800 rounded-full mt-3 relative overflow-hidden">
                        <div 
                          className={`absolute h-full rounded-full transition-all ${b.score >= 80 ? 'bg-emerald-500' : b.score >= 60 ? 'bg-amber-500' : 'bg-neutral-700'}`}
                          style={{ width: `${b.score}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-neutral-400 mt-3 flex items-start gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-neutral-500 mt-0.5 shrink-0" />
                        <span>{b.reason}</span>
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Explanation card */}
            <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 text-left">
              <p className="text-xs uppercase font-mono text-neutral-500 tracking-wider mb-3 font-bold">Explainable AI & Audit Summary</p>
              <p className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap font-sans">{report.explanation}</p>
            </div>

          </div>
        )}

      </div>

    </div>
  );

  function profileName(applicants: any[]) {
    // If customized
    return profile.name || user.name || user.email.split('@')[0];
  }
};

const DEMO_APPLICANTS = [
  { id: "demo-ravi-001", name: "Ravi Kumar" },
  { id: "demo-priya-002", name: "Priya Sharma" }
];
