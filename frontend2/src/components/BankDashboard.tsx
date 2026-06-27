import React, { useState, useEffect } from 'react';
import { evaluateCreditScore, ScoreReport } from '../lib/scoring';
import { 
  Users, Check, X, Search, FileText, Calendar, PieChart, Shield, CheckCircle, 
  Trash, ChevronRight, RefreshCw, Smartphone, ShoppingBag, MapPin, Store, Landmark, Scale 
} from 'lucide-react';

interface BankDashboardProps {
  user: { uid: string; email: string; role: 'applicant' | 'officer' | 'admin'; name?: string };
  onLogout: () => void;
}

interface ApplicantRow {
  id: string;
  name: string;
  email: string;
  phone: string;
  aadhaar_last4: string;
  final_score?: number;
  risk_category?: string;
  loan_recommended?: number;
  interest_rate?: number;
  status?: 'pending' | 'approved' | 'rejected';
  scored_at?: string;
}

export const BankDashboard: React.FC<BankDashboardProps> = ({ user, onLogout }) => {
  const [applicants, setApplicants] = useState<ApplicantRow[]>([]);
  const [selectedApplicant, setSelectedApplicant] = useState<ApplicantRow | null>(null);
  const [reportData, setReportData] = useState<ScoreReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [search, setSearch] = useState<string>('');
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  // Real-time synchronization of applicants list (Mocked to fetch via interval)
  useEffect(() => {
    const fetchApplicants = async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem('token');
        // Fetch from Python backend (Vite proxy forwards /api/* to port 8000)
        const res = await fetch('/api/applicants', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          // Python returns { applicants: [...] } — extract the array
          setApplicants(Array.isArray(data) ? data : (data.applicants || []));
        } else {
          setApplicants([]);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    
    fetchApplicants();
    const interval = setInterval(fetchApplicants, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch applicant's alternative data and logs upon selection
  const handleSelectApplicant = async (app: ApplicantRow) => {
    setSelectedApplicant(app);
    setReportData(null);
    setAuditLogs([]);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`/api/applicants/${app.id}/score`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.score) {
          setReportData(data.score);
        }
        if (data.logs) {
          setAuditLogs(data.logs);
        }
        // Merge status from score into selectedApplicant
        if (data.score?.status) {
          setSelectedApplicant({ ...app, status: data.score.status });
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateStatus = async (applicantId: string, choice: 'approved' | 'rejected') => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/admin/applicants/${applicantId}/status`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ status: choice, decided_by: user.name || user.email })
      });

      // Update local state directly
      if (selectedApplicant && selectedApplicant.id === applicantId) {
        setSelectedApplicant({ ...selectedApplicant, status: choice });
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Search filtering
  const filteredApplicants = applicants.filter(a => 
    a.name.toLowerCase().includes(search.toLowerCase()) || 
    a.email.toLowerCase().includes(search.toLowerCase()) ||
    (a.risk_category && a.risk_category.toLowerCase().includes(search.toLowerCase()))
  );

  const pendingCount = applicants.filter(a => a.status === 'pending' && a.final_score).length;
  const approvedCount = applicants.filter(a => a.status === 'approved').length;

  return (
    <div className="flex-grow flex flex-col justify-start max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 bg-neutral-900 border border-neutral-800 rounded-3xl shadow-xl mt-4 mb-12">
      
      {/* Title Header area */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-neutral-800 pb-5 mb-8 gap-4">
        <div className="font-display">
          <span className="text-xs uppercase font-mono tracking-widest text-blue-400 font-bold">UCO Bank Officer Underwriting</span>
          <h2 className="text-2xl font-black text-white mt-1">Lending Review Terminal</h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs bg-neutral-800 border border-neutral-700/60 px-3.5 py-1.5 rounded-lg text-neutral-300 font-semibold flex items-center gap-1.5 font-mono">
            🔑 Role: Underwriter
          </span>
          <button 
            onClick={onLogout}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-neutral-800 hover:bg-neutral-750 text-xs font-semibold text-neutral-300 hover:text-white rounded-lg border border-neutral-700 transition-colors cursor-pointer"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Underwriting stats panel (Stunning 3-cell Bento grid) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8 text-left select-none">
        <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 hover:border-neutral-800 transition-all">
          <p className="text-[10px] text-neutral-500 font-mono uppercase tracking-wider font-bold">Total Registrants</p>
          <p className="text-3xl font-black text-white mt-1 font-display">{applicants.length}</p>
        </div>
        <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 hover:border-neutral-800 transition-all">
          <p className="text-[10px] text-neutral-500 font-mono uppercase tracking-wider font-bold">Needs Underwriting</p>
          <p className="text-3xl font-black text-amber-500 mt-1 font-display">{pendingCount}</p>
        </div>
        <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 hover:border-neutral-800 transition-all">
          <p className="text-[10px] text-neutral-500 font-mono uppercase tracking-wider font-bold">Disbursed Loans</p>
          <p className="text-3xl font-black text-emerald-500 mt-1 font-display">{approvedCount}</p>
        </div>
      </div>

      {/* Main Review Portal grid layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        
        {/* Left Col: Applicants list frame */}
        <div className="lg:col-span-5 flex flex-col">
          <div className="bg-neutral-950/50 rounded-2xl border border-neutral-850 p-4 flex-grow flex flex-col h-full min-h-[400px]">
            <p className="text-xs uppercase font-mono text-neutral-500 tracking-wider mb-3 text-left font-bold">Applicant Pipeline</p>
            
            {/* Search filter input */}
            <div className="relative mb-4">
              <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-neutral-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search name, email, risk band..."
                className="w-full bg-neutral-900 border border-neutral-800 focus:border-blue-500 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white transition-all outline-none"
              />
            </div>

            {/* List entries frame */}
            <div className="space-y-2 flex-grow overflow-y-auto max-h-[500px] text-left">
              {loading ? (
                <div className="text-center text-neutral-500 text-xs py-8">Synchronizing ledger...</div>
              ) : filteredApplicants.length === 0 ? (
                <div className="text-center text-neutral-500 text-xs py-12">No match records found.</div>
              ) : (
                filteredApplicants.map((a) => {
                  const isSelected = selectedApplicant?.id === a.id;
                  const hasScored = typeof a.final_score === 'number';
                  
                  return (
                    <div
                      key={a.id}
                      onClick={() => handleSelectApplicant(a)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer ${isSelected ? 'bg-blue-600/10 border-blue-500 shadow-md' : 'bg-neutral-900 border-neutral-850 hover:bg-neutral-850/50'}`}
                    >
                      <div className="flex justify-between items-center mb-2">
                        <p className="text-sm font-bold text-white truncate max-w-[150px]">{a.name}</p>
                        {hasScored ? (
                          <span className={`text-xs font-mono font-bold tracking-tight rounded px-1.5 py-0.5 ${
                            a.final_score! >= 750 ? 'bg-emerald-500/10 text-emerald-400' :
                            a.final_score! >= 650 ? 'bg-emerald-500/10 text-emerald-400' :
                            a.final_score! >= 550 ? 'bg-amber-500/10 text-amber-400' :
                            a.final_score! >= 450 ? 'bg-orange-500/10 text-orange-400' :
                            'bg-rose-500/10 text-rose-400'
                          }`}>
                            Score: {a.final_score}
                          </span>
                        ) : (
                          <span className="text-[10px] bg-neutral-800 text-neutral-400 font-mono px-2 py-0.5 rounded border border-neutral-700">Unscored</span>
                        )}
                      </div>
                      
                      <div className="flex justify-between items-end">
                        <p className="text-[10px] text-neutral-500 font-mono truncate max-w-[140px]">{a.email}</p>
                        {hasScored && (
                          <span className={`text-[10px] uppercase font-bold font-mono tracking-wide ${
                            a.status === 'approved' ? 'text-emerald-400' :
                            a.status === 'rejected' ? 'text-rose-400' :
                            'text-amber-500'
                          }`}>
                            {a.status === 'approved' ? '✓ Approved' : a.status === 'rejected' ? '✗ Rejected' : '● Verification'}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

          </div>
        </div>

        {/* Right Col: Score review detailing & Approve Reject panel */}
        <div className="lg:col-span-7 flex flex-col">
          {selectedApplicant ? (
            <div className="bg-neutral-950/50 rounded-2xl border border-neutral-850 p-6 flex flex-col h-full min-h-[400px] text-left">
              
              {/* Header card details */}
              <div className="border-b border-neutral-850 pb-4 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="font-display">
                  <span className="text-[10px] font-mono tracking-widest text-blue-400 uppercase font-black">Micro-loan Credit Audit</span>
                  <h3 className="text-xl font-bold text-white mt-1">{selectedApplicant.name}</h3>
                  <p className="text-xs text-neutral-500 font-mono mt-0.5">UID: {selectedApplicant.id}</p>
                </div>
                
                {/* One Click buttons block (Slide 8 element) */}
                {selectedApplicant.final_score && (
                  <div className="flex items-center gap-2 self-start sm:self-auto">
                    {selectedApplicant.status === 'pending' ? (
                      <>
                        <button
                          onClick={() => handleUpdateStatus(selectedApplicant.id, 'approved')}
                          className="px-3.5 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold rounded-lg flex items-center gap-1 shadow-md shadow-emerald-950/20 transition-all cursor-pointer"
                        >
                          <Check className="w-3.5 h-3.5" /> Approve
                        </button>
                        <button
                          onClick={() => handleUpdateStatus(selectedApplicant.id, 'rejected')}
                          className="px-3.5 py-2 bg-neutral-800 hover:bg-rose-600 text-neutral-200 hover:text-white text-xs font-bold rounded-lg hover:border-transparent border border-neutral-750 transition-all cursor-pointer"
                        >
                          <X className="w-3.5 h-3.5" /> Reject
                        </button>
                      </>
                    ) : (
                      <span className={`text-xs font-mono font-bold px-3 py-1.5 rounded-lg border ${
                        selectedApplicant.status === 'approved' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                      }`}>
                        Status: {selectedApplicant.status === 'approved' ? 'Loan Sanctioned' : 'Application Voided'}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Assessment detailing and subscores breakdowns */}
              {reportData ? (
                <div className="space-y-6 flex-grow overflow-y-auto max-h-[550px] pr-2">
                  
                  {/* Score gauge text details */}
                  <div className="grid grid-cols-2 gap-4 bg-neutral-900 border border-neutral-850 p-4 rounded-xl">
                    <div>
                      <p className="text-[10px] text-neutral-400 font-mono">Combined alternate score</p>
                      <p className="text-2xl font-black text-white mt-1 font-display">{selectedApplicant.final_score} / 850</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-neutral-400 font-mono">Assessed recommended limit</p>
                      <p className="text-2xl font-black text-blue-400 mt-1 font-display">₹{selectedApplicant.loan_recommended ? selectedApplicant.loan_recommended.toLocaleString("en-IN") : '0'}</p>
                    </div>
                  </div>

                  {/* 6 signals summaries listing */}
                  <div className="space-y-3.5">
                    <p className="text-[10px] text-neutral-500 font-mono uppercase tracking-wider font-bold">Alternate Data breakdown logs</p>
                    {Object.keys(reportData.breakdown).map((key) => {
                      const b = reportData.breakdown[key];
                      return (
                        <div key={key} className={`p-4 rounded-xl border transition-all ${b.consented ? 'bg-neutral-900 border-neutral-850' : 'bg-neutral-950/50 border-neutral-900 border-dashed opacity-50'}`}>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-xs font-bold text-white capitalize">{key.replace("_", " ")}</span>
                            <span className="text-xs font-mono text-blue-400 font-bold">{b.score}/100</span>
                          </div>
                          <p className="text-[10px] text-neutral-400 mt-1 italic leading-relaxed">{b.reason}</p>
                        </div>
                      );
                    })}
                  </div>

                  {/* Explanation audit summary */}
                  <div className="p-4 bg-neutral-900 p-5 rounded-xl border border-neutral-850">
                    <p className="text-xs uppercase font-mono text-neutral-500 tracking-wider mb-2 font-bold">Explainable AI Justification</p>
                    <p className="text-xs text-neutral-300 leading-relaxed whitespace-pre-wrap font-sans">{reportData.explanation}</p>
                  </div>

                  {/* Individual Applicant's Audit Log list */}
                  <div className="space-y-2 border-t border-neutral-850 pt-4">
                    <p className="text-xs uppercase font-mono text-neutral-500 tracking-wider mb-3 font-bold">Applicant Consent & Interaction History</p>
                    <div className="space-y-1.5">
                      {auditLogs.length === 0 ? (
                        <p className="text-xs text-neutral-500 italic">No historical traces in ledger yet.</p>
                      ) : (
                        auditLogs.map((log, idx) => (
                          <div key={idx} className="flex justify-between items-center py-2 border-b border-neutral-850 text-xs">
                            <div>
                              <span className="bg-neutral-800 text-neutral-300 px-2 py-0.5 rounded font-mono text-[10px] mr-2">
                                {log.action}
                              </span>
                              <span className="text-neutral-500 text-[10px] font-mono">
                                {(() => {
                                  if (!log.metadata) return "";
                                  if (typeof log.metadata === 'object') {
                                    return JSON.stringify(log.metadata);
                                  }
                                  try {
                                    return JSON.stringify(JSON.parse(log.metadata));
                                  } catch (e) {
                                    return log.metadata;
                                  }
                                })()}
                              </span>
                            </div>
                            <span className="text-neutral-500 text-[10px] font-mono">
                              {new Date(log.timestamp).toLocaleDateString()} {new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                </div>
              ) : (
                <div className="flex-grow flex flex-col justify-center items-center text-center text-neutral-500 py-12">
                  <RefreshCw className="w-8 h-8 animate-spin text-neutral-600 mb-2" />
                  <p className="text-xs font-semibold">Generating synthetic data models...</p>
                </div>
              )}

            </div>
          ) : (
            <div className="bg-neutral-950/30 rounded-2xl border border-neutral-850 p-8 flex flex-col justify-center items-center text-center text-neutral-500 h-full min-h-[460px]">
              <Users className="w-12 h-12 text-neutral-700 mb-3" />
              <h3 className="text-base font-bold text-neutral-400 font-display">Select Applicant profile</h3>
              <p className="text-xs text-neutral-500 max-w-sm mt-1 leading-normal">Choose an applicant from the registration pipeline on the left panel to review score justification breakdown and one-click sanctioning decision.</p>
            </div>
          )}
        </div>

      </div>

    </div>
  );
};
