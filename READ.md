# 🚦 AI-Powered Red-Light Violation Detection System with Driver Profiling

This is a complete, modular, and production-ready Python codebase for an AI-powered system designed to detect red-light violations using CCTV video feeds and perform driver profiling.

## ✨ Features

- **Vehicle Detection:** Uses pre-trained **YOLOv8** (Ultralytics) for high-accuracy vehicle identification.
- **Violation Logic:** Robust OpenCV-based logic to check if a vehicle centroid crosses a configurable stop-line during a red light.
- **License Plate Recognition (LPR):** Primary OCR with **EasyOCR**, with a fallback to **PyTesseract** for increased reliability.
- **Driver Profiling:** PostgreSQL database via SQLAlchemy to log violations and maintain a profile (risk score, total violations, smart fine calculation) for repeat offenders.
- **Dashboard:** A simple, responsive dashboard built with **Flask** and HTML/CSS (Bootstrap) to visualize violations and offender profiles.
- **Modular Design:** Code is structured with type hints, docstrings, and unit tests for production readiness.

## 🚀 Architecture Overview


The system operates in two main parts:

1.  **Inference Pipeline (`scripts/process_video.py`):** Takes a video stream, applies YOLOv8 for detection, tracks vehicles, checks for stop-line violation during the red phase, and logs the violation (including license plate) to the PostgreSQL database via a dedicated API endpoint.
2.  **Web Dashboard (`app/api/routes.py`):** A Flask application that serves an administrative interface to view statistics, lists of offenders, and details of each violation by querying the PostgreSQL database.

## ⚙️ Setup and Installation

### Prerequisites

1.  **Python 3.8+**
2.  **PostgreSQL** server running locally or accessible via a network.
3.  **Tesseract OCR** must be installed on your system if you want to use the Tesseract fallback.

### Step-by-Step Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd red-light-detector
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Requirements:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a file named `.env` in the root directory and populate it based on `.env.example`.

    ```bash
    # Example command to copy the template
    cp .env.example .env
    # Edit the .env file with your specific credentials
    ```

### Database Initialization (PostgreSQL)

You need a PostgreSQL database.

1.  **Create the Database:** Use your PostgreSQL client (like `psql` or `pgAdmin`) to create a database, e.g., `redlight_violations`.

    ```sql
    CREATE DATABASE redlight_violations;
    ```

2.  **Run the Setup Script:** The `run_local.sh` script will automatically run the necessary setup steps, including creating the tables.

## 🏃 How to Run Locally

### 1. Database Setup & Table Creation

The `run_local.sh` script handles this using the SQLAlchemy `Base.metadata.create_all()` method defined in `app/models/db.py`.

### 2. Run the Main Inference Script

Process a sample video to detect violations and populate the database.

```bash
python scripts/process_video.py \
    --video sample_data/sample_video.mp4 \
    --signal-json sample_data/signal_timestamps.json \
    --stop-line "500,800,1000,800" \
    --output output/annotated_demo.mp4