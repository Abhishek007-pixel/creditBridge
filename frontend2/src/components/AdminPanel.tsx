import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { 
  Settings, Sliders, Shield, FileSpreadsheet, Download, Search, RefreshCw, 
  HelpCircle, AlertTriangle, ArrowRightLeft, Cpu 
} from 'lucide-react';

interface AdminPanelProps {
  user: { uid: string; email: string; role: 'applicant' | 'officer' | 'admin'; name?: string };
  onLogout: () => void;
}

export const AdminPanel: React.FC<AdminPanelProps> = ({ user, onLogout }) => {
  const [weights, setWeights] = useState<{ [key: string]: number }>({
    phone_bill: 25,
    cashflow: 20,
    psychometric: 20,
    geolocation: 15,
    ecommerce: 12,
    merchant: 8
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [savingWeights, setSavingWeights] = useState<boolean>(false);
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string>('');
  
  const [globalLogs, setGlobalLogs] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState({
    totalApplicants: 0,
    averageRating: 0,
    riskDistribution: [] as { name: string; value: number }[],
    consentPenetration: [] as { name: string; consented: number; unconsented: number }[]
  });

  // Calculate sum of current weights
  const weightsSum = (Object.values(weights) as number[]).reduce((a, b) => a + b, 0);

  // Sync current weights & Global stats/logs from Python backend
  useEffect(() => {
    const fetchAdminData = async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem('token');
        const headers = { 'Authorization': `Bearer ${token}` };

        // Two parallel calls: Python has separate /analytics and /weights endpoints
        const [analyticsRes, weightsRes, auditRes] = await Promise.all([
          fetch('/api/admin/analytics', { headers }),
          fetch('/api/admin/weights',   { headers }),
          fetch('/api/admin/audit',     { headers }),
        ]);

        if (analyticsRes.ok) {
          const ana = await analyticsRes.json();
          setAnalytics({
            totalApplicants: ana.total_applicants ?? 0,
            averageRating:   ana.average_score ?? 0,
            riskDistribution: Object.entries(ana.risk_distribution || {})
              .map(([name, value]) => ({ name, value: value as number })),
            consentPenetration: [],
          });
        }

        if (weightsRes.ok) {
          const wd = await weightsRes.json();
          if (wd.weights) {
            const pct: any = {};
            for (const k in wd.weights) pct[k] = Math.round(wd.weights[k] * 100);
            setWeights(pct);
          }
        }

        if (auditRes.ok) {
          const ad = await auditRes.json();
          setGlobalLogs(ad.logs || []);
        }

      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    
    fetchAdminData();
    const interval = setInterval(fetchAdminData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleWeightChange = (key: string, value: number) => {
    setWeights({ ...weights, [key]: value });
  };

  const handleSaveWeights = async () => {
    setErrorMsg('');
    setSuccessMsg('');

    if (weightsSum !== 100) {
      setErrorMsg(`Weights sum must exactly equal 100%. Current sum: ${weightsSum}%`);
      return;
    }

    setSavingWeights(true);
    try {
      // Norm weights config to decimal
      const normDecimal: any = {};
      for (const k in weights) {
        normDecimal[k] = weights[k] / 100;
      }
      const token = localStorage.getItem('token');
      await fetch('/api/admin/weights', {
        method: 'PUT',   // Python expects PUT, not POST
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ weights: normDecimal })
      });

      setSuccessMsg('Alternate channel agent scoring weights updated successfully!');
    } catch (e: any) {
      console.error(e);
      setErrorMsg(e.message || 'Error saving weights parameters.');
    } finally {
      setSavingWeights(false);
    }
  };

  const COLORS = ['#06b6d4', '#3b82f6', '#aa3bff', '#f59e0b', '#ef4444'];

  const triggerExportCSV = () => {
    if (globalLogs.length === 0) return;

    // Build plain string CSV (Slide 9 export directive check!)
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Action,Timestamp,Applicant UID,Metadata\n";
    
    globalLogs.forEach((log) => {
      let rawMetadata = "";
      if (log.metadata) {
        if (typeof log.metadata === 'object') {
          rawMetadata = JSON.stringify(log.metadata);
        } else {
          try {
            rawMetadata = JSON.stringify(JSON.parse(log.metadata));
          } catch (e) {
            rawMetadata = log.metadata;
          }
        }
      }
      const metadataStr = rawMetadata.replace(/"/g, '""');
      csvContent += `"${log.action}","${log.timestamp}","${log.applicant_id || ''}","${metadataStr}"\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `creditbridge_system_audit_trail_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link); // Required for FF
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex-grow flex flex-col justify-start max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 bg-neutral-900 border border-neutral-800 rounded-3xl shadow-xl mt-4 mb-12 text-left">
      
      {/* Title Header area */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-neutral-800 pb-5 mb-8 gap-4">
        <div className="font-display">
          <span className="text-xs uppercase font-mono tracking-widest text-[#3b82f6] font-bold">Security & Analytics Console</span>
          <h2 className="text-2xl font-black text-white mt-1">Admin Configuration Desk</h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs bg-neutral-800 border border-neutral-700/60 px-3.5 py-1.5 rounded-lg text-neutral-300 font-semibold flex items-center gap-1.5 font-mono">
            🔧 Role: System Admin
          </span>
          <button 
            onClick={onLogout}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-neutral-800 hover:bg-neutral-750 text-xs font-semibold text-neutral-300 hover:text-white rounded-lg border border-neutral-700 transition-colors cursor-pointer"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Admin stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8 text-left select-none">
        <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 hover:border-neutral-800 transition-all">
          <p className="text-[10px] text-neutral-500 font-mono uppercase tracking-wider font-bold">Evaluation Rate</p>
          <p className="text-3xl font-black text-white mt-1 font-display">{analytics.totalApplicants}</p>
        </div>
        <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 hover:border-neutral-800 transition-all">
          <p className="text-[10px] text-neutral-500 font-mono uppercase tracking-wider font-bold">System Average Rating</p>
          <p className="text-3xl font-black text-white mt-1 font-display">{analytics.averageRating} / 850</p>
        </div>
        <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 hover:border-neutral-800 transition-all">
          <p className="text-[10px] text-neutral-500 font-mono uppercase tracking-wider font-bold">Active Agency Models</p>
          <p className="text-3xl font-black text-emerald-500 mt-1 font-display">9 Agents</p>
        </div>
        <div className="bg-neutral-950/50 p-6 rounded-2xl border border-neutral-850 hover:border-neutral-800 transition-all">
          <p className="text-[10px] text-neutral-500 font-mono uppercase tracking-wider font-bold">Dynamic Audits Logged</p>
          <p className="text-3xl font-black text-blue-400 mt-1 font-display">{globalLogs.length}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        
        {/* Left Col: Weights Adjustment sliders box (Slide 9 & 8) */}
        <div className="lg:col-span-12 xl:col-span-5 flex flex-col">
          <div className="bg-neutral-950/50 rounded-2xl border border-neutral-850 p-6 flex-grow flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2 text-blue-400">
                <Sliders className="w-5 h-5 text-blue-500" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-display">Multi-Agent scoring weights</h3>
              </div>
              <p className="text-xs text-neutral-450 mb-6 leading-relaxed">System parameters to adjust the scoring influence of each alternate channel. Sum of all weights must exactly sum to 100%.</p>

              {errorMsg && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs rounded-xl mb-4 leading-relaxed font-bold">
                  {errorMsg}
                </div>
              )}

              {successMsg && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs rounded-xl mb-4 leading-relaxed font-bold">
                  {successMsg}
                </div>
              )}

              <div className="space-y-4">
                {Object.keys(weights).map((key) => (
                  <div key={key} className="space-y-1">
                    <div className="flex justify-between items-center text-xs">
                      <span className="capitalize font-semibold text-neutral-200">{key.replace("_", " ")}</span>
                      <span className="font-mono text-blue-400 font-bold">{weights[key]}%</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="1"
                        value={weights[key]}
                        onChange={(e) => handleWeightChange(key, parseInt(e.target.value))}
                        className="w-full accent-blue-500 bg-neutral-800 h-1.5 rounded-lg outline-none cursor-pointer"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="border-t border-neutral-850 pt-4 mt-6 flex items-center justify-between">
              <div className="text-xs">
                <p className="text-neutral-500 font-mono uppercase tracking-wide font-bold">Currently Configured:</p>
                <p className={`text-base font-extrabold mt-0.5 ${weightsSum === 100 ? 'text-blue-400' : 'text-rose-400'}`}>{weightsSum}% / 100%</p>
              </div>
              <button
                onClick={handleSaveWeights}
                disabled={savingWeights}
                className="px-5 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-505 text-white text-xs font-bold rounded-xl shadow-lg shadow-blue-900/10 active:scale-95 transition-all text-sm flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                {savingWeights ? 'Storing...' : 'Save Parameters'}
              </button>
            </div>

          </div>
        </div>

        {/* Right Col: Aggregate Charts & Auditing panel */}
        <div className="lg:col-span-12 xl:col-span-7 space-y-6 flex flex-col justify-between">
          
          {/* Recharts Analytics Charts Frame (Slide 9 & 8) */}
          <div className="bg-neutral-950/50 rounded-2xl border border-neutral-850 p-6">
            <p className="text-xs uppercase font-mono text-neutral-500 tracking-wider mb-4 font-bold">Pipeline Distribution Charts</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Piechart risk distribution */}
              <div className="bg-neutral-900 p-4 rounded-xl border border-neutral-850 flex flex-col items-center">
                <p className="text-[10px] text-neutral-400 font-mono uppercase mb-4 font-bold">Risk Stratification</p>
                {analytics.riskDistribution.length === 0 ? (
                  <p className="text-xs text-neutral-500 py-12">No data recorded yet.</p>
                ) : (
                  <div className="w-full h-44 flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={analytics.riskDistribution}
                          cx="50%"
                          cy="50%"
                          innerRadius={45}
                          outerRadius={70}
                          paddingAngle={3}
                          dataKey="value"
                        >
                          {analytics.riskDistribution.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={{ background: '#171717', border: '1px solid #262626', fontSize: '10px' }} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="flex flex-col text-left text-[10px] space-y-1 pl-2 font-mono">
                      {analytics.riskDistribution.map((entry, index) => (
                        <div key={entry.name} className="flex items-center gap-1">
                          <span className="w-2 h-2 rounded" style={{ backgroundColor: COLORS[index % COLORS.length] }}></span>
                          <span className="text-neutral-300 font-bold">{entry.name}: {entry.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Bar Chart consented path penetration */}
              <div className="bg-neutral-900 p-4 rounded-xl border border-neutral-850 flex flex-col items-center">
                <p className="text-[10px] text-neutral-400 font-mono uppercase mb-4 font-bold font-mono">Consented Channel Penetration</p>
                {analytics.totalApplicants === 0 ? (
                  <p className="text-xs text-neutral-500 py-12 font-mono">No data parameters available.</p>
                ) : (
                  <div className="w-full h-44">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.consentPenetration}>
                        <XAxis dataKey="name" stroke="#737373" fontSize={8} tickLine={false} />
                        <YAxis stroke="#737373" fontSize={8} tickLine={false} />
                        <Tooltip contentStyle={{ background: '#171717', border: '1px solid #262626', fontSize: '10px' }} />
                        <Bar dataKey="consented" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

            </div>
          </div>

          {/* Absolute Ledger trails display */}
          <div className="bg-neutral-950/50 rounded-2xl border border-neutral-850 p-6 flex-grow flex flex-col">
            <div className="flex justify-between items-center mb-4 pb-2 border-b border-neutral-850">
              <p className="text-xs uppercase font-mono text-neutral-500 tracking-wider font-bold">Immutable System Audit Trail</p>
              <button
                onClick={triggerExportCSV}
                className="px-3 py-1.5 bg-neutral-850 hover:bg-neutral-800 text-[10px] font-bold text-blue-400 border border-neutral-750 hover:text-blue-300 rounded flex items-center gap-1 transition-colors cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" /> Export ledger CSV
              </button>
            </div>

            <div className="space-y-1.5 flex-grow overflow-y-auto max-h-[300px] text-xs font-mono">
              {globalLogs.length === 0 ? (
                <p className="text-xs text-neutral-500 italic py-6 text-center">Ledger block registry is currently empty.</p>
              ) : (
                globalLogs.map((log, idx) => (
                  <div key={idx} className="flex justify-between items-start gap-4 py-2 border-b border-neutral-850">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded font-mono text-[9px] font-bold ${
                        log.action.includes('APPROVED') ? 'bg-emerald-500/10 text-emerald-400' :
                        log.action.includes('REJECTED') ? 'bg-rose-500/10 text-rose-400' :
                        log.action.includes('UPDATED') ? 'bg-blue-500/10 text-blue-400' :
                        'bg-neutral-800 text-neutral-400'
                      }`}>
                        {log.action}
                      </span>
                      <p className="text-[10px] text-neutral-400 truncate max-w-[200px]">
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
                      </p>
                    </div>
                    <span className="text-neutral-500 text-[9px] font-mono shrink-0">
                      {new Date(log.timestamp).toLocaleDateString()} {new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </span>
                  </div>
                ))
              )}
            </div>

          </div>

        </div>

      </div>

    </div>
  );
};
