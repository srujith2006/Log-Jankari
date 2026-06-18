# 🚀 QUICK START GUIDE - Run Everything

## **TL;DR - Windows Users**

Just double-click this file:
```
d:\myVerse\start_all.bat
```

That's it! Everything starts automatically.

---

## **TL;DR - Linux/Mac Users**

```bash
cd d/myVerse
chmod +x start_all.sh
./start_all.sh
```

---

## 📊 What Happens When You Run start_all

```
start_all.bat / start_all.sh
        ↓
    ┌───┴───┬─────────┬──────────────┐
    ↓       ↓         ↓              ↓
GPS Server  app.py    web_server.py  Browser Opens
(Port 8888) (Detection) (Port 5000)  (auto)
    ↓       ↓         ↓
    └───────┴─────────┴──→ MongoDB Atlas
                            (Shared Database)
```

All 3 run at the same time ✅

---

## 🎯 Access Your Services

Once everything starts:

| Service | Access | Purpose |
|---------|--------|---------|
| **Website** | http://localhost:5000 | Register, identify survivors, admin dashboard |
| **GPS Server** | localhost:8888 | Location data (automatic) |
| **Detection** | Background | Video processing (automatic) |

---

## 📱 How Mobile Video Works

```
Your Mobile Device
        ↓
   (Video URL in app.py)
        ↓
    app.py (Running)
    - Captures frames
    - Detects survivors
    - Gets GPS location
        ↓
  MongoDB Database
        ↓
web_server.py (Running)
   - Displays survivors on website
   - Users can identify them
        ↓
  http://localhost:5000 (Browser)
```

---

## ⚙️ Manual Start (If You Prefer)

Instead of `start_all.bat`, open 3 separate terminals:

### **Terminal 1 (GPS Server)**
```bash
python gps_server.py
```
Wait for: `GPS Server running on port 8888`

### **Terminal 2 (Detection Backend)**
```bash
python app.py
```
Wait for: Detection system ready

### **Terminal 3 (Web Server)**
```bash
python web_server.py
```
Wait for: Running on http://localhost:5000

**Then open browser:** http://localhost:5000

All 3 keep running simultaneously ✅

---

## 🔄 Data Synchronization

Everything syncs through MongoDB:

```
app.py (Detection)          web_server.py (Website)
    ↓                              ↓
   Detects survivor      ←→   MongoDB   ←→   Displays to users
   Saves to DB           ←→  (Shared)  ←→   Users identify
   Stores location       ←→  Database  ←→   Admin sees stats
    ↓                              ↓
  GPS Server
    ↓
Updates location data
```

**Result:** Everything updates in real-time across all services!

---

## ✅ Verification Checklist

After starting, verify everything works:

- [ ] GPS Server window shows "Running on port 8888"
- [ ] app.py window shows detection processing
- [ ] Web Server window shows "Running on http://localhost:5000"
- [ ] Browser opens to http://localhost:5000
- [ ] Website loads successfully
- [ ] Can see "Unidentified Survivors" section

If all ✅, you're good to go!

---

## 🎥 Mobile Video Setup

Your mobile should be configured to stream to:
```
http://<your-computer-ip>:<port>
```

Where:
- `<your-computer-ip>` = Your PC's IP (e.g., 192.168.1.100)
- `<port>` = Port configured in app.py (default: usually 8000+)

Check `app.py` for the exact URL to use on mobile.

---

## 📊 Monitor Services

### **Windows - Task Manager**
- Press `Ctrl+Shift+Esc`
- Look for 3 python processes running

### **Windows - Command Prompt**
```cmd
tasklist | findstr python
```

You should see 3 python.exe processes

### **Linux/Mac - Terminal**
```bash
ps aux | grep python
```

You should see 3 python processes

---

## 🛑 Stop Services

### **Safe Way - Ctrl+C**
In each terminal/window:
```
Press Ctrl+C
```

Services stop gracefully, data is saved.

### **Quick Way - Close Windows**
Just close each terminal window (data is saved to MongoDB).

### **Force Stop**
```bash
# Windows
taskkill /F /IM python.exe

# Linux/Mac
pkill -9 python
```

**Note:** Force stop loses unsaved data in memory (usually not a problem since MongoDB stores everything).

---

## ⚠️ Troubleshooting

### **Problem: Port 5000 already in use**
```bash
# Find what's using port 5000
netstat -ano | findstr :5000

# Kill it (Windows)
taskkill /PID <PID_NUMBER> /F

# Or use different port in web_server.py
```

### **Problem: MongoDB connection failed**
- Check `.env` file has correct connection string
- Verify internet connection
- Check MongoDB Atlas IP whitelist settings

### **Problem: Video not detected**
- Verify mobile is streaming to correct URL
- Check app.py is running and receiving frames
- Check MongoDB connection in app.py

### **Problem: Website shows "No survivors"**
- App.py might still be processing first batch
- Check app.py output for errors
- Wait 10-30 seconds for first detection batch

### **Problem: One service keeps crashing**
- Check the terminal output for error message
- Restart just that one service
- Other services keep running (thanks to MongoDB!)

---

## 🎯 Typical Daily Operation

### **Morning - Start Everything**
```bash
# Single command
python start_all.bat  (Windows)
# or
./start_all.sh  (Linux/Mac)

# Wait 5-10 seconds for all to start
```

### **During Day - Monitor**
- Keep all 3 windows/terminals open
- Website continues working
- Detection continues running
- New survivors appear automatically on website

### **Evening - Shutdown**
```bash
# Press Ctrl+C in each window
# Or close windows
# Data is saved to MongoDB
```

### **Next Day - Start Again**
- All previous data is still there
- Survivors you identified remain identified
- Stats are preserved
- Start from step 1

---

## 📈 Performance Tips

### **Optimize Detection**
- Adjust confidence threshold in app.py
- Reduce frame processing rate if CPU maxed
- Use GPU if available

### **Optimize Website**
- Clear browser cache if slow
- Restart web_server.py if sluggish
- Check MongoDB Atlas connection

### **Monitor Resources**
```bash
# Windows - Task Manager
Ctrl + Shift + Esc

# Linux - System Monitor
top
# or
htop
```

Look for:
- RAM usage < 1 GB total
- CPU < 80% average

---

## 🚀 Production Considerations

When going live:

### **Step 1: Test Everything**
- Run start_all.bat/sh for 24 hours
- Monitor logs for errors
- Verify data saves correctly

### **Step 2: Backup Database**
- MongoDB Atlas auto-backups (good!)
- Set up manual backups weekly

### **Step 3: Set Up Auto-Start**
Windows:
```
Task Scheduler → Create Task → Run start_all.bat on startup
```

Linux/Mac:
```
systemctl create service for each script
Or use supervisor/pm2
```

### **Step 4: Monitoring**
- Set up error logging
- Monitor disk space
- Track database size
- Alert on service crashes

---

## 📞 Need Help?

Check these files:
- `RUN_ALL_SERVICES.md` - Detailed explanation
- `SETUP_GUIDE.md` - Initial setup
- `start_all.bat` - Windows launcher
- `start_all.sh` - Linux/Mac launcher

---

## 🎉 Summary

**The Simplest Way:**
```
Double-click: start_all.bat
Wait 10 seconds
Open browser: http://localhost:5000
Done!
```

**All 3 services run simultaneously:**
- ✅ GPS Server (tracking location)
- ✅ Detection Backend (processing video)
- ✅ Web Server (displaying on website)

**Everything syncs automatically through MongoDB.**

You're ready to go! 🚀
