# 📶 NFC Student Attendance System

Complete NFC-based student clock-in/clock-out system for universities.  
Uses NFC student ID cards, Flask backend, MySQL database, and a responsive admin dashboard.

---

## 📁 Folder Structure

```
nfc-attendance/
├── backend/
│   ├── app.py                    # Flask main app
│   ├── requirements.txt
│   ├── models/
│   │   └── db.py                 # DB connection pool
│   └── routes/
│       ├── auth.py               # Login / JWT
│       ├── students.py           # Student CRUD
│       ├── attendance.py         # Clock in/out, reports, CSV export
│       ├── nfc.py                # NFC card management & logs
│       └── dashboard.py          # Stats for dashboard
├── frontend/
│   └── index.html                # Single-page admin dashboard
├── nfc/
│   └── nfc_reader.py             # NFC reader daemon (hardware)
├── database/
│   └── schema.sql                # MySQL schema + sample data
├── docs/
│   └── nfc-attendance.service    # Systemd service (Raspberry Pi)
├── .env.example
└── README.md
```

---

## 🔧 Requirements

- Python 3.9+
- MySQL 8.0+
- NFC Reader: ACR122U **or** PN532 (UART/SPI/I2C)

---

## 💻 Local Installation (PC / Ubuntu)

### 1. Clone & set up environment

```bash
git clone <your-repo>
cd nfc-attendance
cp .env.example .env
nano .env   # Fill in your DB credentials and secret keys
```

### 2. Set up MySQL

```bash
mysql -u root -p
```

```sql
CREATE USER 'nfc_user'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON nfc_attendance.* TO 'nfc_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

```bash
mysql -u nfc_user -p < database/schema.sql
```

### 3. Install Python dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the Flask backend

```bash
python app.py
```

Server starts at: **http://localhost:5000**

### 5. Open the dashboard

Open `frontend/index.html` in your browser  
**or** visit http://localhost:5000 if Flask serves it.

**Default login:** `admin` / `Admin@1234`

---

## 🔌 Connecting the NFC Reader

### ACR122U (USB)

```bash
# Install nfcpy
pip install nfcpy

# Ubuntu: give USB permissions
sudo adduser $USER plugdev
sudo nano /etc/udev/rules.d/99-nfc.rules
# Add: SUBSYSTEM=="usb", ATTRS{idVendor}=="072f", ATTRS{idProduct}=="2200", MODE="0664", GROUP="plugdev"
sudo udevadm control --reload-rules

# Run reader daemon
cd nfc/
python3 nfc_reader.py --reader acr122u --api http://localhost:5000
```

### PN532 via UART (Raspberry Pi)

```bash
# Enable UART in raspi-config
sudo raspi-config  # → Interface Options → Serial → Enable

# Install pn532 library
pip install pn532

# Run reader daemon
python3 nfc_reader.py --reader pn532 --port /dev/ttyAMA0 --api http://localhost:5000
```

### Test without hardware (Simulation mode)

```bash
python3 nfc_reader.py --simulate --api http://localhost:5000
# Enter UIDs manually when prompted
```

---

## 🥧 Raspberry Pi Deployment

### 1. Flash Raspberry Pi OS and connect via SSH

```bash
ssh pi@<pi-ip-address>
```

### 2. Install dependencies

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv mysql-server
sudo mysql_secure_installation
```

### 3. Copy project to Pi

```bash
scp -r nfc-attendance/ pi@<pi-ip>:/home/pi/
```

### 4. Set up as systemd service

```bash
sudo cp docs/nfc-attendance.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nfc-attendance
sudo systemctl start nfc-attendance
sudo systemctl status nfc-attendance
```

### 5. Configure NFC reader daemon as service

Create `/etc/systemd/system/nfc-reader.service`:

```ini
[Unit]
Description=NFC Card Reader Daemon
After=nfc-attendance.service

[Service]
User=pi
WorkingDirectory=/home/pi/nfc-attendance/nfc
ExecStart=/home/pi/nfc-attendance/venv/bin/python3 nfc_reader.py \
    --reader acr122u \
    --api http://localhost:5000 \
    --entry main
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable nfc-reader
sudo systemctl start nfc-reader
```

### 6. Access dashboard over local network

Any device on the same WiFi can access:
`http://<pi-ip-address>:5000`

---

## 🌐 Multi-Entry-Point Setup

Run a separate NFC reader daemon per entry point:

```bash
# Main entrance
python3 nfc_reader.py --api http://192.168.1.100:5000 --entry main_entrance

# Library
python3 nfc_reader.py --api http://192.168.1.100:5000 --entry library

# Lab
python3 nfc_reader.py --api http://192.168.1.100:5000 --entry computer_lab
```

---

## 👤 Sample Students (pre-loaded)

| Name | Student ID | Course | Year | Card UID |
|------|-----------|--------|------|----------|
| Kevin Ssemwanga | STU2026001 | BSc Computer Science | 2 | 04A3F91B2C |
| Aisha Nakato | STU2026002 | BBA | 1 | 039BD4827F |

---

## 📡 API Reference

| Method | Endpoint | Auth | Description |
|--------|---------|------|-------------|
| POST | `/api/auth/login` | None | Admin login |
| POST | `/api/attendance/scan` | None | NFC scan (clock in/out) |
| GET | `/api/attendance/today` | JWT | Today's records |
| GET | `/api/attendance/report` | JWT | Date range report |
| GET | `/api/attendance/export` | JWT | CSV download |
| GET | `/api/attendance/summary` | JWT | Hours per student |
| GET | `/api/students/` | JWT | List students |
| POST | `/api/students/` | JWT | Add student |
| PUT | `/api/students/<id>` | JWT | Edit student |
| DELETE | `/api/students/<id>` | JWT | Deactivate student |
| POST | `/api/nfc/assign` | JWT | Assign card UID |
| GET | `/api/nfc/logs` | JWT | Scan audit logs |
| GET | `/api/dashboard/stats` | JWT | Dashboard stats |

---

## 🔐 Security Notes

- Change `SECRET_KEY` and `JWT_SECRET_KEY` in `.env` before deployment
- Run behind nginx with HTTPS in production
- Default admin password must be changed on first login
- All admin endpoints are JWT-protected
- Card scan endpoint is intentionally open (local hardware only)

---

## 🛠️ Troubleshooting

**NFC reader not detected?**  
→ Check USB permissions. Run `lsusb` to confirm device is visible.

**MySQL connection refused?**  
→ Ensure MySQL is running: `sudo systemctl start mysql`

**Cards not recognized?**  
→ Use simulation mode to test: `python3 nfc_reader.py --simulate`  
→ Verify the UID is assigned to a student via the admin dashboard.

**Dashboard shows "Login failed"?**  
→ Default credentials: `admin` / `Admin@1234`  
→ Run schema.sql again if admin user was not created.
