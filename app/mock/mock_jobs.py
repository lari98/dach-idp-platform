"""
app/mock/mock_jobs.py
======================
Realistic mock job descriptions from DACH + Nordic enterprise employers.
Multilingual: DE, EN, FR, SV.

Employers represented:
  DE: Deloitte, KPMG, Deutsche Bank, Accenture, Sparkasse, Siemens, SAP SE
  CH: Six Group, UBS, Zurich Insurance, PwC Schweiz
  AT: Erste Bank, OMV, KPMG Austria
  SE: Handelsbanken, Nordea, Ericsson (Swedish-language postings)
"""
from __future__ import annotations

from app.models.ats import (
    Department,
    EmploymentType,
    HardRequirement,
    JobLanguage,
    JobRequisition,
    SeniorityLevel,
)

MOCK_JOBS: list[JobRequisition] = [

    # ─── 1. Deloitte DE — Senior Consultant Strategy (German) ───────────────
    JobRequisition(
        job_id="JR-DEL-001",
        title="Senior Consultant Strategy & Operations",
        employer="Deloitte Deutschland GmbH",
        department=Department.CONSULTING,
        location="Frankfurt, DE",
        remote_possible=True,
        employment_type=EmploymentType.FULL_TIME,
        seniority=SeniorityLevel.SENIOR,
        language=JobLanguage.DE,
        salary_min=75000,
        salary_max=95000,
        currency="EUR",
        description_text="""
Wir suchen einen erfahrenen Senior Consultant (m/w/d) für unsere Practice Strategy & Operations
am Standort Frankfurt. Sie beraten DAX-Konzerne und mittelständische Unternehmen bei
strategischen Transformationsprojekten und Prozessoptimierungen.

Ihre Aufgaben:
- Leitung von Beratungsprojekten im Bereich Unternehmensberatung und Strategieberatung
- Projektmanagement und Teamführung von 3-5 Consultants
- Stakeholder Management auf C-Level
- Entwicklung von Präsentationen und Entscheidungsvorlagen
- Agile Methoden und Scrum in der Projektarbeit

Das bringen Sie mit (Voraussetzungen):
- Mindestens 5 Jahre Berufserfahrung in der Unternehmensberatung oder Strategieberatung
- Abgeschlossenes Masterstudium (Wirtschaft, BWL, Ingenieurwesen oder vergleichbar)
- Verhandlungssicheres Deutsch (C2/Muttersprache) und fließend Englisch (C1)
- Ausgeprägte Kommunikation und Präsentation Skills
- Erfahrung in Projektmanagement und Agile Methoden
- SAP-Kenntnisse von Vorteil

Das wäre wünschenswert (Nice-to-have):
- PMP-Zertifizierung oder Prince2
- Erfahrung mit Data Analysis und Business Intelligence
- Kenntnisse im Risikomanagement
        """,
        required_skills=["consulting", "project_management", "communication", "leadership"],
        preferred_skills=["data_analysis", "risk_management", "sap", "agile"],
        required_certifications=[],
        min_years_experience=5.0,
        required_education="master",
        required_languages=[
            {"language": "german_language", "min_level": "c1", "weight": 2.0},
            {"language": "english_language", "min_level": "b2", "weight": 1.0},
        ],
        hard_requirements=[
            HardRequirement(field="work_authorization", value="EU_EEA_required",
                            description="EU/EEA work authorisation required"),
        ],
        posted_date=None,
        is_active=True,
        applications_count=47,
    ),

    # ─── 2. KPMG DE — Manager Audit & Assurance (German) ────────────────────
    JobRequisition(
        job_id="JR-KPM-001",
        title="Manager Wirtschaftsprüfung / Audit (m/w/d)",
        employer="KPMG AG Wirtschaftsprüfungsgesellschaft",
        department=Department.AUDIT,
        location="München, DE",
        remote_possible=False,
        employment_type=EmploymentType.FULL_TIME,
        seniority=SeniorityLevel.MANAGER,
        language=JobLanguage.DE,
        salary_min=80000,
        salary_max=105000,
        currency="EUR",
        description_text="""
KPMG sucht einen Manager (m/w/d) für den Bereich Wirtschaftsprüfung / Audit
am Standort München. Sie führen eigenverantwortlich Jahresabschlussprüfungen
nach HGB und IFRS durch und betreuen DAX- und MDAX-Unternehmen.

Ihre Aufgaben:
- Leitung von Jahresabschlussprüfungen und Sonderprüfungen
- Führung eines Teams von 4-6 Prüfungsassistenten
- Prüfung von Jahresabschlüssen nach HGB, IFRS und US-GAAP
- Risikomanagement und Compliance-Prüfungen
- Reporting und Präsentation an Mandanten und Aufsichtsräte

Voraussetzungen:
- Mindestens 6 Jahre Erfahrung in der Wirtschaftsprüfung / Revision
- Bestandenes Wirtschaftsprüferexamen (CPA/WP) oder kurz vor Abschluss
- Masterstudium in Wirtschaftswissenschaften, Rechnungswesen oder Steuerrecht
- Verhandlungssicheres Deutsch und Englisch (min. C1)
- Buchhaltung, Rechnungswesen und IFRS-Kenntnisse zwingend erforderlich
- Erfahrung in Compliance und Risikobewertung

Wünschenswert:
- SAP FI Kenntnisse
- Steuerrechtliche Grundkenntnisse
- CIA-Zertifizierung
        """,
        required_skills=["audit", "accounting", "risk_management", "compliance"],
        preferred_skills=["tax", "sap"],
        required_certifications=["cpa"],
        min_years_experience=6.0,
        required_education="master",
        required_languages=[
            {"language": "german_language", "min_level": "c1", "weight": 2.0},
            {"language": "english_language", "min_level": "c1", "weight": 1.5},
        ],
        hard_requirements=[
            HardRequirement(field="required_certification", value="cpa",
                            description="WP-Examen or equivalent required"),
            HardRequirement(field="work_authorization", value="EU_EEA_required"),
        ],
        is_active=True,
        applications_count=31,
    ),

    # ─── 3. Deutsche Bank — Risk Analyst (English) ───────────────────────────
    JobRequisition(
        job_id="JR-DB-001",
        title="Risk Analyst — Market & Credit Risk",
        employer="Deutsche Bank AG",
        department=Department.RISK,
        location="Frankfurt, DE",
        remote_possible=True,
        employment_type=EmploymentType.FULL_TIME,
        seniority=SeniorityLevel.MID,
        language=JobLanguage.EN,
        salary_min=65000,
        salary_max=85000,
        currency="EUR",
        description_text="""
Deutsche Bank is seeking a Risk Analyst to join our Market & Credit Risk team in Frankfurt.
You will contribute to the bank's risk management framework and support regulatory reporting
under Basel III requirements.

Responsibilities:
- Market risk and credit risk analysis and monitoring
- Risk management reporting for senior management and regulators
- Compliance with MiFID, Basel III, and BaFin regulatory requirements
- Data analysis and risk model validation using Python and SQL
- AML and KYC process support

Requirements (must have):
- 3+ years of experience in banking or financial services risk management
- Bachelor's or Master's degree in Finance, Mathematics, Economics or related field
- Proficiency in Python and SQL for data analysis
- Knowledge of risk management frameworks (Basel III, MiFID)
- Fluent English (C1+) — business working language
- German B2 minimum for client interactions

Nice to have:
- FRM or CFA certification
- Excel and VBA skills
- Experience with compliance and AML frameworks
        """,
        required_skills=["risk_management", "banking", "python", "sql", "compliance"],
        preferred_skills=["excel", "data_analysis"],
        required_certifications=[],
        min_years_experience=3.0,
        required_education="bachelor",
        required_languages=[
            {"language": "english_language", "min_level": "c1", "weight": 2.0},
            {"language": "german_language", "min_level": "b2", "weight": 1.0},
        ],
        hard_requirements=[
            HardRequirement(field="work_authorization", value="EU_EEA_required"),
        ],
        is_active=True,
        applications_count=89,
    ),

    # ─── 4. Six Group — Data Engineer (English/German) ───────────────────────
    JobRequisition(
        job_id="JR-SIX-001",
        title="Data Engineer — Financial Market Infrastructure",
        employer="SIX Group AG",
        department=Department.DATA,
        location="Zürich, CH",
        remote_possible=True,
        employment_type=EmploymentType.FULL_TIME,
        seniority=SeniorityLevel.SENIOR,
        language=JobLanguage.EN,
        salary_min=110000,
        salary_max=140000,
        currency="CHF",
        description_text="""
SIX Group is Switzerland's financial market infrastructure operator.
We are looking for a Data Engineer to join our Data & Analytics platform team in Zurich.

Your responsibilities:
- Design and implement scalable data pipelines for financial market data
- Cloud infrastructure development on Azure and AWS
- Machine learning model deployment and MLOps pipelines
- Python and SQL development for high-volume data processing
- Agile development in cross-functional teams

What you bring (required):
- 5+ years of experience in data engineering or software development
- Strong Python programming skills
- Expert SQL and database management skills
- Cloud experience (Azure preferred, AWS acceptable)
- Fluent English — working language of the team
- German B1 or above for Swiss business environment

Nice to have:
- Machine learning and AI experience
- Azure certifications (AZ-900 or above)
- Financial services or banking domain knowledge
        """,
        required_skills=["python", "sql", "cloud", "software_development"],
        preferred_skills=["machine_learning", "data_analysis", "banking"],
        required_certifications=[],
        min_years_experience=5.0,
        required_education="bachelor",
        required_languages=[
            {"language": "english_language", "min_level": "c1", "weight": 2.0},
            {"language": "german_language", "min_level": "b1", "weight": 1.0},
        ],
        hard_requirements=[],
        is_active=True,
        applications_count=62,
    ),

    # ─── 5. Accenture — SAP Consultant (German) ─────────────────────────────
    JobRequisition(
        job_id="JR-ACC-001",
        title="SAP S/4HANA Berater Finance (m/w/d)",
        employer="Accenture GmbH",
        department=Department.TECHNOLOGY,
        location="Berlin, DE",
        remote_possible=True,
        employment_type=EmploymentType.FULL_TIME,
        seniority=SeniorityLevel.MID,
        language=JobLanguage.DE,
        salary_min=60000,
        salary_max=80000,
        currency="EUR",
        description_text="""
Accenture sucht einen SAP S/4HANA Berater (m/w/d) mit Schwerpunkt Finance für
unseren Standort Berlin. Sie begleiten DAX-Unternehmen bei der SAP-Transformation
und implementieren SAP FI/CO Module.

Ihre Aufgaben:
- Implementierung und Customizing von SAP S/4HANA FI/CO
- Unternehmensberatung bei SAP-Transformationsprojekten
- Erarbeitung von Konzepten für Buchhaltung und Rechnungswesen in SAP
- Projektmanagement und Stakeholder Management
- Anforderungsanalyse und Workshops mit Fachbereichen

Voraussetzungen:
- Mindestens 3 Jahre SAP-Erfahrung (FI, CO oder MM/SD)
- Abgeschlossenes Bachelor- oder Masterstudium
- Kenntnisse in Buchhaltung, Rechnungswesen und IFRS
- Verhandlungssicheres Deutsch (Muttersprache oder C2)
- Fließend Englisch (mind. B2) für internationale Projektarbeit
- Erfahrung in Beratung und Projektmanagement

Wünschenswert:
- SAP S/4HANA Zertifizierung
- Agile / Scrum Erfahrung
- Kenntnisse in Compliance und Risikomanagement
        """,
        required_skills=["sap", "accounting", "consulting", "project_management"],
        preferred_skills=["agile", "compliance", "risk_management"],
        required_certifications=[],
        min_years_experience=3.0,
        required_education="bachelor",
        required_languages=[
            {"language": "german_language", "min_level": "c2", "weight": 2.5},
            {"language": "english_language", "min_level": "b2", "weight": 1.0},
        ],
        hard_requirements=[
            HardRequirement(field="work_authorization", value="EU_EEA_required"),
        ],
        is_active=True,
        applications_count=55,
    ),

    # ─── 6. Sparkasse — HR Manager (German) ─────────────────────────────────
    JobRequisition(
        job_id="JR-SPK-001",
        title="HR Manager / Personalreferent (m/w/d)",
        employer="Sparkasse Frankfurt am Main",
        department=Department.HR,
        location="Frankfurt, DE",
        remote_possible=False,
        employment_type=EmploymentType.FULL_TIME,
        seniority=SeniorityLevel.MID,
        language=JobLanguage.DE,
        salary_min=52000,
        salary_max=68000,
        currency="EUR",
        description_text="""
Die Sparkasse Frankfurt am Main sucht einen Personalreferenten (m/w/d) zur Verstärkung
unseres HR-Teams. Sie übernehmen eigenverantwortlich das Recruiting und die
Personalentwicklung für unsere Filialen.

Ihre Aufgaben:
- Recruiting und Personalauswahl für gewerbliche und kaufmännische Stellen
- Onboarding neuer Mitarbeiterinnen und Mitarbeiter
- Personalentwicklung und Talent Management
- Beratung von Führungskräften in arbeitsrechtlichen Fragen
- Lohnabrechnung und Payroll (SAP HCM)
- Employer Branding und Stellenausschreibungen

Voraussetzungen:
- 3+ Jahre Erfahrung im Personalwesen / HR
- Abgeschlossene kaufmännische Ausbildung oder Bachelorstudium HR
- Fundierte Kenntnisse im deutschen Arbeitsrecht
- SAP HCM Kenntnisse
- Verhandlungssicheres Deutsch, Muttersprache bevorzugt
- Sehr gute Kommunikation und Sozialkompetenz

Wünschenswert:
- Englischkenntnisse (B1+)
- Erfahrung mit Talent Management Systemen
        """,
        required_skills=["human_resources", "sap", "communication"],
        preferred_skills=["leadership", "english_language"],
        required_certifications=[],
        min_years_experience=3.0,
        required_education="bachelor",
        required_languages=[
            {"language": "german_language", "min_level": "c2", "weight": 3.0},
        ],
        hard_requirements=[
            HardRequirement(field="work_authorization", value="EU_EEA_required"),
        ],
        is_active=True,
        applications_count=28,
    ),

    # ─── 7. PwC Switzerland — Tax Advisor (French/German) ───────────────────
    JobRequisition(
        job_id="JR-PWC-001",
        title="Conseiller Fiscal / Tax Advisor (m/f/x)",
        employer="PricewaterhouseCoopers SA",
        department=Department.TAX,
        location="Genf, CH",
        remote_possible=True,
        employment_type=EmploymentType.FULL_TIME,
        seniority=SeniorityLevel.SENIOR,
        language=JobLanguage.FR,
        salary_min=95000,
        salary_max=125000,
        currency="CHF",
        description_text="""
PwC Suisse recherche un(e) Conseiller(ère) Fiscal(e) expérimenté(e) pour renforcer
notre équipe Tax & Legal à Genève. Vous conseillerez des multinationales sur des
questions de fiscalité internationale et de prix de transfert.

Vos responsabilités:
- Conseil en fiscalité des entreprises et prix de transfert
- Planification fiscale pour clients internationaux (Suisse, EU, global)
- Conformité fiscale et reporting réglementaire
- Gestion de projets et management d'équipe
- Audit fiscal et gestion des risques fiscaux

Profil requis:
- Minimum 5 ans d'expérience en conseil fiscal ou droit fiscal
- Master en droit fiscal, comptabilité ou domaine similaire
- Expert-comptable ou titre équivalent (CPA)
- Français courant (langue principale de travail, C1 minimum)
- Allemand courant (B2 minimum) pour clients romands et alémaniques
- Anglais professionnel (B2) pour contexte international

Souhaité:
- Connaissance approfondie de la fiscalité suisse (TVA, impôt sur les sociétés)
- Maîtrise d'Excel et outils d'analyse de données
        """,
        required_skills=["tax", "accounting", "consulting", "risk_management"],
        preferred_skills=["excel", "data_analysis", "compliance"],
        required_certifications=["cpa"],
        min_years_experience=5.0,
        required_education="master",
        required_languages=[
            {"language": "french_language", "min_level": "c1", "weight": 3.0},
            {"language": "german_language", "min_level": "b2", "weight": 1.5},
            {"language": "english_language", "min_level": "b2", "weight": 1.0},
        ],
        hard_requirements=[
            HardRequirement(field="required_certification", value="cpa",
                            description="Expert-comptable or equivalent required"),
        ],
        is_active=True,
        applications_count=19,
    ),

    # ─── 8. Nordea — Technology Project Manager (Swedish) ───────────────────
    JobRequisition(
        job_id="JR-NOR-001",
        title="IT-projektledare — Digital Banking",
        employer="Nordea Bank Abp, filial i Sverige",
        department=Department.TECHNOLOGY,
        location="Stockholm, SE",
        remote_possible=True,
        employment_type=EmploymentType.FULL_TIME,
        seniority=SeniorityLevel.SENIOR,
        language=JobLanguage.SV,
        salary_min=700000,
        salary_max=900000,
        currency="SEK",
        description_text="""
Nordea söker en erfaren IT-projektledare för vår Digital Banking-division i Stockholm.
Du leder komplexa teknikprojekt och driver digitaliseringsinitiativ i en agil miljö.

Dina ansvarsområden:
- Projektledning av stora IT-transformationsprojekt inom digital bankverksamhet
- Agila metoder och Scrum i leveransteam
- Intressenthantering på C-nivå och med externa leverantörer
- Riskhantering och compliance med finansiella regelverk (MiFID, PSD2)
- Molntjänster och cloud-migrering (Azure eller AWS)
- Kommunikation och rapportering till styrelse och ledningsgrupp

Krav (obligatoriska):
- Minst 7 års erfarenhet av IT-projektledning
- Civilingenjör eller masterexamen inom IT, Datateknik eller liknande
- Flytande svenska — modersmål eller motsvarande (C2)
- God engelska (C1) för nordiska och internationella samarbeten
- Dokumenterad erfarenhet av agila metoder (Scrum, Kanban, SAFe)
- Riskhantering och regelefterlevnad inom finansbranschen

Meriterande:
- PMP- eller PRINCE2-certifiering
- Erfarenhet av molntjänster (Azure/AWS)
- Kunskaper om bankverksamhet och kapitalmarknad
        """,
        required_skills=["project_management", "agile", "risk_management", "cloud", "communication"],
        preferred_skills=["banking", "machine_learning"],
        required_certifications=[],
        min_years_experience=7.0,
        required_education="master",
        required_languages=[
            {"language": "swedish_language", "min_level": "c2", "weight": 3.0},
            {"language": "english_language", "min_level": "c1", "weight": 1.5},
        ],
        hard_requirements=[],
        is_active=True,
        applications_count=34,
    ),
]


def get_job(job_id: str) -> JobRequisition | None:
    return next((j for j in MOCK_JOBS if j.job_id == job_id), None)


def get_active_jobs() -> list[JobRequisition]:
    return [j for j in MOCK_JOBS if j.is_active]


def get_jobs_by_employer(employer: str) -> list[JobRequisition]:
    return [j for j in MOCK_JOBS if employer.lower() in j.employer.lower()]
