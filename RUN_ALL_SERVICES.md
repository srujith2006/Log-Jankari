# Running All Services Together

## 🎯 Quick Answer

**YES, all three run simultaneously without interference:**
- ✅ `gps_server.py` (GPS on Port 8888)
- ✅ `app.py` (Video detection + survivor detection)
- ✅ `web_server.py` (Website on Port 5000)

They communicate through **MongoDB**, not directly with each other.

---

## 🚀 Easiest Way: One-Click Start

### **Windows**
Double-click: `start_all.bat`

This will:
1. Open GPS Server in Window 1
2. Open Detection Backend in Window 2
3. Open Web Server in Window 3 + Browser

All 3 run simultaneously!

### **Linux/Mac**
```bash
chmod +x start_all.sh
./start_all.sh
```

---

## 📋 Manual: Run Each in Separate Terminal

If you prefer manual control:

### **Terminal 1 - GPS Server**
```bash
python gps_server.py
# Output: GPS server running on port 8888
```

### **Terminal 2 - Detection Backend**
```bash
python app.py
# Output: Processing video from mobile
#         Detecting survivors
#         Saving to MongoDB
```

### **Terminal 3 - Web Server**
```bash
python web_server.py
# Output: Running on http://localhost:5000
```

---

## 🔄 How They Work Together

```
Mobile Device (Video Stream)
        ↓
    app.py (Detection)
        ↓
   MongoDB Database ← MongoDB stores data
        ↑          ↓
        └─ web_server.py (Website displays it)
        
GPS Server
    ↓
app.py (Uses GPS location data)
    ↓
MongoDB
    ↓
web_server.py (Shows location on map)
```

### **Data Flow:**
1. **Mobile sends video** → `app.py` processes it
2. **app.py detects survivors** → Saves to MongoDB
3. **Web server queries MongoDB** → Displays on website
4. **GPS data** → app.py uses it, stored in MongoDB
5. **Users identify survivors** → Web server updates MongoDB
6. **Admin sees everything** → Real-time updates

---

## 💻 Technical Details

### **Port Usage**
| Service | Port | URL |
|---------|------|-----|
| GPS Server | 8888 | `localhost:8888` |
| Web Server | 5000 | `http://localhost:5000` |
| Detection Backend | - | Background process |

### **Process Management**
- Each service is **independent**
- They don't wait for each other
- Stopping one doesn't stop others
- You can restart them individually

### **Database Synchronization**
```
All services ←→ MongoDB Atlas
       ↓
   Shared data (Survivors, Users, Locations)
```

---

## ✅ Start Sequence

```
1. start_all.bat/sh (or start each manually)
   ↓
2. GPS Server starts (Port 8888) - waits for location requests
   ↓
3. Detection Backend starts (app.py) - waits for video
   ↓
4. Web Server starts (Port 5000) - ready for users
   ↓
5. All three now run simultaneously
   ↓
6. Mobile sends video → Detection processes → Website updates in real-time
```

**Total startup time:** ~5-10 seconds

---

## 📊 Status Check

### **How to Know All are Running:**

**Windows:**
- You see 3 command windows open
- Each shows service-specific logs

**Browser:**
- Open `http://localhost:5000`
- You see the website loading
- Unidentified survivors displayed

**Check Ports:**
```bash
# Windows
netstat -ano | findstr "5000\|8888"

# Linux/Mac
lsof -i :5000,8888
```

---

## 🎬 Typical Operation Flow

### **At Startup:**
```
1. Run: python start_all.bat (or start_all.sh)
2. Wait 5-10 seconds for all services to start
3. Browser opens http://localhost:5000
4. Website ready for users
```

### **During Operation:**
```
Mobile → Video Stream → app.py → MongoDB
                           ↓
Website queries MongoDB → Shows survivors
```

### **User Interaction:**
```
User identifies survivor → Submits form → web_server.py → MongoDB
                                                    ↓
                    Admin dashboard updates automatically
```

---

## ⚠️ Troubleshooting

### **"Port 5000 already in use"**
```bash
# Stop other services using port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### **MongoDB Connection Failed**
- Check `.env` file has correct connection string
- Verify IP whitelist in MongoDB Atlas
- Check internet connectivity

### **One service crashes**
- Restart just that service in its terminal
- Other services keep running
- Data in MongoDB remains intact

### **Video not detected**
- Verify mobile is sending to correct URL
- Check `app.py` is running
- Check MongoDB connection

---

## 🛑 Stopping Services

### **Graceful Shutdown:**
- Press `Ctrl+C` in each terminal

### **Force Kill:**
```bash
# Windows
taskkill /F /IM python.exe

# Linux/Mac
pkill -9 python
```

---

## 📈 Performance Considerations

### **Resource Usage (Typical):**
- GPS Server: ~10 MB RAM, minimal CPU
- Detection Backend: ~500 MB RAM (with video), high CPU during detection
- Web Server: ~100 MB RAM, minimal CPU
- Total: ~600 MB RAM, varies with activity

### **Optimization:**
- All 3 can run on same machine
- Or distribute across multiple machines (update MongoDB connection)
- Auto-restart if crashes (consider supervisor/systemd)

---

## 🚀 Production Setup

For long-running deployment:

### **Option 1: Supervisor (Linux)**
```bash
sudo apt install supervisor
# Create config files for each service
# Auto-restart on crash
```

### **Option 2: Docker**
```bash
docker-compose up -d
# All services in containers
# Easy to manage and scale
```

### **Option 3: System Services (Linux)**
```bash
sudo systemctl enable myverse-app
sudo systemctl start myverse-app
# Auto-start on boot
```

### **Option 4: Task Scheduler (Windows)**
```
Create scheduled tasks for each service
Auto-start on system boot
```

---

## 📝 Summary

| Aspect | Details |
|--------|---------|
| **Can all 3 run together?** | ✅ Yes, simultaneously |
| **Do they interfere?** | ❌ No, they use MongoDB for communication |
| **Easy start?** | ✅ Yes, use `start_all.bat` or `start_all.sh` |
| **Manual start?** | ✅ Yes, 3 terminals, one for each |
| **Communication** | MongoDB (shared database) |
| **Real-time updates?** | ✅ Yes, website updates as survivors detected |
| **Can stop individually?** | ✅ Yes, other services keep running |

---

## 🎯 What You Get

```
✅ Video processing (24/7 if needed)
✅ GPS location tracking (continuous)
✅ Website running (accept user input)
✅ Database updates (real-time)
✅ Admin dashboard (live statistics)
✅ All simultaneously without conflicts
```

**Just run `start_all.bat` (Windows) or `start_all.sh` (Linux/Mac) and everything works!** 🎉
