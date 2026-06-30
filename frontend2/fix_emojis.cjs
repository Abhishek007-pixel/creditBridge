const fs = require('fs');

function fixBankDashboard() {
  let content = fs.readFileSync('src/components/BankDashboard.tsx', 'utf8');

  // 1. Add imports
  content = content.replace(
    /import \{ evaluateCreditScore, ScoreReport \} from '\.\.\/lib\/scoring';/g,
    `import { evaluateCreditScore, ScoreReport } from '../lib/scoring';
import { useGSAP } from '@gsap/react';
import { initScrollAnimations, initHoverEffects } from '../lib/animations';`
  );

  // 2. Add useGSAP hook
  content = content.replace(
    /const \[auditLogs, setAuditLogs\] = useState<any\[\]>\(\[\]\);/g,
    `const [auditLogs, setAuditLogs] = useState<any[]>([]);

  useGSAP(() => {
    initScrollAnimations();
    initHoverEffects();
  }, [selectedApplicant, applicants]);`
  );

  // 3. Emoji replacements
  content = content.replace(/🔑 Role: Underwriter/g, '<Key className="w-4 h-4 text-neutral-500" /> Role: Underwriter');
  content = content.replace(/✓ Approved/g, '<CheckCircle className="w-3 h-3" /> Approved');
  content = content.replace(/✗ Rejected/g, '<X className="w-3 h-3" /> Rejected');
  content = content.replace(/● Verification/g, '<Activity className="w-3 h-3 animate-pulse" /> Verification');

  content = content.replace(
    /import \{\s*Users, Check, X, Search, FileText, Calendar, PieChart, Shield, CheckCircle,\s*Trash, ChevronRight, RefreshCw, Smartphone, ShoppingBag, MapPin, Store, Landmark, Scale\s*\} from 'lucide-react';/,
    `import { 
  Users, Check, X, Search, FileText, Calendar, PieChart, Shield, CheckCircle, 
  Trash, ChevronRight, RefreshCw, Smartphone, ShoppingBag, MapPin, Store, Landmark, Scale, Key, Activity 
} from 'lucide-react';`
  );

  content = content.replace(/<span className=\{\`text-\[10px\] uppercase font-bold font-mono tracking-wide \$\{/g, '<span className={`text-[10px] uppercase font-bold font-mono tracking-wide flex items-center justify-end gap-1 ${');

  content = content.replace(/\{a\.status === 'approved' \? '✓ Approved' : a\.status === 'rejected' \? '✗ Rejected' : '● Verification'\}/g, `{a.status === 'approved' ? <><CheckCircle className="w-3 h-3" /> Approved</> : a.status === 'rejected' ? <><X className="w-3 h-3" /> Rejected</> : <><Activity className="w-3 h-3 animate-pulse" /> Verification</>}`);

  fs.writeFileSync('src/components/BankDashboard.tsx', content);
}

function fixApplicantPortal() {
  let content = fs.readFileSync('src/components/ApplicantPortal.tsx', 'utf8');

  // 1. Add GSAP
  content = content.replace(
    /import \{ Button \} from '\.\/ui\/Button';/g,
    `import { Button } from './ui/Button';
import { useGSAP } from '@gsap/react';
import { initScrollAnimations, initHoverEffects } from '../lib/animations';`
  );

  content = content.replace(
    /const \[loading, setLoading\] = useState<boolean>\(false\);/g,
    `const [loading, setLoading] = useState<boolean>(false);

  useGSAP(() => {
    initScrollAnimations();
    initHoverEffects();
  }, [step]);`
  );

  // 2. Add Emoji Imports
  content = content.replace(
    /import \{\s*ShieldCheck, CheckCircle2, AlertCircle, FileText, ChevronRight, HelpCircle,\s*Settings, LogOut, Check, Smartphone, ShoppingBag, MapPin, Scale, Store, Landmark, Info,\s*Plus, Trash, RefreshCw, Activity, CheckCircle, Clock\s*\} from 'lucide-react';/g,
    `import { 
  ShieldCheck, CheckCircle2, AlertCircle, FileText, ChevronRight, HelpCircle, 
  Settings, LogOut, Check, Smartphone, ShoppingBag, MapPin, Scale, Store, Landmark, Info,
  Plus, Trash, RefreshCw, Activity, CheckCircle, Clock, Contact, IdCard, ShoppingCart, Receipt, User, Shield, Crown, Brain, MessageSquare
} from 'lucide-react';`
  );

  // 3. Emoji replacements
  content = content.replace(/<p className="text-2xl mb-1">📄<\/p>/g, '<FileText className="w-8 h-8 mb-2" />');
  content = content.replace(/<p className="text-xl mb-1">🏦<\/p>/g, '<Landmark className="w-6 h-6 mb-2" />');
  content = content.replace(/<p className="text-xl mb-1">📇<\/p>/g, '<Contact className="w-6 h-6 mb-2" />');

  content = content.replace(/<span>📇 Aadhaar Address Document<\/span>/g, '<span className="flex items-center gap-2"><IdCard className="w-4 h-4 text-neutral-500" /> Aadhaar Address Document</span>');
  content = content.replace(/<span className="text-emerald-400 font-bold">✓ Uploaded<\/span>/g, '<span className="text-emerald-500 font-bold flex items-center gap-1"><Check className="w-4 h-4" /> Uploaded</span>');
  content = content.replace(/<span>📍 Live GPS Coordinates \(lat, long\)<\/span>/g, '<span className="flex items-center gap-2"><MapPin className="w-4 h-4 text-neutral-500" /> Live GPS Coordinates (lat, long)</span>');
  content = content.replace(/<span className="text-emerald-400 font-bold">✓ Captured<\/span>/g, '<span className="text-emerald-500 font-bold flex items-center gap-1"><Check className="w-4 h-4" /> Captured</span>');

  content = content.replace(/<p className="text-2xl mb-1">🛒<\/p>/g, '<ShoppingCart className="w-8 h-8 mb-2" />');
  content = content.replace(/<p className="text-lg mb-1">🧾<\/p>/g, '<Receipt className="w-6 h-6 mb-2" />');
  content = content.replace(/<span>👤 \{r\.reference_name\} \(\{r\.relationship_type\}\)<\/span>/g, '<span className="flex items-center gap-2"><User className="w-4 h-4 text-neutral-500" /> {r.reference_name} ({r.relationship_type})</span>');
  content = content.replace(/<p className="text-2xl mb-1">🛡️<\/p>/g, '<Shield className="w-8 h-8 mb-2" />');

  content = content.replace(/\{ key: 'credit_coordinator', label: 'credit_coordinator', icon: '👑' \}/g, `{ key: 'credit_coordinator', label: 'credit_coordinator', icon: <Crown className="w-5 h-5 mb-1" /> }`);
  content = content.replace(/\{ key: 'bill_consistency_agent', label: 'bill_consistency_agent', icon: '📄' \}/g, `{ key: 'bill_consistency_agent', label: 'bill_consistency_agent', icon: <FileText className="w-5 h-5 mb-1" /> }`);
  content = content.replace(/\{ key: 'commitment_agent', label: 'commitment_agent', icon: '🛡️' \}/g, `{ key: 'commitment_agent', label: 'commitment_agent', icon: <Shield className="w-5 h-5 mb-1" /> }`);
  content = content.replace(/\{ key: 'cashflow_agent', label: 'cashflow_agent', icon: '🏦' \}/g, `{ key: 'cashflow_agent', label: 'cashflow_agent', icon: <Landmark className="w-5 h-5 mb-1" /> }`);
  content = content.replace(/\{ key: 'ecommerce_agent', label: 'ecommerce_agent', icon: '🛒' \}/g, `{ key: 'ecommerce_agent', label: 'ecommerce_agent', icon: <ShoppingCart className="w-5 h-5 mb-1" /> }`);
  content = content.replace(/\{ key: 'merchant_agent', label: 'merchant_agent', icon: '🏬' \}/g, `{ key: 'merchant_agent', label: 'merchant_agent', icon: <Store className="w-5 h-5 mb-1" /> }`);
  content = content.replace(/\{ key: 'psychometric_agent', label: 'psychometric_agent', icon: '🧠' \}/g, `{ key: 'psychometric_agent', label: 'psychometric_agent', icon: <Brain className="w-5 h-5 mb-1" /> }`);
  content = content.replace(/\{ key: 'risk_synthesizer', label: 'risk_synthesizer', icon: '⚖️' \}/g, `{ key: 'risk_synthesizer', label: 'risk_synthesizer', icon: <Scale className="w-5 h-5 mb-1" /> }`);
  content = content.replace(/\{ key: 'score_explainer', label: 'score_explainer', icon: '💬' \}/g, `{ key: 'score_explainer', label: 'score_explainer', icon: <MessageSquare className="w-5 h-5 mb-1" /> }`);

  content = content.replace(/<div className="text-2xl mb-1">\{agent\.icon\}<\/div>/g, '<div className="text-center">{agent.icon}</div>');

  content = content.replace(/\{state === 'running' \? '● executing\.\.\.' : state === 'done' \? '✓ completed' : 'waiting'\}/g, `{state === 'running' ? <span className="flex items-center justify-center gap-1"><Activity className="w-3 h-3 animate-pulse" /> executing...</span> : state === 'done' ? <span className="flex items-center justify-center gap-1"><Check className="w-3 h-3" /> completed</span> : 'waiting'}`);

  fs.writeFileSync('src/components/ApplicantPortal.tsx', content);
}

fixBankDashboard();
fixApplicantPortal();
