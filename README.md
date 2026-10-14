# ResilienceOps — Enterprise Business Continuity Management (BCM) Tool

A high-resilience, enterprise-grade **Business Continuity Management (BCM)** and **Operational Resilience** platform built with **Python & Django**, aligned with **ISO 22301** and the **EU Digital Operational Resilience Act (DORA)**.

This system replaces the conceptual React frontend proposed in `BCM.docx` with a responsive, high-performance Django web application featuring interactive dashboards, dynamic charts, dependency topologies, cascading failure simulations, real-time drill stopwatch, and conversational AI assistance.

---

## 🚀 Key Modules & Capabilities

### 1. Executive & Operational Cockpit (`/`)
- **Key Metrics**: Active critical services, Tier 1 concentration, ISO 22301 BIA compliance rate, active BCPs, open CAPA findings, and financial loss per hour.
- **Interactive Visualizations (Chart.js)**:
  - Criticality Tier Distribution (Tier 1 vs Tier 2 vs Tier 3).
  - BIA Attestation lifecycle health (Attested vs Under Review vs Draft).
- **Operational Worklists**: Pending workflow sign-offs and upcoming/recent RTEP test exercises.

### 2. Critical Services Registry & Third-Party ICT (`/services/`, `/ict-third-parties/`)
- **Service Catalog**: Service Code, Name, Tier, Business Owner, Department, RTO (Recovery Time Objective), RPO (Recovery Point Objective), MTPD (Maximum Tolerable Period of Disruption), and hourly loss exposure.
- **Lineage & Resilience Profile**: In-depth profile for each service displaying linked BIAs, active BCPs, upstream and downstream dependencies, and past test records.
- **ICT Third-Party Register (DORA Art. 28)**: Cloud providers and critical vendor infrastructure (AWS, Equinix, SWIFT, Cloudflare) with SLA tracking, hosting regions, and regulatory compliance.

### 3. Business Impact Analysis (BIA) Hub (`/bia/`)
- Multi-dimensional scoring matrix across **Financial**, **Operational**, **Regulatory**, and **Reputational** impact vectors (1–5 scale).
- Automated overall criticality score calculation (Catastrophic, Major, Moderate, Minor).
- Interactive 4-axis radar chart visualization for each assessment.
- Formal **Executive Attestation** workflow with digital sign-off and annual review triggers.

### 4. Interactive Operational Dependency Graph (`/dependencies/`)
- Interactive network topology (powered by Vis.js Network) mapping services, cloud providers, and third-party rails.
- Node Inspector: Click any node to inspect outgoing dependencies, dependent upstream services, recovery objectives, and blast radius.

### 5. Business Continuity Plans & Runbooks (`/bcp/`)
- Crisis activation thresholds and failover triggers.
- Primary vs secondary DR site specifications (e.g. Frankfurt Colocation to Zurich Hot Standby).
- Step-by-step failover execution sequence.
- **Crisis Response Call Tree**: Emergency contacts with phone, email, priority ordering, and alternate designations.

### 6. Extreme Scenario Catalog & RTEP Testing (`/scenarios/`, `/rtep/`)
- **Scenario Library**: Standardized stress-test scenarios (Ransomware lockouts, Data Center power blackouts, AWS regional partitions, Third-party network severances).
- **RTEP Test Platform**: Scheduling and tracking of failover exercises (Simulation Drills, Tabletop Walkthroughs, Full Failovers).
- **Interactive Live Drill Runner (`/rtep/<id>/drill/`)**:
  - Digital real-time stopwatch / timer (Start, Pause, Reset).
  - Chronological inject sequence checklist.
  - Live timestamped observation logger.
  - Actual recovery time verification against target RTO thresholds.

### 7. Cascading Impact Simulation Engine (`/impact/`)
- Interactive "What-If" failure simulation studio.
- Select any internal critical service or third-party cloud infrastructure (e.g., AWS eu-central-1, Equinix Frankfurt).
- Calculates:
  - Cumulative projected financial loss based on duration.
  - Immediate direct vs cascading upstream contagion.
  - RTO breach warnings (services whose RTO is lower than the disruption duration).
  - Recommended contingency BCP runbooks.

### 8. Findings & Remediation (CAPA) (`/findings/`)
- Corrective Action and Preventative Action (CAPA) tracking register.
- Severity levels (Critical, High, Medium, Low) and lifecycle states (Open, In Progress, Ready for Retest, Closed & Verified).
- Retest verification notes.

### 9. Evidence Repository & Vault (`/evidence/`)
- Auditable storage of drill execution logs, failover proofs, BIA sign-offs, and regulator disclosures.
- Checksum integrity verification.

### 10. Governance & Workflow Approvals (`/approvals/`)
- Dual-control governance inbox for pending sign-offs (BIA attestation, finding closures, scenario approvals).
- One-click Approve or Reject actions with mandatory audit comments.

### 11. ResQ AI Assistant (`/resq/`)
- Context-aware conversational AI assistant trained on your BCM repository, ISO 22301, and DORA standards.
- Quick prompt pills for instant answers:
  - *"What happens if AWS Frankfurt fails?"*
  - *"Tier 1 services with RTO < 2h"*
  - *"Open critical CAPA findings"*
  - *"DORA compliance readiness"*

### 12. System Governance & Immutable Audit Logs (`/admin-audit/`)
- Chronological, tamper-evident audit trail capturing actor, action, entity class, target reference, timestamp, and IP address.
- Role-Based Access Control (RBAC) governance matrix.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.14 + Django 6.1
- **Database**: SQLite (Development / Demo) or PostgreSQL (Production)
- **Frontend / UI**: Django Templates + Custom Glassmorphic Dark Design System (`static/css/bcm.css`)
- **Visualizations**: Chart.js 4.4 + Vis.js Network
- **Icons & Typography**: Google Fonts (Inter & Outfit) + Scalable Feather / Heroicons

---

## 🏃 Quick Start Guide

### 1. Prerequisites
Ensure Python 3.10+ is installed:
```powershell
py -3 --version
```

### 2. Install Dependencies
```powershell
py -3 -m pip install django
```

### 3. Run Migrations
```powershell
py -3 manage.py makemigrations bcm_app
py -3 manage.py migrate
```

### 4. Seed Enterprise Sample Data
Populate the database with realistic banking / fintech critical services, ICT vendors, dependencies, BCPs, scenarios, and tests:
```powershell
py -3 manage.py seed_bcm_data
```

### 5. Launch the Server
```powershell
py -3 manage.py runserver 127.0.0.1:8000
```

Open your browser to: **`http://127.0.0.1:8000/`**