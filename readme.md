# India District Scraper and Downloader (IGOD Web Interface)
*A work-in-progress data acquisition tool for automated retrieval of India’s district, subdistrict, and block-level administrative data from the IGOD platform.*

---

## Overview

This repository hosts a **web-enabled automated scraper** for extracting India’s district- and subdistrict-level administrative information from the **Infrastructure and Governance Open Data (IGOD)** portal. It provides:

- A **Python Playwright scraper** that navigates IGOD’s dynamic interface to collect administrative units (states, districts, subdistricts/tehsils, blocks).  
- A lightweight **Flask web application** that exposes a clean user interface for triggering the scraper and automatically downloading output CSV files.  
- A **Dockerized deployment** workflow, supporting both local execution and cloud hosting via services such as Render.  
- A **progress display and browser-based download workflow**, enabling non-technical users to initiate and retrieve fresh district data with a single click.

This project is currently a **work in progress** and intended primarily for internal and research use. Future development aims to integrate fully automated scraping, scheduled data refreshes, and deployment to the **IndiaStateStory.in** portal.

---

## Repository Structure

```text
.
├── app.py                # Flask web server hosting UI, status endpoints, and zip downloader
├── igod_scraper.py       # Automated scraper (Playwright + requests + BeautifulSoup)
├── Dockerfile            # Full Docker build for Playwright-based deployment
├── requirements.txt      # Python dependencies
├── templates/
│   └── index.html        # Simple UI with scraping button and live progress display
├── data/                 # Auto-generated scrape logs and CSVs (ignored by Git)
└── .gitignore            # Excludes venv, data outputs, caches, etc.
```

### Key Components

#### `igod_scraper.py`
- Implements a hybrid scraping approach (Playwright for dynamic DOM elements + requests/BeautifulSoup for static content).  
- Produces timestamped CSV files for:
  - Subdistricts  
  - Blocks  
- Generates progress logs and scrape metadata within `data/`.

#### `app.py`
- Flask server enabling:
  - `/` — main page with UI  
  - `/download` — triggers scraper and returns zipped CSVs  
  - `/status` — reveals last 40+ log lines for progress streaming  
- Serves as a minimal backend to allow non-technical users to run the scraper.

#### `Dockerfile`
- Uses a Playwright-supported base image.  
- Installs system-level dependencies, Python libraries, and Chromium browsers needed for scraping.  
- Enables deployment on cloud platforms (Render, AWS, etc.).

#### `index.html`
- Clean UI with:
  - One-click **Download latest district data**  
  - Warning not to close the popup tab  
  - Live progress box updated every 3 seconds via polling  
  - Auto-triggered ZIP downloads when scraper completes  

---

## Installation & Local Development

### 1. Clone the repository
```bash
git clone https://github.com/mvdhv/India-district-scraper-and-downloader.git
cd India-district-scraper-and-downloader
```
### 2. Local Docker Run (recommended)
```bash
docker build -t igod-scraper:local .
docker run -p 5001:5000 --name igod-local -it igod-scraper:local
```
Open the application in your browser:
```bash
http://localhost:5001/
```
### 3. Development with Live Code Updates (optional)
To avoid rebuilding Docker during development:
```bash
docker run -p 5001:5000 \
  -v $(pwd):/app \
  --name igod-local \
  -it igod-scraper:local
```

---

## Cloud Deployment (Render)

This project supports one-click deployment on Render using the Dockerfile. But currently, this has been **suspended** pending further updates in the code.

---

## Planned Enhancements

The current release is functional but streamlined for testing and demonstration. Planned future development includes:

- **Automated scheduled scraping** (daily/weekly data refresh).
- **Integration with the IndiaStateStory.in platform** for public dissemination.
- **Improved concurrency handling,** including:
    - Run-locks
    - Background job queues
    - Per-user rate limiting
- **Persistent storage** (e.g., S3) for long-term archival of scraped datasets.
- **Improved progress visualization** and asynchronous UI.
- **State-level selective scraping** for faster demos and modular data retrieval.

---

## Credits and Acknowledgments

This repository contains contributions from multiple researchers:

### Scraping Logic & Core Data Extraction (igod_scraper.py)
Developed by  
**Ms. Anumeha Saxena**  
Research Associate   
India Gold Policy Centre  
Indian Institute of Management Ahmedabad   

### Web Application, Automation, Integration, Deployment
Developed by  
**Mr. Madhav Singh**  
Senior Research Associate  
Centre for Legislative Education and Research (CLER)  
FLAME University   

---

## License and Rights

**All rights reserved.**  
This project is not open-source and redistribution is restricted unless explicit written permission is granted by the contributors and affiliated institutions. Use of this codebase, in whole or in part, requires proper attribution to the original developers as noted above.

---
