import express from 'express';
import mongoose from 'mongoose';
import cors from 'cors';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import 'dotenv/config';

const app = express();
app.use(cors());
app.use(express.json());

const MONGODB_URI = process.env.MONGODB_URI;
const JWT_SECRET = process.env.JWT_SECRET;

mongoose.connect(MONGODB_URI)
  .then(() => console.log('Connected to MongoDB Atlas'))
  .catch(err => console.error('MongoDB connection error:', err));

// --- SCHEMAS ---
const userSchema = new mongoose.Schema({
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
  role: { type: String, default: 'applicant' },
  name: String,
});
const User = mongoose.model('User', userSchema);

const applicantSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  name: String,
  email: String,
  phone: String,
  aadhaar_last4: String,
  aadhaar_hash: String,
});
const Applicant = mongoose.model('Applicant', applicantSchema);

const scoreSchema = new mongoose.Schema({
  applicant_id: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  final_score: Number,
  risk_category: String,
  decision: String,
  loan_recommended: Number,
  interest_rate: Number,
  explanation: String,
  breakdown: Object,
  weights_used: Object,
  status: { type: String, default: 'pending' },
});
const Score = mongoose.model('Score', scoreSchema);

// --- MIDDLEWARE ---
const authMiddleware = (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'No token provided' });
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

// --- ROUTES ---
app.post('/api/auth/register', async (req, res) => {
  try {
    const { email, password, role, name } = req.body;
    const existing = await User.findOne({ email });
    if (existing) return res.status(400).json({ error: 'User already exists' });
    
    const hashedPassword = await bcrypt.hash(password, 10);
    const user = new User({ email, password: hashedPassword, role: role || 'applicant', name });
    await user.save();
    
    const token = jwt.sign({ uid: user._id, email: user.email, role: user.role }, JWT_SECRET);
    res.json({ token, user: { uid: user._id, email: user.email, role: user.role } });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    const user = await User.findOne({ email });
    if (!user) return res.status(400).json({ error: 'Invalid credentials' });
    
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) return res.status(400).json({ error: 'Invalid credentials' });
    
    const token = jwt.sign({ uid: user._id, email: user.email, role: user.role }, JWT_SECRET);
    res.json({ token, user: { uid: user._id, email: user.email, role: user.role } });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/me', authMiddleware, async (req, res) => {
  try {
    const applicant = await Applicant.findOne({ userId: req.user.uid });
    const score = await Score.findOne({ applicant_id: req.user.uid });
    res.json({ applicant, score });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/applicants', authMiddleware, async (req, res) => {
  try {
    const data = req.body;
    let applicant = await Applicant.findOne({ userId: req.user.uid });
    if (applicant) {
      Object.assign(applicant, data);
    } else {
      applicant = new Applicant({ ...data, userId: req.user.uid });
    }
    await applicant.save();
    res.json(applicant);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/scores', authMiddleware, async (req, res) => {
  try {
    const data = req.body;
    const score = new Score({ ...data, applicant_id: req.user.uid });
    await score.save();
    res.json(score);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// --- ADMIN/OFFICER ROUTES ---
app.get('/api/admin/applicants', authMiddleware, async (req, res) => {
  try {
    const applicants = await Applicant.find();
    const scores = await Score.find();
    
    const results = applicants.map(app => {
      const score = scores.find(s => s.applicant_id.toString() === app.userId.toString());
      return {
        id: app.userId,
        name: app.name,
        email: app.email,
        phone: app.phone,
        aadhaar_last4: app.aadhaar_last4,
        final_score: score?.final_score,
        risk_category: score?.risk_category,
        loan_recommended: score?.loan_recommended,
        interest_rate: score?.interest_rate,
        status: score?.status || 'pending'
      };
    });
    res.json(results);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/admin/applicants/:id', authMiddleware, async (req, res) => {
  try {
    const score = await Score.findOne({ applicant_id: req.params.id });
    // Audit logs mock for now
    res.json({ score, logs: [] });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/admin/applicants/:id/status', authMiddleware, async (req, res) => {
  try {
    await Score.findOneAndUpdate({ applicant_id: req.params.id }, { status: req.body.status });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

let globalWeights = { phone_bill: 25, cashflow: 20, psychometric: 20, geolocation: 15, ecommerce: 12, merchant: 8 };

app.get('/api/admin/data', authMiddleware, async (req, res) => {
  try {
    const scores = await Score.find();
    const analytics = {
      totalApplicants: scores.length,
      averageRating: scores.length ? Math.round(scores.reduce((sum, s) => sum + (s.final_score || 0), 0) / scores.length) : 0,
      riskDistribution: [],
      consentPenetration: []
    };
    res.json({ weights: globalWeights, logs: [], analytics });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/admin/weights', authMiddleware, (req, res) => {
  globalWeights = req.body.weights;
  res.json({ success: true });
});

const PORT = 3001;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
