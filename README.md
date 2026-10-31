# Smart Community — Digital Neighborhood & Services Marketplace

A modern, full-stack community management platform and service marketplace connecting neighborhood residents and service providers (Electricians, Plumbers, AC Repair Technicians, Cleaners, and more).

## 🌟 Key Features
- **Community Services Marketplace**: Browse verified local trade professionals with transparent pricing, reviews, and ratings.
- **Dual Portal Registration**: Register either as a **Customer** (Service Required) or as a **Service Provider** (Seller Partner).
- **Instant 1-Click Booking**: Customer checkout drawer with time slots, address, and live order tracking.
- **Order Tracking**: 4-stage live technician dispatch tracker (`Confirmed` → `Dispatched` → `In Progress` → `Completed`).
- **Seller Central**: Dedicated Provider Dashboard with real-time customer leads, dispatch management, and metrics.
- **Mutual 2-Way Reviews**: Both customers and providers can review each other to build transparent community trust scores.
- **OTP Security**: Email-based OTP verification for secure resident authentication.

---

## 🚀 Running Locally

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd <repo-folder>
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables (optional):**
   Copy `.env.example` to `.env` and fill in credentials:
   ```bash
   cp .env.example .env
   ```

4. **Start the application:**
   ```bash
   python app.py
   ```
   Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## 🌐 Deploying to Render

### Option 1: Automatic Blueprint (Recommended)
1. Push this repository to GitHub.
2. Sign in to [Render.com](https://render.com/).
3. Click **New +** → **Blueprint**.
4. Select your GitHub repository.
5. Render will detect `render.yaml` automatically and configure the build & start commands!
6. In **Environment Variables**, optionally set:
   - `EMAIL_ADDRESS`: Your Gmail address for sending OTPs
   - `EMAIL_PASSWORD`: Your Gmail App Password

### Option 2: Manual Web Service
1. On Render, click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Set the following settings:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Under **Advanced** → **Add Environment Variable**:
   - `PYTHON_VERSION`: `3.11.9`
   - `SECRET_KEY`: (any random string)
   - `EMAIL_ADDRESS`: (your Gmail address)
   - `EMAIL_PASSWORD`: (your Gmail App Password)
5. Click **Create Web Service**. Your app will be live with a free `https://<app-name>.onrender.com` URL!

---

## 🔑 Default Accounts (For Testing)
- **Administrator**: `admin` / `admin123`
- **Electrician Pro**: `ganesh_electrician` / `ganesh123`
- **AC Repair Pro**: `amit_acrepair` / `amit123`
- **Customer**: `rohit` / `rohit123`
