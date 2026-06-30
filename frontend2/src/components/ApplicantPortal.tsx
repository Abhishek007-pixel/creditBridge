import React, { useState, useEffect } from 'react';
import { psychometricQuestions } from '../lib/questions';
import { ScoreReport } from '../lib/scoring';
import { 
  ShieldCheck, CheckCircle2, AlertCircle, FileText, ChevronRight, HelpCircle, 
  Settings, LogOut, Check, Smartphone, ShoppingBag, MapPin, Scale, Store, Landmark, Info,
  Plus, Trash, RefreshCw, Activity, CheckCircle, Clock
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
    cashflow: true,
    financial_commitment: true
  });

  const [answers, setAnswers] = useState<number[]>(new Array(10).fill(-1));
  const [loading, setLoading] = useState<boolean>(false);
  const [report, setReport] = useState<ScoreReport | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<number>(0);
  const [status, setStatus] = useState<'pending' | 'approved' | 'rejected' | 'none'>('pending');

  // --- Alternate Document & Sim State ---
  const [activeTabKey, setActiveTabKey] = useState<string>('');
  const [bills, setBills] = useState<any[]>([]);
  const [cashflows, setCashflows] = useState<any[]>([]);
  const [geolocations, setGeolocations] = useState<any>({ aadhaar_addresses: [], gps_verifications: [] });
  const [ecommerceInvoices, setEcommerceInvoices] = useState<any[]>([]);
  const [merchantData, setMerchantData] = useState<any>({ gstn_filings: [], merchant_references: [] });
  const [commitments, setCommitments] = useState<any[]>([]);

  // Simulation input states
  const [aaPhone, setAaPhone] = useState<string>('');
  const [aaBank, setAaBank] = useState<string>('SBI');
  const [gstin, setGstin] = useState<string>('');
  const [refName, setRefName] = useState<string>('');
  const [refPhone, setRefPhone] = useState<string>('');
  const [refRel, setRefRel] = useState<string>('supplier');
  const [refDuration, setRefDuration] = useState<number>(12);

  // Status logs for loaders
  const [gpsStatus, setGpsStatus] = useState<string>('');
  const [uploading, setUploading] = useState<boolean>(false);

  // --- Step 5 Processing Loader State ---
  const [activeAgentIdx, setActiveAgentIdx] = useState<number>(-1);
  const [processingLogs, setProcessingLogs] = useState<string[]>([]);
  const [agentStates, setAgentStates] = useState<{ [key: string]: 'idle' | 'running' | 'done' }>({
    credit_coordinator: 'idle',
    bill_consistency_agent: 'idle',
    commitment_agent: 'idle',
    cashflow_agent: 'idle',
    ecommerce_agent: 'idle',
    merchant_agent: 'idle',
    psychometric_agent: 'idle',
    risk_synthesizer: 'idle',
    score_explainer: 'idle',
  });

  const channels = [
    { key: "phone_bill", name: "Bill consistency history", weight: "20%", desc: "Measures rent receipts, electricity bills, gas, municipal taxes, and EMIs.", icon: <Smartphone className="w-5 h-5 text-indigo-400" /> },
    { key: "cashflow", name: "Bank Cashflow patterns", weight: "20%", desc: "Analyzes digital credit/debit logs, balance cushion and transaction failures.", icon: <Landmark className="w-5 h-5 text-indigo-400" /> },
    { key: "financial_commitment", name: "Financial Commitments", weight: "18%", desc: "Evaluates insurance premium payments, SIPs, recurring deposits, and chit funds.", icon: <Scale className="w-5 h-5 text-indigo-400" /> },
    { key: "geolocation", name: "Physical Geolocation stability", weight: "12%", desc: "Surrogates social rootedness, household history and flight risk indices.", icon: <MapPin className="w-5 h-5 text-indigo-400" /> },
    { key: "ecommerce", name: "E-commerce purchase behavior", weight: "10%", desc: "Evaluates prepaid usage ratios, product returns discipline and buyer age.", icon: <ShoppingBag className="w-5 h-5 text-indigo-400" /> },
    { key: "merchant", name: "Merchant ratings & trade ties", weight: "5%", desc: "Acquires supplier reliability logs and verified local trade standing.", icon: <Store className="w-5 h-5 text-indigo-400" /> },
  ];

  const activeTabs = [
    { key: 'phone_bill', label: 'Bills', name: 'Bill Consistency', desc: 'Rent receipt, electricity, gas, municipal tax, emi_receipt' },
    { key: 'cashflow', label: 'Cashflow', name: 'Bank Cashflow', desc: 'Account Aggregator feed or PDF statements' },
    { key: 'geolocation', label: 'Geolocation', name: 'GPS & Aadhaar', desc: 'Physical stability check and registered address scan' },
    { key: 'ecommerce', label: 'E-commerce', name: 'E-commerce Invoices', desc: 'Amazon, Flipkart, Local shop receipts' },
    { key: 'merchant', label: 'Merchant / GSTN', name: 'Business & References', desc: 'GSTIN tax filings, supplier/buyer trade references' },
    { key: 'financial_commitment', label: 'Savings', name: 'Financial Commitments', desc: 'LIC premiums, MF SIPs, chit fund statements' }
  ].filter(t => consents[t.key]);

  // Load profile + existing score
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
            decision: data.score.risk_category,
            loan_recommended: data.score.loan_recommended,
            interest_rate: data.score.interest_rate,
            weighted_average: data.score.final_score || 0,
            breakdown: data.score.breakdown || {},
            weights_used: data.score.weights_used || {},
            explanation: data.score.explanation
          });
          setStatus(data.score.status || 'pending');
          setStep(6); // directly to report if already scored
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchExistingData();
  }, [user.uid]);

  // Fetch document uploads on entering Step 3
  const fetchUploads = async () => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      if (consents.phone_bill) {
        const res = await fetch(`/api/bills/${user.uid}`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setBills(data.bills || []);
        }
      }
      if (consents.cashflow) {
        const res = await fetch(`/api/cashflow/${user.uid}`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setCashflows(data.statements || []);
        }
      }
      if (consents.geolocation) {
        const res = await fetch(`/api/geolocation/${user.uid}`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) setGeolocations(await res.json());
      }
      if (consents.ecommerce) {
        const res = await fetch(`/api/ecommerce/${user.uid}`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) setEcommerceInvoices(await res.json());
      }
      if (consents.merchant) {
        const res = await fetch(`/api/merchant/${user.uid}`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) setMerchantData(await res.json());
      }
      if (consents.financial_commitment) {
        const res = await fetch(`/api/commitments/${user.uid}`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) setCommitments(await res.json());
      }
    } catch (e) {
      console.error("Error loading uploads:", e);
    }
  };

  useEffect(() => {
    if (step === 3) {
      fetchUploads();
      if (activeTabs.length > 0 && !activeTabKey) {
        setActiveTabKey(activeTabs[0].key);
      }
    }
  }, [step]);

  const handleRegisterProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile.phone || !profile.aadhaar_last4) return;
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      await fetch('/api/register', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: profile.name,
          email: profile.email,
          phone: profile.phone,
          aadhaar_last4: profile.aadhaar_last4,
          uid: user?.uid,
        })
      });
      setStep(2);
    } catch (err) {
      console.error(err);
      setStep(2); 
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConsent = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
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
          financial_commitment: consents.financial_commitment
        })
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      setStep(3);
    }
  };

  // --- Document Upload API handler ---
  const handleUploadFile = async (endpoint: string, file: File, onSuccess: () => void) => {
    if (file.size > 5 * 1024 * 1024) {
      alert("File size exceeds 5MB limit. Please upload a smaller file.");
      return;
    }
    setUploading(true);
    const formData = new FormData();
    formData.append('applicant_id', user.uid);
    formData.append('file', file);
    const token = localStorage.getItem('token');

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed');
      }
      onSuccess();
    } catch (e: any) {
      alert(e.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // --- AA Link Simulator ---
  const handleLinkAA = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aaPhone) return;
    setUploading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/cashflow/simulate-aa', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          applicant_id: user.uid,
          phone_number: aaPhone,
          bank_name: aaBank
        })
      });
      if (res.ok) {
        alert("Bank account successfully linked via Account Aggregator simulator!");
        setAaPhone('');
        fetchUploads();
      } else {
        const d = await res.json();
        alert(d.detail || "AA connection failed");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setUploading(false);
    }
  };

  // --- GPS Reverse-Geocode Simulator ---
  const handleCaptureGPS = () => {
    setGpsStatus("Acquiring device GPS coordinates...");
    if (!navigator.geolocation) {
      setGpsStatus("Geolocation not supported by your browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setGpsStatus("Coordinates acquired! Synchronizing with alternate bureau...");
        try {
          const token = localStorage.getItem('token');
          const res = await fetch('/api/geolocation/verify-gps', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              applicant_id: user.uid,
              latitude: pos.coords.latitude,
              longitude: pos.coords.longitude
            })
          });
          const d = await res.json();
          if (res.ok) {
            setGpsStatus(`Verified! Resolved location: ${d.resolved_city} (PIN: ${d.resolved_pin_code})`);
            fetchUploads();
          } else {
            setGpsStatus(`GPS verify error: ${d.detail}`);
          }
        } catch (e: any) {
          setGpsStatus(`Error: ${e.message}`);
        }
      },
      (err) => {
        setGpsStatus(`Failed to acquire GPS: ${err.message}`);
      }
    );
  };

  // --- GSTN Simulator ---
  const handleLinkGST = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gstin) return;
    setUploading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/merchant/simulate-gst', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          applicant_id: user.uid,
          gstin: gstin,
          phone_number: profile.phone || '9876543210'
        })
      });
      if (res.ok) {
        alert("GSTN Tax filing successfully simulated!");
        setGstin('');
        fetchUploads();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setUploading(false);
    }
  };

  // --- Peer References Simulator ---
  const handleAddReference = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!refName || !refPhone) return;
    setUploading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/merchant/references', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          applicant_id: user.uid,
          references: [{
            reference_name: refName,
            phone: refPhone,
            relationship_type: refRel,
            duration_months: refDuration
          }]
        })
      });
      if (res.ok) {
        alert("Trade reference added successfully!");
        setRefName('');
        setRefPhone('');
        fetchUploads();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setUploading(false);
    }
  };

  const handleSelectAnswer = (qIdx: number, choiceIdx: number) => {
    const updated = [...answers];
    updated[qIdx] = choiceIdx;
    setAnswers(updated);
  };

  // --- Async Neuro SAN Scoring with Visual Agent Loader ---
  const handleTriggerScoring = async () => {
    setStep(5);
    setProcessingLogs(["[INFO] Handshaking with alternate credit bureau...", "[INFO] Resolving applicant consents and inputs..."]);
    setAgentStates({
      credit_coordinator: 'running',
      bill_consistency_agent: 'idle',
      commitment_agent: 'idle',
      cashflow_agent: 'idle',
      ecommerce_agent: 'idle',
      merchant_agent: 'idle',
      psychometric_agent: 'idle',
      risk_synthesizer: 'idle',
      score_explainer: 'idle',
    });

    // 1. Kickoff simulated pipeline logs animation
    const stages = [
      { name: "credit_coordinator", log: "[INFO] credit_coordinator orchestrating alternate scoring networks." },
      { name: "bill_consistency_agent", log: `[AGENT] bill_consistency_agent evaluating ${bills.length} uploaded utility/rent streams.` },
      { name: "commitment_agent", log: `[AGENT] commitment_agent checking ${commitments.length} savings/insurance documents.` },
      { name: "cashflow_agent", log: "[AGENT] cashflow_agent running bank transaction cash cushion matrix." },
      { name: "ecommerce_agent", log: `[AGENT] ecommerce_agent evaluating prepaid buy ratio and purchase records.` },
      { name: "merchant_agent", log: "[AGENT] merchant_agent validating GST return compliance and peer reference score." },
      { name: "psychometric_agent", log: "[AGENT] psychometric_agent scoring character integrity and moral indicators." },
      { name: "risk_synthesizer", log: "[SYNTHESIZER] risk_synthesizer dynamically normalizing consent-first scoring weights." },
      { name: "score_explainer", log: "[EXPLAINER] score_explainer generating plain language underwriting recommendations." }
    ];

    let currentStage = 0;
    const logInterval = setInterval(() => {
      if (currentStage < stages.length) {
        const stage = stages[currentStage];
        setAgentStates(prev => {
          const next = { ...prev };
          if (currentStage > 0) {
            next[stages[currentStage - 1].name] = 'done';
          }
          next[stage.name] = 'running';
          return next;
        });
        setProcessingLogs(prev => [...prev, stage.log]);
        currentStage++;
      } else {
        clearInterval(logInterval);
      }
    }, 1500);

    // 2. Fire actual Python Scoring endpoint
    try {
      const token = localStorage.getItem('token');
      
      // Save questionnaire response first
      await fetch('/api/questionnaire', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          applicant_id: user.uid,
          answers: answers
        })
      });

      const res = await fetch('/api/score', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          applicant_id: user.uid,
          questionnaire_answers: answers,
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Score API error ${res.status}`);
      }

      const resultReport = await res.json();
      
      // Make sure the logs animation finishes or transition
      setTimeout(() => {
        clearInterval(logInterval);
        setAgentStates({
          credit_coordinator: 'done',
          bill_consistency_agent: 'done',
          commitment_agent: 'done',
          cashflow_agent: 'done',
          ecommerce_agent: 'done',
          merchant_agent: 'done',
          psychometric_agent: 'done',
          risk_synthesizer: 'done',
          score_explainer: 'done',
        });
        
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
        setStep(6);
      }, Math.max(1000, 13500 - (currentStage * 1500))); // Let the user witness the premium animation for at least 8-13 seconds

    } catch (e: any) {
      clearInterval(logInterval);
      console.error('Score submission error:', e);
      alert(`Scoring failed: ${e.message}. Fallback applied.`);
      setStep(4);
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
          <span className="text-xs uppercase font-mono tracking-widest text-[#3b82f6] font-bold">Applicant Portal</span>
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
      {step < 6 && (
        <div className="grid grid-cols-5 gap-2 mb-8 select-none">
          {[
            { id: 1, label: "Register Profile" },
            { id: 2, label: "Alternate Consent" },
            { id: 3, label: "Data Uploads" },
            { id: 4, label: "Integrity Questions" },
            { id: 5, label: "AI Process" }
          ].map((s) => (
            <div 
              key={s.id} 
              className={`pb-2 border-b-2 text-center transition-all ${step === s.id ? 'border-blue-500 text-blue-400 font-bold' : step > s.id ? 'border-indigo-600 text-neutral-400 font-medium' : 'border-neutral-800 text-neutral-500'}`}
            >
              <p className="text-[10px] uppercase font-mono tracking-wider truncate">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Main Steps Content */}
      <div className="flex-grow text-left">
        
        {/* Step 1: Profile Registry form */}
        {step === 1 && (
          <form onSubmit={handleRegisterProfile} className="space-y-6">
            <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850">
              <h3 className="text-lg font-bold text-white mb-2 font-display">Step 1: Create Alternate Credit Profile</h3>
              <p className="text-sm text-neutral-400 mb-6">Confirm your personal identifiers. No formal credit history is required. All information is secured using AES-256 field encryption standards on the DB.</p>

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
          <div className="space-y-6">
            <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850">
              <div className="flex items-center gap-2 text-emerald-400 mb-2">
                <ShieldCheck className="w-5 h-5 text-emerald-500" />
                <h3 className="text-lg font-bold text-white font-display">Step 2: DPDP Consent-First Data Integration</h3>
              </div>
              <p className="text-sm text-neutral-400 mb-6 leading-relaxed">In accordance with India's <strong>Digital Personal Data Protection (DPDP) Act 2023</strong>, you hold absolute rights to select which data pipelines to integrate. CreditBridge will dynamically redistribute weights so that rejecting a channel never zeroizes your score!</p>

              <div className="space-y-3.5">
                {channels.map((ch) => (
                  <div 
                    key={ch.key}
                    onClick={() => setConsents({ ...consents, [ch.key]: !consents[ch.key] })}
                    className={`flex items-start gap-4 p-4 rounded-xl border transition-all cursor-pointer select-none ${consents[ch.key] ? 'bg-neutral-900 border-blue-500 shadow-md' : 'bg-neutral-950 border-neutral-850 text-neutral-500'}`}
                  >
                    <div className="mt-1">
                      {ch.icon}
                    </div>
                    <div className="flex-grow">
                      <div className="flex items-center justify-between">
                        <p className={`text-sm font-bold ${consents[ch.key] ? 'text-white' : 'text-neutral-500'}`}>{ch.name}</p>
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
              className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-bold shadow-lg active:scale-95 transition-all text-sm flex items-center justify-center gap-2 cursor-pointer"
            >
              Fulfill Document & Link Phase <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Step 3: Document Uploads & Simulator Integration Workspace */}
        {step === 3 && (
          <div className="space-y-6">
            <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850">
              <h3 className="text-lg font-bold text-white mb-2 font-display">Step 3: Alternative Document Upload & Verification</h3>
              <p className="text-sm text-neutral-400 mb-6">Link and upload evidence for your consented scoring channels. The AI agent network will parse these documents dynamically.</p>

              {activeTabs.length === 0 ? (
                <div className="text-center py-8 bg-neutral-900 border border-neutral-800 rounded-xl">
                  <p className="text-sm text-neutral-400">No alternate channels selected. You can proceed directly to behavioral questions.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                  
                  {/* Left list of tabs */}
                  <div className="md:col-span-4 space-y-2">
                    {activeTabs.map(tab => (
                      <button
                        key={tab.key}
                        onClick={() => setActiveTabKey(tab.key)}
                        className={`w-full text-left p-3.5 rounded-xl border text-xs font-semibold transition-all flex items-center justify-between cursor-pointer ${activeTabKey === tab.key ? 'bg-blue-600/10 border-blue-500 text-blue-400 font-bold' : 'bg-neutral-900 border-neutral-850 text-neutral-400 hover:bg-neutral-850'}`}
                      >
                        <span>{tab.label}</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    ))}
                  </div>

                  {/* Right tab panel contents */}
                  <div className="md:col-span-8 bg-neutral-900/60 p-5 rounded-2xl border border-neutral-800">
                    <p className="text-xs uppercase font-mono text-blue-400 font-bold mb-1">
                      {activeTabs.find(t => t.key === activeTabKey)?.name}
                    </p>
                    <p className="text-xs text-neutral-400 mb-5 leading-relaxed">
                      {activeTabs.find(t => t.key === activeTabKey)?.desc}
                    </p>

                    {/* DYNAMIC UPLOAD ZONES & FORMS */}

                    {/* 1. BILLS TAB */}
                    {activeTabKey === 'phone_bill' && (
                      <div className="space-y-4">
                        <div className="border border-dashed border-neutral-700 hover:border-blue-500 bg-neutral-950/40 p-6 rounded-xl text-center relative cursor-pointer">
                          <input 
                            type="file"
                            onChange={(e) => e.target.files && e.target.files[0] && handleUploadFile('/api/bills/upload', e.target.files[0], fetchUploads)}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            accept=".pdf,.jpg,.jpeg,.png,.csv,.xlsx,.txt"
                          />
                          <p className="text-2xl mb-1">📄</p>
                          <p className="text-xs text-neutral-200 font-semibold">Drop or Browse Utility Bills / Rent Receipts</p>
                          <p className="text-[10px] text-neutral-500 mt-2 font-mono">
                            Max size: 5MB | Formats: PDF, JPG, PNG, CSV, TXT | Limit: Up to 10 files
                          </p>
                        </div>

                        <div>
                          <p className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider mb-2 font-bold flex justify-between">
                            <span>Uploaded Bill Stream Registry</span>
                            <span>({bills.length} / 10 bills)</span>
                          </p>
                          <div className="space-y-1.5 max-h-[160px] overflow-y-auto">
                            {bills.length === 0 ? (
                              <p className="text-xs text-neutral-600 font-mono italic">No bill documents uploaded yet.</p>
                            ) : (
                              bills.map((b: any) => (
                                <div key={b._id} className="flex justify-between items-center p-2.5 bg-neutral-950/40 border border-neutral-850 rounded-lg text-xs font-mono">
                                  <span className="truncate max-w-[180px]">{b.original_filename}</span>
                                  <span className={`px-2 py-0.5 rounded text-[10px] ${b.stage === 'scored' ? 'bg-emerald-500/10 text-emerald-400' : b.stage === 'rejected' ? 'bg-rose-500/10 text-rose-400' : 'bg-amber-500/10 text-amber-400 animate-pulse'}`}>
                                    {b.stage}
                                  </span>
                                </div>
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 2. CASHFLOW TAB */}
                    {activeTabKey === 'cashflow' && (
                      <div className="space-y-4">
                        <div className="bg-neutral-950/40 p-4 rounded-xl border border-neutral-850">
                          <p className="text-xs font-bold text-white mb-2">Simulation: RBI Account Aggregator Link</p>
                          <form onSubmit={handleLinkAA} className="flex gap-2">
                            <input 
                              type="tel"
                              required
                              placeholder="Telem linked mobile: 9876543210"
                              value={aaPhone}
                              onChange={(e) => setAaPhone(e.target.value)}
                              className="bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-xs text-white outline-none flex-grow"
                            />
                            <select 
                              value={aaBank}
                              onChange={(e) => setAaBank(e.target.value)}
                              className="bg-neutral-900 border border-neutral-800 rounded-lg px-2 py-2 text-xs text-white outline-none"
                            >
                              <option value="SBI">SBI Bank</option>
                              <option value="UCO">UCO Bank</option>
                              <option value="HDFC">HDFC Bank</option>
                              <option value="ICICI">ICICI Bank</option>
                            </select>
                            <button type="submit" className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-xs font-bold text-white rounded-lg cursor-pointer">
                              Link A/c
                            </button>
                          </form>
                        </div>

                        <div className="border border-dashed border-neutral-700 bg-neutral-950/40 p-4 rounded-xl text-center relative cursor-pointer">
                          <input 
                            type="file"
                            onChange={(e) => e.target.files && e.target.files[0] && handleUploadFile('/api/cashflow/upload', e.target.files[0], fetchUploads)}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            accept=".pdf,.csv,.xlsx"
                          />
                          <p className="text-xl mb-1">🏦</p>
                          <p className="text-xs text-neutral-200 font-semibold">Or Upload Bank Statement PDF/CSV</p>
                          <p className="text-[10px] text-neutral-500 mt-1 font-mono">Max size: 5MB | Formats: PDF, CSV, XLSX | Limit: Max 5 statement files</p>
                        </div>

                        <div>
                          <p className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider mb-2 font-bold">Statement / Ledger Registry</p>
                          <div className="space-y-1.5 max-h-[100px] overflow-y-auto">
                            {cashflows.length === 0 ? (
                              <p className="text-xs text-neutral-600 font-mono italic">No offline statements loaded.</p>
                            ) : (
                              cashflows.map((c: any) => (
                                <div key={c._id} className="flex justify-between items-center p-2.5 bg-neutral-950/40 border border-neutral-850 rounded-lg text-xs font-mono">
                                  <span className="truncate max-w-[200px]">{c.original_filename || 'AA Connect Feed'}</span>
                                  <span className={`px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400`}>
                                    {c.stage || 'AA Connected'}
                                  </span>
                                </div>
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 3. GEOLOCATION TAB */}
                    {activeTabKey === 'geolocation' && (
                      <div className="space-y-4">
                        <div className="bg-neutral-950/40 p-4 rounded-xl border border-neutral-850">
                          <p className="text-xs font-bold text-white mb-2">Live Geolocation Verification</p>
                          <button 
                            type="button" 
                            onClick={handleCaptureGPS}
                            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white rounded-lg flex items-center justify-center gap-1.5 cursor-pointer"
                          >
                            <MapPin className="w-4 h-4" /> Share Browser HTML5 Location
                          </button>
                          {gpsStatus && (
                            <p className="text-[10px] font-mono text-amber-400 mt-2 leading-relaxed">{gpsStatus}</p>
                          )}
                        </div>

                        <div className="border border-dashed border-neutral-700 bg-neutral-950/40 p-4 rounded-xl text-center relative cursor-pointer">
                          <input 
                            type="file"
                            onChange={(e) => e.target.files && e.target.files[0] && handleUploadFile('/api/geolocation/upload-aadhaar', e.target.files[0], fetchUploads)}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            accept=".pdf,.jpg,.jpeg,.png"
                          />
                          <p className="text-xl mb-1">📇</p>
                          <p className="text-xs text-neutral-200 font-semibold">Upload Aadhaar Registered Address Scan (Back Page)</p>
                          <p className="text-[10px] text-neutral-500 mt-1 font-mono">Max size: 5MB | Formats: PDF, JPG, PNG | Limit: 1 back scan</p>
                        </div>

                        <div>
                          <p className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider mb-2 font-bold">Verification Audits</p>
                          <div className="space-y-1.5 text-xs font-mono">
                            {geolocations.aadhaar_addresses?.length > 0 && (
                              <div className="p-2.5 bg-neutral-950/40 border border-neutral-850 rounded-lg flex justify-between">
                                <span>📇 Aadhaar Address Document</span>
                                <span className="text-emerald-400 font-bold">✓ Uploaded</span>
                              </div>
                            )}
                            {geolocations.gps_verifications?.length > 0 && (
                              <div className="p-2.5 bg-neutral-950/40 border border-neutral-850 rounded-lg flex justify-between">
                                <span>📍 Live GPS Coordinates (lat, long)</span>
                                <span className="text-emerald-400 font-bold">✓ Captured</span>
                              </div>
                            )}
                            {(!geolocations.aadhaar_addresses?.length && !geolocations.gps_verifications?.length) && (
                              <p className="text-xs text-neutral-600 font-mono italic">No verification records found.</p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 4. E-COMMERCE TAB */}
                    {activeTabKey === 'ecommerce' && (
                      <div className="space-y-4">
                        <div className="border border-dashed border-neutral-700 bg-neutral-950/40 p-6 rounded-xl text-center relative cursor-pointer">
                          <input 
                            type="file"
                            onChange={(e) => e.target.files && e.target.files[0] && handleUploadFile('/api/ecommerce/upload', e.target.files[0], fetchUploads)}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            accept=".pdf,.jpg,.jpeg,.png,.txt"
                          />
                          <p className="text-2xl mb-1">🛒</p>
                          <p className="text-xs text-neutral-200 font-semibold">Upload Amazon/Flipkart Invoice PDF or Screenshots</p>
                          <p className="text-[10px] text-neutral-500 mt-2 font-mono">Max size: 5MB | Formats: PDF, JPG, PNG, TXT | Limit: Up to 10 invoices</p>
                        </div>

                        <div>
                          <p className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider mb-2 font-bold">Invoice registry ({ecommerceInvoices.length} invoices)</p>
                          <div className="space-y-1.5 max-h-[140px] overflow-y-auto">
                            {ecommerceInvoices.length === 0 ? (
                              <p className="text-xs text-neutral-600 font-mono italic">No e-commerce receipts uploaded.</p>
                            ) : (
                              ecommerceInvoices.map((inv: any) => (
                                <div key={inv._id} className="flex justify-between items-center p-2.5 bg-neutral-950/40 border border-neutral-850 rounded-lg text-xs font-mono">
                                  <span className="truncate max-w-[180px]">{inv.original_filename}</span>
                                  <span className={`px-2 py-0.5 rounded text-[10px] ${inv.stage === 'scored' ? 'bg-emerald-500/10 text-emerald-400' : inv.stage === 'rejected' ? 'bg-rose-500/10 text-rose-400' : 'bg-amber-500/10 text-amber-400 animate-pulse'}`}>
                                    {inv.stage}
                                  </span>
                                </div>
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 5. MERCHANT / GSTN TAB */}
                    {activeTabKey === 'merchant' && (
                      <div className="space-y-4 max-h-[350px] overflow-y-auto pr-1">
                        
                        {/* Simulation: GST Link */}
                        <div className="bg-neutral-950/40 p-4 rounded-xl border border-neutral-850">
                          <p className="text-xs font-bold text-white mb-2">GSTN filing Simulator</p>
                          <form onSubmit={handleLinkGST} className="flex gap-2">
                            <input 
                              type="text"
                              required
                              maxLength={15}
                              placeholder="15-character GSTIN (e.g. 27AAAAA1111A1Z1)"
                              value={gstin}
                              onChange={(e) => setGstin(e.target.value)}
                              className="bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-xs text-white outline-none flex-grow font-mono uppercase"
                            />
                            <button type="submit" className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-xs font-bold text-white rounded-lg cursor-pointer">
                              Sim Link
                            </button>
                          </form>
                        </div>

                        {/* GST tax receipt upload */}
                        <div className="border border-dashed border-neutral-700 bg-neutral-950/40 p-4 rounded-xl text-center relative cursor-pointer">
                          <input 
                            type="file"
                            onChange={(e) => e.target.files && e.target.files[0] && handleUploadFile('/api/merchant/upload-gst', e.target.files[0], fetchUploads)}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            accept=".pdf"
                          />
                          <p className="text-lg mb-1">🧾</p>
                          <p className="text-xs text-neutral-200 font-semibold">Upload GSTR Return PDF</p>
                          <p className="text-[10px] text-neutral-500 mt-1 font-mono">Max size: 5MB | Formats: PDF only | Limit: Up to 5 files</p>
                        </div>

                        {/* Peer References list */}
                        <div className="bg-neutral-950/40 p-4 rounded-xl border border-neutral-850 space-y-3">
                          <p className="text-xs font-bold text-white">Add Buyer / Supplier Trade References</p>
                          <form onSubmit={handleAddReference} className="grid grid-cols-2 gap-2">
                            <input 
                              type="text"
                              required
                              placeholder="Reference Name"
                              value={refName}
                              onChange={(e) => setRefName(e.target.value)}
                              className="bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-xs text-white outline-none"
                            />
                            <input 
                              type="tel"
                              required
                              maxLength={10}
                              placeholder="Mobile: 9812345678"
                              value={refPhone}
                              onChange={(e) => setRefPhone(e.target.value)}
                              className="bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-xs text-white outline-none font-mono"
                            />
                            <select 
                              value={refRel}
                              onChange={(e) => setRefRel(e.target.value)}
                              className="bg-neutral-900 border border-neutral-800 rounded-lg px-2 py-2 text-xs text-white outline-none"
                            >
                              <option value="supplier">Supplier relationship</option>
                              <option value="buyer">Buyer relationship</option>
                              <option value="peer">Local Peer rating</option>
                            </select>
                            <input 
                              type="number"
                              required
                              min={1}
                              placeholder="Duration (months)"
                              value={refDuration}
                              onChange={(e) => setRefDuration(parseInt(e.target.value))}
                              className="bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-xs text-white outline-none"
                            />
                            <button type="submit" className="col-span-2 py-2 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white rounded-lg cursor-pointer">
                              + Add Trade Reference
                            </button>
                          </form>
                        </div>

                        {/* List trade references + filings */}
                        <div>
                          <p className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider mb-2 font-bold">GST returns & references</p>
                          <div className="space-y-1.5 max-h-[100px] overflow-y-auto font-mono text-xs">
                            {merchantData.gstn_filings?.map((f: any) => (
                              <div key={f._id} className="flex justify-between items-center p-2.5 bg-neutral-950/40 border border-neutral-850 rounded-lg">
                                <span className="truncate max-w-[150px]">Filing: {f.original_filename || f.gstin}</span>
                                <span className="text-emerald-400">Scored</span>
                              </div>
                            ))}
                            {merchantData.merchant_references?.map((r: any) => (
                              <div key={r._id} className="flex justify-between items-center p-2.5 bg-neutral-950/40 border border-neutral-850 rounded-lg">
                                <span>👤 {r.reference_name} ({r.relationship_type})</span>
                                <span className="text-amber-400 capitalize">{r.verified_status}</span>
                              </div>
                            ))}
                            {(!merchantData.gstn_filings?.length && !merchantData.merchant_references?.length) && (
                              <p className="text-neutral-600 italic">No GST or peer records added.</p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 6. SAVINGS/COMMITMENT TAB */}
                    {activeTabKey === 'financial_commitment' && (
                      <div className="space-y-4">
                        <div className="border border-dashed border-neutral-700 bg-neutral-950/40 p-6 rounded-xl text-center relative cursor-pointer">
                          <input 
                            type="file"
                            onChange={(e) => e.target.files && e.target.files[0] && handleUploadFile('/api/commitments/upload', e.target.files[0], fetchUploads)}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            accept=".pdf,.jpg,.jpeg,.png,.txt"
                          />
                          <p className="text-2xl mb-1">🛡️</p>
                          <p className="text-xs text-neutral-200 font-semibold">Upload LIC Insurance Premium / Mutual Fund SIP / RD Statement</p>
                          <p className="text-[10px] text-neutral-500 mt-2 font-mono">Max size: 5MB | Formats: PDF, JPG, PNG, TXT | Limit: Up to 5 files</p>
                        </div>

                        <div>
                          <p className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider mb-2 font-bold">Commitments registry ({commitments.length} files)</p>
                          <div className="space-y-1.5 max-h-[140px] overflow-y-auto">
                            {commitments.length === 0 ? (
                              <p className="text-xs text-neutral-600 font-mono italic">No savings documents uploaded.</p>
                            ) : (
                              commitments.map((com: any) => (
                                <div key={com._id} className="flex justify-between items-center p-2.5 bg-neutral-950/40 border border-neutral-850 rounded-lg text-xs font-mono">
                                  <span className="truncate max-w-[180px]">{com.original_filename}</span>
                                  <span className={`px-2 py-0.5 rounded text-[10px] ${com.stage === 'scored' ? 'bg-emerald-500/10 text-emerald-400' : com.stage === 'rejected' ? 'bg-rose-500/10 text-rose-400' : 'bg-amber-500/10 text-amber-400 animate-pulse'}`}>
                                    {com.stage}
                                  </span>
                                </div>
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                  </div>

                </div>
              )}
            </div>

            <button
              onClick={() => setStep(4)}
              className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-bold shadow-lg active:scale-95 transition-all text-sm flex items-center justify-center gap-2 cursor-pointer"
            >
              Continue to Integrity Questions <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Step 4: Psychometric Integrity Questions (Character Assessment) */}
        {step === 4 && (
          <div className="space-y-6">
            <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850">
              <div className="flex items-center justify-between mb-4 border-b border-neutral-850 pb-4">
                <div className="flex items-center gap-2">
                  <HelpCircle className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-lg font-bold text-white font-display">Step 4: Character & Moral Integrity Assessment</h3>
                </div>
                <span className="text-xs font-mono font-bold text-blue-400 bg-neutral-900 border border-neutral-800 px-2.5 py-1 rounded-md">
                  Q {currentQuestion + 1} of 10
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full h-1.5 bg-neutral-800 rounded-full mb-6 relative overflow-hidden">
                <div 
                  className="absolute h-full bg-blue-500 transition-all animate-all"
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
                <p className="text-xs text-neutral-400 mt-2 italic flex items-center gap-1">
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
                          <p className={`text-xs mt-1 ${isSelected ? 'text-neutral-300' : 'text-neutral-450'}`}>{opt.description}</p>
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
                  onClick={handleTriggerScoring}
                  className="px-8 py-3.5 bg-gradient-to-r from-emerald-600 to-blue-600 hover:from-emerald-500 hover:to-blue-500 disabled:opacity-30 text-white rounded-xl text-sm font-bold shadow-lg active:scale-95 transition-all flex items-center gap-2 cursor-pointer"
                >
                  Generate Alternate score <ShieldCheck className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Step 5: Visual 9-Agent Neuro SAN Pipeline Processing Loader */}
        {step === 5 && (
          <div className="space-y-6 text-center py-6">
            <div className="max-w-md mx-auto">
              <span className="px-3 py-1 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs rounded-full font-mono uppercase tracking-widest font-bold">
                9-Agent Neuro SAN Scorer
              </span>
              <h3 className="text-xl font-bold text-white mt-3 font-display">Analyzing Risk Channels...</h3>
              <p className="text-xs text-neutral-400 mt-1 leading-relaxed">Each specialist agent is verifying your evidence. Consented weights normalize automatically.</p>
            </div>

            {/* Visual Agent Grid nodes */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 max-w-xl mx-auto my-8 select-none">
              {[
                { key: 'credit_coordinator', label: 'credit_coordinator', icon: '👑' },
                { key: 'bill_consistency_agent', label: 'bill_consistency_agent', icon: '📄' },
                { key: 'commitment_agent', label: 'commitment_agent', icon: '🛡️' },
                { key: 'cashflow_agent', label: 'cashflow_agent', icon: '🏦' },
                { key: 'ecommerce_agent', label: 'ecommerce_agent', icon: '🛒' },
                { key: 'merchant_agent', label: 'merchant_agent', icon: '🏬' },
                { key: 'psychometric_agent', label: 'psychometric_agent', icon: '🧠' },
                { key: 'risk_synthesizer', label: 'risk_synthesizer', icon: '⚖️' },
                { key: 'score_explainer', label: 'score_explainer', icon: '💬' }
              ].map((agent) => {
                const state = agentStates[agent.key] || 'idle';
                return (
                  <div 
                    key={agent.key} 
                    className={`p-3.5 rounded-xl border text-xs font-mono transition-all flex flex-col items-center justify-center gap-1.5 ${
                      state === 'running' ? 'bg-blue-600/15 border-blue-500 text-white shadow-lg shadow-blue-500/10 scale-105' :
                      state === 'done' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                      'bg-neutral-950/40 border-neutral-850 text-neutral-500'
                    }`}
                  >
                    <span className="text-lg">{agent.icon}</span>
                    <span className="font-bold truncate max-w-full">{agent.label}</span>
                    <span className="text-[9px] uppercase tracking-wider font-semibold opacity-85">
                      {state === 'running' ? '● executing...' : state === 'done' ? '✓ completed' : 'waiting'}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Terminal logs display */}
            <div className="max-w-xl mx-auto bg-neutral-950 border border-neutral-850 p-4 rounded-2xl text-left">
              <p className="text-[10px] text-neutral-500 uppercase font-mono tracking-widest mb-2 font-bold">
                Dynamic Agent System Console Logs
              </p>
              <div className="space-y-1.5 font-mono text-xs text-neutral-400 max-h-[140px] overflow-y-auto">
                {processingLogs.map((log, idx) => (
                  <p key={idx} className="leading-relaxed border-l-2 border-indigo-500/50 pl-2">
                    {log}
                  </p>
                ))}
                <div className="flex items-center gap-2 mt-2 pl-2">
                  <Activity className="w-3.5 h-3.5 text-blue-500 animate-pulse" />
                  <span className="text-[10px] text-blue-400 animate-pulse">Running alternative scoring pipeline...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 6: Final credit score rating report card */}
        {step === 6 && report && (
          <div className="space-y-8 print:bg-white print:text-black print:p-0">
            
            {/* Header info */}
            <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 flex flex-col md:flex-row justify-between items-center gap-4">
              <div className="text-left font-display">
                <span className="text-xs uppercase tracking-widest text-[#3b82f6] font-extrabold">Alternate Credit Rating Report</span>
                <h3 className="text-2xl font-black text-white mt-1">{profile.name || user.name || user.email.split('@')[0]}</h3>
                <p className="text-sm text-neutral-400 flex items-center gap-1.5 mt-1 font-mono">
                  ID: <span className="bg-neutral-900 border border-neutral-800 px-2 py-0.5 rounded text-neutral-300 select-all">{user.uid}</span>
                </p>
                <div className="flex items-center gap-2 mt-4 font-sans">
                  <span className={`px-2.5 py-1 text-xs font-bold rounded-lg ${
                    status === 'approved' ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' :
                    status === 'rejected' ? 'bg-rose-500/10 border border-rose-500/20 text-rose-450' :
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
                    'bg-rose-500/10 text-rose-450'
                  }`}>
                    {report.risk_category}
                  </span>
                </div>
              </div>

              {/* Loan Details Card */}
              <div className="md:col-span-12 xl:col-span-7 bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 flex flex-col justify-between">
                <div>
                  <span className="px-2.5 py-1 bg-blue-500/10 border border-blue-500/20 text-blue-450 text-[10px] uppercase font-mono tracking-wider rounded font-bold">Pre-Qualified Limit</span>
                  <p className="text-xs text-neutral-450 mt-1">Assessed micro-commission recommended loan structure.</p>
                  
                  <div className="mt-6 flex items-baseline gap-2 font-display">
                    <span className="text-4xl sm:text-5xl font-black text-white tracking-tight">
                      ₹{report.loan_recommended ? report.loan_recommended.toLocaleString("en-IN") : '0'}
                    </span>
                    <span className="text-sm font-mono text-neutral-500">INR Max Limit</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 border-t border-neutral-800 pt-6 mt-6 font-mono text-left">
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
                        </div>
                        <div className="flex items-center gap-3 self-end sm:self-auto font-mono">
                          <span className={`text-xl font-extrabold ${b.score >= 80 ? 'text-emerald-400' : b.score >= 60 ? 'text-amber-400' : 'text-neutral-500'}`}>{b.score}/100</span>
                        </div>
                      </div>
                      <div className="w-full h-1.5 bg-neutral-800 rounded-full mt-3 relative overflow-hidden">
                        <div 
                          className={`absolute h-full rounded-full transition-all ${b.score >= 80 ? 'bg-emerald-500' : b.score >= 60 ? 'bg-amber-500' : 'bg-neutral-700'}`}
                          style={{ width: `${b.score}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-neutral-450 mt-3 flex items-start gap-1">
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
};
