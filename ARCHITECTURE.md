# 🏗️ ARCHITECTURE DIAGRAM

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MyVerse Survivor Detection System                 │
└─────────────────────────────────────────────────────────────────────┘

                              Mobile Device
                            (Video Stream)
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ↓                           ↓
            ┌──────────────────┐      ┌──────────────────┐
            │  GPS Server      │      │  app.py          │
            │  Port 8888       │      │  (Detection)     │
            │  ┌────────────┐  │      │  ┌────────────┐  │
            │  │ Location   │  │      │  │ Video      │  │
            │  │ Tracking   │  │      │  │ Processing │  │
            │  │ GPS Data   │  │      │  │ Survivor   │  │
            │  │            │  │      │  │ Detection  │  │
            │  └────────────┘  │      │  │ Location   │  │
            └────────┬─────────┘      │  │ Data       │  │
                     │                │  └────────────┘  │
                     │                │         │        │
                     │                └────────┬┘        │
                     │                         │        │
                     └────────────┬────────────┘        │
                                  │                    │
                                  ↓                    │
                        ┌─────────────────────┐        │
                        │  MongoDB Atlas      │        │
                        │  (Cloud Database)   │        │
                        │                     │        │
                        │  Collections:       │        │
                        │  - survivors        │        │
                        │  - users            │        │
                        │  - locations        │        │
                        │                     │        │
                        └────────────┬────────┘        │
                                     │                 │
                        ┌────────────┴────────────┐    │
                        │                         │    │
                        ↓                         ↓    │
                   ┌──────────────┐        ┌───────────────┐
                   │web_server.py │        │ app.py        │
                   │Port 5000     │        │(Continued)    │
                   │              │        │               │
                   │┌────────────┐│        │ ┌───────────┐ │
                   ││ Website    ││        │ │ Statistics│ │
                   ││ Interface  ││        │ │ Logging   │ │
                   ││ Home       ││        │ │ Reports   │ │
                   ││ Register   ││        │ │ (optional)│ │
                   ││ Login      ││        │ └───────────┘ │
                   ││ Identify   ││        │               │
                   ││ Dashboard  ││        └───────────────┘
                   ││ Admin      ││
                   │└────────────┘│
                   └──────────────┘
                        │
                        ↓
                  ┌────────────────┐
                  │   Browser      │
                  │ (User Interface)
                  │ :5000          │
                  └────────────────┘
```

---

## Data Flow Diagram

```
                    ╔════════════════════════════════╗
                    ║   MOBILE DEVICE VIDEO STREAM   ║
                    ╚════════════════════╤═══════════╝
                                        │
                ┌───────────────────────┼───────────────────────┐
                │                       │                       │
                ↓                       ↓                       ↓
        ┌──────────────┐        ┌──────────────┐       ┌──────────────┐
        │ GPS Server   │        │   app.py     │       │ web_server.py│
        │              │        │              │       │              │
        │ Location:    │        │ • Extract    │       │ [Already     │
        │ • Lat/Lon    │        │   frames     │       │  Running]    │
        │ • Bearing    │        │ • Detect     │       │              │
        └──────┬───────┘        │   survivors  │       └──────┬───────┘
               │                │ • Get GPS    │              │
               │                │ • Capture    │              │
               │                │   image      │              │
               │                └──────┬───────┘              │
               │                       │                      │
               └───────────────────────┼──────────────────────┘
                                       │
                                       ↓
                    ╔════════════════════════════════╗
                    ║  MongoDB Atlas (Cloud DB)      ║
                    ║  ┌──────────────────────────┐  ║
                    ║  │ Survivor {               │  ║
                    ║  │   survivor_id: "...",   │  ║
                    ║  │   image: "path/...",    │  ║
                    ║  │   latitude: 16.99537,   │  ║
                    ║  │   longitude: 82.2488,   │  ║
                    ║  │   posture: "standing",  │  ║
                    ║  │   confidence: 0.829,    │  ║
                    ║  │   identified: false,    │  ║
                    ║  │ }                       │  ║
                    ║  └──────────────────────────┘  ║
                    ╚════════════╤═══════════════════╝
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ↓            ↓            ↓
          ┌─────────────────┐  ┌──────────────────┐
          │  web_server.py  │  │   app.py Stats   │
          │  Queries DB:    │  │  (Optional)      │
          │  • Gets new     │  │                  │
          │    survivors    │  │  Can query DB for│
          │  • Shows on web │  │  identification  │
          │  • Accepts      │  │  stats/reports   │
          │    identific... │  │                  │
          └────────┬────────┘  └──────────────────┘
                   │
                   ↓
         ┌─────────────────────┐
         │  http://localhost   │
         │      :5000          │
         │                     │
         │  ┌───────────────┐  │
         │  │ Unidentified  │  │
         │  │ Survivors     │  │
         │  │ Grid View     │  │
         │  │ with Images   │  │
         │  └───────────────┘  │
         │                     │
         │  User clicks:       │
         │  "Provide Info"     │
         │      │              │
         │      └────→ Submit  │
         │            Form     │
         │      │              │
         └──────┼──────────────┘
                │
                ↓
         MongoDB: identification = {
             name: "John Doe",
             phone: "+91...",
             email: "...",
             identified_by: user_id,
             identified_at: timestamp
         }
```

---

## Service Dependency Graph

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ GPS Server   │  │  app.py      │  │  web_server.py       │   │
│  │              │  │              │  │                      │   │
│  │ Independent  │  │ Uses GPS     │  │  Independent         │   │
│  │              │  │ Optional     │  │                      │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                 │                     │                │
│         └─────────────────┼─────────────────────┘                │
│                           │                                      │
│                    All depend on MongoDB                          │
│                           │                                      │
│         ┌─────────────────┴─────────────────┐                   │
│         │                                   │                   │
│         ↓                                   ↓                   │
│    ╔═════════════════════════════════════════╗                 │
│    ║   MongoDB Atlas Cloud Database          ║                 │
│    ║   (Shared Data Repository)              ║                 │
│    ║   - One source of truth                 ║                 │
│    ║   - All services read/write here        ║                 │
│    ║   - No direct communication between     ║                 │
│    ║     services (except via MongoDB)       ║                 │
│    ╚═════════════════════════════════════════╝                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

Benefits:
✓ Services are truly independent
✓ Can restart any service without affecting others
✓ Data is persistent and shared
✓ No port conflicts or interference
✓ Easy to scale (add more services if needed)
```

---

## Startup Sequence

```
User runs: start_all.bat (or start_all.sh)
                │
                ↓
    ┌───────────┴───────────┐
    │                       │
    ↓                       ↓
 1. GPS Server          2. app.py
    starts                 starts (waits for GPS if needed)
    (Port 8888)
                             │
                             ↓
                       3. web_server.py
                          starts
                        (Port 5000)
                             │
                             ↓
                       All 3 running
                       simultaneously!
                             │
                             ↓
                       Browser opens
                  http://localhost:5000
                             │
                             ↓
                     Website displayed
                     Ready for users!

Total Time: 5-10 seconds
```

---

## Communication Paths

```
Path 1: Video Detection → Website Updates
  app.py detects survivor
    │
    └─→ Save to MongoDB
          │
          └─→ web_server.py queries
                │
                └─→ Website updated
                      │
                      └─→ Browser shows survivor

Path 2: User Identifies → Admin Sees Update
  User submits form on website
    │
    └─→ web_server.py saves to MongoDB
          │
          └─→ app.py can query (for stats)
          │
          └─→ Admin dashboard updated

Path 3: GPS Data → Location Stored
  GPS Server provides location
    │
    └─→ app.py uses for survivor detection
          │
          └─→ Saved to MongoDB with survivor
                │
                └─→ web_server.py displays location
```

---

## Request/Response Example

```
Timeline: User identifies a survivor

10:00:05 - Survivor detected by app.py
          └─→ Saved to MongoDB with survivor_id="unknown_1_1234"

10:00:07 - web_server.py queries MongoDB
          └─→ Finds survivor, displays on website

10:00:10 - User sees survivor on website
          └─→ Clicks "Help" → Redirects to login

10:00:15 - User registers/logs in
          └─→ Fills identification form

10:00:20 - User submits: name, phone, email
          └─→ web_server.py saves to MongoDB
                └─→ identification = {
                      name: "John Doe",
                      phone: "+91...",
                      email: "john@email.com",
                      identified_by_user_id: user_123,
                      identified_at: 2024-01-15 10:00:20
                    }

10:00:25 - Admin dashboard updates
          └─→ Shows: "1 survivor identified"

10:00:30 - app.py queries (optional, for reports)
          └─→ Can see identification details
```

---

## File Locations & Roles

```
d:\myVerse\
│
├── start_all.bat ........... Main launcher (Windows)
├── start_all.sh ............ Main launcher (Linux/Mac)
├── start_all.py ............ Python launcher
│
├── gps_server.py ........... GPS Location Server (Port 8888)
├── app.py .................. Video Detection Backend
├── web_server.py ........... Flask Website Server (Port 5000)
│
├── reports/
│   ├── connection.py ....... MongoDB Connection Handler
│   └── survivors.json ...... Backup of survivor data
│
├── models/
│   ├── user.py ............ User authentication model
│   └── survivor.py ........ Survivor data model
│
├── templates/ .............. HTML templates (8 files)
│   ├── home.html
│   ├── login.html
│   ├── register.html
│   ├── identify.html
│   ├── survivor_detail.html
│   ├── dashboard.html
│   ├── admin.html
│   └── error.html
│
├── static/
│   ├── css/style.css ....... Styling
│   ├── js/script.js ........ Frontend utilities
│   └── images/
│       └── placeholder.svg . Fallback image
│
└── Documentation
    ├── COMPLETE_SOLUTION.md . Full explanation
    ├── QUICK_START.md ....... Quick reference
    ├── RUN_ALL_SERVICES.md .. Detailed guide
    ├── SETUP_GUIDE.md ....... Initial setup
    ├── INTEGRATION_GUIDE.py . Code examples
    └── .env ................. Configuration
```

---

## Key Design Principles

```
1. INDEPENDENCE
   ✓ Each service can run alone
   ✓ Each can be restarted independently
   ✓ No inter-service dependencies

2. LOOSE COUPLING
   ✓ Services don't call each other
   ✓ Communication via MongoDB only
   ✓ Can be on different machines

3. SHARED STATE
   ✓ MongoDB is single source of truth
   ✓ All services read/write same data
   ✓ Automatic synchronization

4. SCALABILITY
   ✓ Easy to add more services
   ✓ Easy to scale individual services
   ✓ Easy to distribute across servers

5. RELIABILITY
   ✓ One service failure doesn't break others
   ✓ Data persists in MongoDB
   ✓ Easy recovery
```

---

This is the **production-ready architecture** for your system! 🚀
