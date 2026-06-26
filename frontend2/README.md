<div align="center">
<h1>CreditBridge</h1>
<p>Alternate Credit Scoring System</p>
</div>

## Getting Started

Follow these steps to run the application locally. Since this is a full-stack application, you need to run both the Node.js backend server and the React frontend simultaneously in two separate terminals.

### Prerequisites
- Node.js installed

### 1. Install Dependencies
Open a terminal in the project directory and install the necessary packages:
```bash
npm install
```

### 2. Configure Environment Variables
Ensure you have a `.env` file in the root directory. It should contain your database URL and JWT secret:
```env
MONGODB_URI="mongodb+srv://..."
JWT_SECRET="your_secret_key"
```

### 3. Start the Backend Server (Terminal 1)
Open a terminal in the project root and run the Node.js API server:
```bash
node server.js
```
*The backend should start and log `Server running on port 3001` and `Connected to MongoDB Atlas`.*

### 4. Start the Frontend (Terminal 2)
Open a **new, separate terminal** in the project root and run the React application:
```bash
npx vite --port 3004 --host 0.0.0.0 
```
*The frontend will start. Open the `localhost` URL provided in the terminal (usually `http://localhost:3000`) in your browser.*

### Quick Demo Testing
Once everything is running, use the **Quick Demo Access** buttons at the bottom of the Login page to instantly test the Applicant, Bank Officer, and Admin dashboards!
