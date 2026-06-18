# Survivor Detection Website Setup Guide

This Flask-based web application allows users to identify and provide information about unidentified survivors.

## 📋 Project Structure

```
myVerse/
├── web_server.py              # Flask web server (main entry point)
├── app.py                      # Backend detection logic (keep running separately)
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration
│
├── models/
│   ├── __init__.py
│   ├── user.py                 # User authentication model
│   └── survivor.py             # Survivor data model
│
├── templates/                  # HTML templates
│   ├── base.html              # Base template
│   ├── home.html              # Home page with survivors list
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── identify.html          # Survivor identification form
│   ├── survivor_detail.html   # Survivor details page
│   ├── dashboard.html         # User dashboard
│   ├── admin.html             # Admin dashboard
│   └── error.html             # Error page
│
├── static/
│   ├── css/
│   │   └── style.css          # Main stylesheet
│   ├── js/
│   │   └── script.js          # JavaScript functionality
│   └── images/                # Static images and assets
│
├── survivors/                 # Survivor images from detection
├── uploads/                   # User-uploaded files
├── reports/
│   ├── connection.py          # MongoDB connection
│   └── survivors.json         # Initial survivors data
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file with your MongoDB Atlas credentials:
```
MONGO_URI=your_mongodb_atlas_connection_string
SECRET_KEY=your_flask_secret_key
```

### 3. Run the Web Server

```bash
# Terminal 1: Run the web server
python web_server.py
```

The website will be available at `http://localhost:5000`

### 4. Keep Backend Detection Running

```bash
# Terminal 2: Keep your detection backend running
python app.py
```

## 📱 Features

### User Features
- **Register/Login**: Create account or log in
- **Browse Survivors**: View unidentified survivors with their photos
- **Provide Information**: Submit details about identified survivors
- **Dashboard**: Track your contributions and account information

### Admin Features
- **Statistics Dashboard**: View overall rescue operation stats
- **Survivor Management**: View identified and unidentified survivors
- **Search & Filter**: Find survivors by ID, name, or contact info
- **Verification System**: Verify submitted information

## 🔐 Authentication

The system uses:
- **Password Hashing**: bcrypt for secure password storage
- **Session Management**: Flask-Login for user sessions
- **Database-backed**: MongoDB for storing user credentials

## 📊 Database Schema

### Users Collection
```json
{
  "_id": ObjectId,
  "username": "string",
  "email": "string",
  "password_hash": "bytes",
  "created_at": "datetime",
  "contributions": "integer",
  "is_admin": "boolean"
}
```

### Survivors Collection
```json
{
  "_id": ObjectId,
  "survivor_id": "string",
  "image": "string (path)",
  "latitude": "float",
  "longitude": "float",
  "direction": "string",
  "posture": "string",
  "confidence": "float",
  "identified": "boolean",
  "identification": {
    "name": "string",
    "phone": "string",
    "email": "string",
    "address": "string",
    "notes": "string",
    "identified_by_user_id": ObjectId,
    "identified_at": "datetime",
    "verified": "boolean"
  },
  "created_at": "datetime",
  "last_updated": "datetime",
  "verified": "boolean"
}
```

## 🛠️ Admin Setup

### Create Admin User

```bash
python web_server.py
# Then run in Flask shell:
flask create-admin-user
```

### Migrate Existing Survivor Data

If you have survivors in `reports/survivors.json`:

```bash
flask migrate-survivors-json
```

## 🌐 API Endpoints

- `GET /` - Home page
- `GET /survivor/<id>` - Survivor details
- `POST /login` - User login
- `POST /register` - User registration
- `POST /identify/<id>` - Submit survivor information
- `GET /dashboard` - User dashboard
- `GET /admin` - Admin dashboard
- `GET /api/survivors/unidentified` - API: Get unidentified survivors
- `GET /api/stats` - API: Get statistics

## 🎨 Customization

After you provide screenshots, we can update:
- Colors and styling in `static/css/style.css`
- Layout and templates in `templates/`
- Logo and branding images in `static/images/`

## 📝 Important Notes

⚠️ **Before Production:**
1. Change `SECRET_KEY` in `.env` to a secure random string
2. Set `FLASK_ENV=production`
3. Use HTTPS/SSL certificate
4. Implement rate limiting
5. Add logging and monitoring

## 🐛 Troubleshooting

### MongoDB Connection Issues
- Verify connection string in `.env`
- Check IP whitelist in MongoDB Atlas
- Ensure network connectivity

### Port Already in Use
```bash
# Change port in web_server.py or .env
PORT=5001
```

### Module Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📞 Support

For issues or questions:
1. Check the error logs
2. Verify MongoDB connection
3. Ensure all dependencies are installed

---

**Ready to go live?** Contact the development team for deployment guidance.
