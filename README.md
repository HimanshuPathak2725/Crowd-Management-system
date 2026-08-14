# 🛕 Temple Crowd Management System using AI & Computer Vision

## 📌 Overview

The **Temple Crowd Management System** is an AI-powered intelligent surveillance solution designed to improve crowd safety in temples and other large public gatherings. The system uses **YOLOv8**, **OpenCV**, and **Machine Learning** to monitor crowd movement, analyze crowd behavior, detect overcrowding, generate real-time alerts, visualize crowd density, and recommend the safest evacuation routes.

The project aims to reduce the risk of stampedes and crowd-related accidents by providing authorities with real-time insights and automated decision support.

---

# 🎯 Problem Statement

Large public gatherings often face serious safety challenges due to:

- Overcrowding
- Poor crowd monitoring
- Congestion at narrow pathways
- Delayed emergency response
- Lack of intelligent evacuation guidance

This project addresses these challenges using AI-based video analytics and real-time crowd monitoring.

---

# 🚀 Features

- 👥 Real-time People Detection
- 🎯 Person Tracking using YOLOv8
- 📊 Crowd Behaviour Analysis
- 🚨 Automatic Crowd Alerts
- 🔥 Crowd Density Heatmaps
- 🛣 Smart Route Recommendation
- 🔊 Voice-based Alerts
- 📈 Interactive Dashboard
- 📹 CCTV Video Analysis
- ⚡ Real-Time Processing

---

# 🏗 Project Architecture

```
                    CCTV Camera Videos
                           │
                           ▼
                 YOLOv8 Person Detection
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
 Crowd Behaviour     Crowd Alert        Crowd Density
    Analysis            System             Mapper
        │                  │                  │
        └──────────────┬───┴──────────────────┘
                       ▼
            Safe Exit Route Recommendation
                       ▼
                Control Room Dashboard
```

---

# 📂 Project Modules

## 1️⃣ Crowd Behaviour Analysis

This module analyzes the movement and behavior of the crowd in real time.

### Features

- Real-time people detection
- Person tracking
- Crowd movement analysis
- Walking speed estimation
- Direction analysis
- Path trajectory visualization
- Crowd flow monitoring
- Detection of abnormal crowd behaviour
- Interactive dashboard

### Technologies

- YOLOv8
- OpenCV
- Python
- Gradio

---

## 2️⃣ Crowd Alert System

This module continuously monitors crowd density and automatically sends alerts whenever the number of people exceeds a predefined threshold.

### Features

- Real-time crowd counting
- Density monitoring
- Configurable threshold
- Automatic alert generation
- Control room notification
- Live dashboard
- Visual warnings

### Applications

- Temple entrances
- Queue management
- Festival crowd monitoring
- Emergency response

---

## 3️⃣ Crowd Density Mapper

This module creates a real-time density map of the crowd to identify congestion zones.

### Features

- Density heatmap generation
- High-density zone detection
- Safe zone identification
- Color-coded risk visualization
- Grid-based crowd analysis
- Live monitoring dashboard

### Output

- Green → Low Density
- Yellow → Medium Density
- Red → High Density

---

## 4️⃣ Temple Crowd Lane Management

This module recommends the safest and fastest route by analyzing crowd density on multiple pathways.

### Features

- Multi-route crowd monitoring
- Person tracking
- Crowd estimation
- Travel time prediction
- Smart route recommendation
- Voice guidance
- Interactive visualization

---

## 5️⃣ Safe Exit Guidance

This module helps people evacuate safely during emergencies.

### Features

- Congestion prediction
- Emergency evacuation support
- Smart exit guidance
- Safe path recommendation
- AI-assisted decision making
- Real-time updates

---

# 🛠 Technologies Used

- Python
- YOLOv8
- OpenCV
- NumPy
- Pandas
- Plotly
- Gradio
- Pillow
- gTTS
- Machine Learning
- Computer Vision

---

# 📁 Project Structure

```
Temple-Crowd-Management-System/

│
├── Crowd Behaviour Analysis/
│
├── Crowd Alert System/
│
├── Crowd Density Mapper/
│
├── Temple Crowd Lane Management/
│
├── README.md
│
├── requirements.txt
│
└── assets/
```

---

# ⚙ Installation

Clone the repository

```bash
git clone https://github.com/yourusername/Temple-Crowd-Management-System.git
```

Move into the project directory

```bash
cd Temple-Crowd-Management-System
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run the application

```bash
python app.py
```

---

# 📊 Workflow

1. Upload CCTV or surveillance video.
2. Detect and track people using YOLOv8.
3. Analyze crowd movement and behaviour.
4. Measure crowd density.
5. Detect overcrowded regions.
6. Generate alerts if thresholds are exceeded.
7. Recommend the safest exit route.
8. Display results through an interactive dashboard.

---

# 📈 Applications

- Temples
- Religious Festivals
- Railway Stations
- Bus Terminals
- Shopping Malls
- Stadiums
- Concerts
- Political Rallies
- Smart Cities
- Airports
- Tourist Attractions

---

# 🔮 Future Enhancements

- Live CCTV Integration
- Mobile Application
- Multi-Camera Support
- Cloud Deployment
- Face Recognition (Authorized Personnel)
- Weather-aware Crowd Prediction
- Drone-based Crowd Monitoring
- IoT Sensor Integration
- Emergency SMS Notifications
- Predictive Crowd Analytics

---

# 📸 Sample Outputs

- Crowd Detection
- Person Tracking
- Density Heatmaps
- Route Recommendation Dashboard
- Crowd Alert Dashboard

(Add screenshots inside the `/assets` folder.)

---

# 🎯 Objectives

- Prevent crowd congestion and stampedes
- Improve public safety
- Assist authorities with real-time monitoring
- Enable intelligent crowd management
- Provide safe evacuation guidance

---

# 👨‍💻 Authors

**Your Name**

B.Tech Final Year Project

Department of Artificial Intelligence & Machine Learning

---

# ⭐ Acknowledgements

This project uses the following open-source technologies:

- Ultralytics YOLOv8
- OpenCV
- Gradio
- Plotly
- NumPy
- Pandas
- Google Text-to-Speech

---

## 📜 License

This project is developed for educational and research purposes.
