"""
app/services/multilingual_keywords.py
======================================
Multilingual keyword dictionary for ATS matching.
Covers: German (DE), English (EN), French (FR), Swedish (SV).
Designed for DACH + Nordic enterprise hiring (Deloitte, KPMG, Deutsche Bank,
Six Group, Accenture, Sparkasse, etc.)

Each entry maps a canonical skill/concept to its equivalents across all 4 languages.
The ATS engine normalises extracted keywords to the canonical form before scoring.
"""
from __future__ import annotations
from typing import Dict, List

# ─────────────────────────────────────────────────────────────────────────────
# CANONICAL → {lang: [synonyms]} mapping
# ─────────────────────────────────────────────────────────────────────────────

MULTILINGUAL_SKILLS: Dict[str, Dict[str, List[str]]] = {

    # ── Project / Programme Management ───────────────────────────────────────
    "project_management": {
        "de": ["projektmanagement", "projektleitung", "projektleiter", "projektmanager",
               "projektkoordination", "programmmanagement"],
        "en": ["project management", "project manager", "programme management",
               "project lead", "project coordinator", "pmo"],
        "fr": ["gestion de projet", "chef de projet", "coordinateur de projet",
               "management de projet", "directeur de projet"],
        "sv": ["projektledning", "projektledare", "projektkoordinator",
               "programledning", "projektchef"],
    },

    # ── Agile / Scrum ─────────────────────────────────────────────────────────
    "agile": {
        "de": ["agile", "scrum", "scrum master", "agiles projektmanagement",
               "kanban", "sprint", "backlog", "agile methoden", "safe"],
        "en": ["agile", "scrum", "scrum master", "kanban", "sprint planning",
               "backlog grooming", "scaled agile", "safe framework"],
        "fr": ["agile", "scrum", "méthode agile", "scrum master", "kanban",
               "sprint", "gestion agile"],
        "sv": ["agile", "scrum", "scrummaster", "kanban", "agila metoder",
               "sprint", "backlogg"],
    },

    # ── Data Analysis ─────────────────────────────────────────────────────────
    "data_analysis": {
        "de": ["datenanalyse", "datenauswertung", "business intelligence",
               "reporting", "datenvisualisierung", "analytik", "bi"],
        "en": ["data analysis", "data analytics", "business intelligence",
               "reporting", "data visualization", "analytics", "bi"],
        "fr": ["analyse de données", "analytique", "intelligence d'affaires",
               "reporting", "visualisation de données", "bi"],
        "sv": ["dataanalys", "affärsintelligens", "rapportering",
               "datavisualisering", "analytik", "bi"],
    },

    # ── Python ────────────────────────────────────────────────────────────────
    "python": {
        "de": ["python", "python programmierung", "python entwicklung"],
        "en": ["python", "python programming", "python development"],
        "fr": ["python", "programmation python", "développement python"],
        "sv": ["python", "python-programmering"],
    },

    # ── SQL / Databases ───────────────────────────────────────────────────────
    "sql": {
        "de": ["sql", "datenbankabfragen", "t-sql", "pl/sql", "mysql",
               "postgresql", "ms sql", "oracle sql", "datenbankmanagement"],
        "en": ["sql", "database queries", "t-sql", "pl/sql", "mysql",
               "postgresql", "ms sql server", "oracle", "database management"],
        "fr": ["sql", "bases de données", "requêtes sql", "gestion de base de données",
               "mysql", "postgresql"],
        "sv": ["sql", "databasfrågor", "databashantering", "mysql", "postgresql"],
    },

    # ── Machine Learning / AI ─────────────────────────────────────────────────
    "machine_learning": {
        "de": ["maschinelles lernen", "machine learning", "ml", "künstliche intelligenz",
               "ki", "deep learning", "neuronale netze", "nlp", "tensorflow", "pytorch"],
        "en": ["machine learning", "ml", "artificial intelligence", "ai",
               "deep learning", "neural networks", "nlp", "tensorflow", "pytorch"],
        "fr": ["apprentissage automatique", "machine learning", "intelligence artificielle",
               "ia", "deep learning", "réseaux de neurones", "nlp"],
        "sv": ["maskininlärning", "artificiell intelligens", "ai", "djupinlärning",
               "neurala nätverk", "nlp"],
    },

    # ── Cloud (Azure / AWS / GCP) ─────────────────────────────────────────────
    "cloud": {
        "de": ["cloud", "azure", "aws", "google cloud", "cloud computing",
               "cloud infrastruktur", "saas", "paas", "iaas", "azure devops"],
        "en": ["cloud", "azure", "aws", "google cloud platform", "cloud computing",
               "cloud infrastructure", "saas", "paas", "iaas", "azure devops"],
        "fr": ["cloud", "informatique en nuage", "azure", "aws",
               "infrastructure cloud", "saas", "paas"],
        "sv": ["molntjänster", "cloud", "azure", "aws", "molninfrastruktur",
               "saas", "paas"],
    },

    # ── Financial Accounting ───────────────────────────────────────────────────
    "accounting": {
        "de": ["buchhaltung", "rechnungswesen", "finanzbuchhaltung", "bilanzierung",
               "jahresabschluss", "hgb", "ifrs", "controlling", "kostenrechnung",
               "debitorenbuchhaltung", "kreditorenbuchhaltung", "sap fi"],
        "en": ["accounting", "financial accounting", "bookkeeping", "balance sheet",
               "financial statements", "ifrs", "gaap", "controlling",
               "accounts payable", "accounts receivable", "sap fi"],
        "fr": ["comptabilité", "comptabilité financière", "bilan", "états financiers",
               "ifrs", "pcg", "contrôle de gestion", "comptes fournisseurs"],
        "sv": ["redovisning", "bokföring", "finansiell redovisning", "balansräkning",
               "ifrs", "controlling", "leverantörsreskontra"],
    },

    # ── Risk Management ────────────────────────────────────────────────────────
    "risk_management": {
        "de": ["risikomanagement", "risikoanalyse", "compliance", "internes kontrollsystem",
               "iks", "operational risk", "kreditrisiko", "marktrisiko",
               "risikobewertung", "risikocontrolling"],
        "en": ["risk management", "risk analysis", "compliance", "internal control",
               "operational risk", "credit risk", "market risk",
               "risk assessment", "risk controlling", "erm"],
        "fr": ["gestion des risques", "analyse de risques", "conformité",
               "contrôle interne", "risque opérationnel", "risque de crédit"],
        "sv": ["riskhantering", "riskanalys", "regelefterlevnad",
               "intern kontroll", "operationell risk", "kreditrisk"],
    },

    # ── Audit ──────────────────────────────────────────────────────────────────
    "audit": {
        "de": ["wirtschaftsprüfung", "revision", "interne revision", "audit",
               "jahresabschlussprüfung", "prüfungswesen", "wirtschaftsprüfer",
               "cpa", "cia", "cfe"],
        "en": ["audit", "internal audit", "external audit", "statutory audit",
               "auditing", "cpa", "cia", "certified public accountant"],
        "fr": ["audit", "audit interne", "commissariat aux comptes", "révision",
               "contrôle légal", "expert-comptable"],
        "sv": ["revision", "intern revision", "extern revision", "revisor",
               "granskning", "godkänd revisor"],
    },

    # ── Consulting ─────────────────────────────────────────────────────────────
    "consulting": {
        "de": ["beratung", "unternehmensberatung", "consultant", "berater",
               "strategieberatung", "managementberatung", "it-beratung",
               "prozessberatung", "transformationsberatung"],
        "en": ["consulting", "management consulting", "consultant", "advisory",
               "strategy consulting", "it consulting", "business consulting",
               "transformation consulting"],
        "fr": ["conseil", "conseil en management", "consultant", "advisory",
               "conseil en stratégie", "conseil informatique"],
        "sv": ["konsulting", "managementkonsulting", "konsult", "rådgivning",
               "strategikonsulting", "it-konsulting"],
    },

    # ── SAP ────────────────────────────────────────────────────────────────────
    "sap": {
        "de": ["sap", "sap erp", "sap s/4hana", "sap fi", "sap co", "sap hr",
               "sap hcm", "sap basis", "sap abap", "sap bw", "sap sd", "sap mm"],
        "en": ["sap", "sap erp", "sap s/4hana", "sap fi", "sap co", "sap hr",
               "sap hcm", "sap abap", "sap bw", "sap sd", "sap mm"],
        "fr": ["sap", "sap erp", "sap s/4hana", "sap fi", "sap co", "sap rh",
               "sap abap"],
        "sv": ["sap", "sap erp", "sap s/4hana", "sap fi", "sap co", "sap hr"],
    },

    # ── Excel / Office ─────────────────────────────────────────────────────────
    "excel": {
        "de": ["excel", "microsoft excel", "pivot-tabellen", "vba", "makros",
               "ms office", "microsoft office", "powerpoint", "word"],
        "en": ["excel", "microsoft excel", "pivot tables", "vba", "macros",
               "ms office", "microsoft office", "powerpoint", "word"],
        "fr": ["excel", "microsoft excel", "tableaux croisés", "vba", "macros",
               "ms office", "microsoft office", "powerpoint"],
        "sv": ["excel", "microsoft excel", "pivottabeller", "vba", "makron",
               "ms office", "microsoft office", "powerpoint"],
    },

    # ── Communication ─────────────────────────────────────────────────────────
    "communication": {
        "de": ["kommunikation", "präsentation", "stakeholder management",
               "verhandlungsführung", "konfliktmanagement", "teamkommunikation"],
        "en": ["communication", "presentation", "stakeholder management",
               "negotiation", "conflict management", "team communication"],
        "fr": ["communication", "présentation", "gestion des parties prenantes",
               "négociation", "gestion des conflits"],
        "sv": ["kommunikation", "presentation", "intressenthantering",
               "förhandling", "konflikthantering"],
    },

    # ── Leadership ────────────────────────────────────────────────────────────
    "leadership": {
        "de": ["führung", "teamführung", "führungserfahrung", "personalführung",
               "team management", "mitarbeiterführung", "management"],
        "en": ["leadership", "team leadership", "people management",
               "management", "staff management", "team management"],
        "fr": ["leadership", "management d'équipe", "gestion d'équipe",
               "encadrement", "direction d'équipe"],
        "sv": ["ledarskap", "teamledning", "personalledning",
               "management", "chefskap"],
    },

    # ── Banking / Finance ─────────────────────────────────────────────────────
    "banking": {
        "de": ["bankwesen", "finanzdienstleistungen", "investment banking",
               "kreditgeschäft", "wertpapiere", "kapitalmarkt", "treasury",
               "corporate banking", "retail banking", "private banking"],
        "en": ["banking", "financial services", "investment banking",
               "lending", "securities", "capital markets", "treasury",
               "corporate banking", "retail banking", "private banking"],
        "fr": ["banque", "services financiers", "banque d'investissement",
               "crédit", "valeurs mobilières", "marchés de capitaux", "trésorerie"],
        "sv": ["bank", "finansiella tjänster", "investmentbank",
               "utlåning", "värdepapper", "kapitalmarknad", "treasury"],
    },

    # ── Compliance / Regulatory ───────────────────────────────────────────────
    "compliance": {
        "de": ["compliance", "regulierung", "mifid", "basel iii", "gdpr", "dsgvo",
               "aml", "geldwäscheprävention", "know your customer", "kyc",
               "bafin", "finma", "eba"],
        "en": ["compliance", "regulatory", "mifid", "basel iii", "gdpr",
               "aml", "anti-money laundering", "know your customer", "kyc",
               "fca", "sec", "finra"],
        "fr": ["conformité", "réglementaire", "mifid", "bâle iii", "rgpd",
               "lba", "blanchiment d'argent", "kyc", "amf", "acpr"],
        "sv": ["regelefterlevnad", "regulatorisk", "mifid", "basel iii", "gdpr",
               "aml", "penningtvätt", "kyc", "finansinspektionen"],
    },

    # ── Software Development ──────────────────────────────────────────────────
    "software_development": {
        "de": ["softwareentwicklung", "programmierung", "entwicklung", "coding",
               "java", "c#", ".net", "javascript", "typescript", "react",
               "rest api", "microservices", "devops", "ci/cd"],
        "en": ["software development", "programming", "coding", "development",
               "java", "c#", ".net", "javascript", "typescript", "react",
               "rest api", "microservices", "devops", "ci/cd"],
        "fr": ["développement logiciel", "programmation", "développement",
               "java", "c#", ".net", "javascript", "react",
               "api rest", "microservices", "devops"],
        "sv": ["mjukvaruutveckling", "programmering", "kodning", "utveckling",
               "java", "c#", ".net", "javascript", "react", "devops"],
    },

    # ── HR / Recruiting ───────────────────────────────────────────────────────
    "human_resources": {
        "de": ["personalwesen", "hr", "personalmanagement", "recruiting",
               "personalentwicklung", "talent management", "employer branding",
               "arbeitsrecht", "onboarding", "payroll", "lohnabrechnung"],
        "en": ["human resources", "hr", "people management", "recruiting",
               "talent development", "talent management", "employer branding",
               "employment law", "onboarding", "payroll"],
        "fr": ["ressources humaines", "rh", "gestion des personnes", "recrutement",
               "développement des talents", "droit du travail", "onboarding", "paie"],
        "sv": ["personalresurser", "hr", "personalledning", "rekrytering",
               "talangutveckling", "arbetsrätt", "onboarding", "löneadministration"],
    },

    # ── Tax ───────────────────────────────────────────────────────────────────
    "tax": {
        "de": ["steuern", "steuerberatung", "körperschaftsteuer", "umsatzsteuer",
               "gewerbesteuer", "einkommensteuer", "steuerrecht", "transfer pricing",
               "steuerplanung", "steuerrecht deutschland", "steuerberater"],
        "en": ["tax", "taxation", "tax advisory", "corporate tax", "vat",
               "income tax", "tax law", "transfer pricing", "tax planning",
               "tax compliance", "tax consultant"],
        "fr": ["fiscalité", "conseil fiscal", "impôt sur les sociétés", "tva",
               "impôt sur le revenu", "droit fiscal", "prix de transfert",
               "planification fiscale"],
        "sv": ["skatt", "skatterådgivning", "bolagsskatt", "moms",
               "inkomstskatt", "skattelagstiftning", "internprissättning"],
    },

    # ── Language Skills ───────────────────────────────────────────────────────
    "german_language": {
        "de": ["deutsch", "deutschkenntnisse", "muttersprache deutsch",
               "verhandlungssicheres deutsch", "fließend deutsch"],
        "en": ["german", "german language", "native german", "fluent german",
               "business german", "proficient in german"],
        "fr": ["allemand", "langue allemande", "allemand courant",
               "allemand des affaires"],
        "sv": ["tyska", "tyska språket", "flytande tyska", "affärstyska"],
    },

    "english_language": {
        "de": ["englisch", "englischkenntnisse", "fließend englisch",
               "verhandlungssicheres englisch", "business english"],
        "en": ["english", "english language", "fluent english", "native english",
               "business english", "proficient in english"],
        "fr": ["anglais", "langue anglaise", "anglais courant",
               "anglais des affaires"],
        "sv": ["engelska", "engelska språket", "flytande engelska"],
    },

    "french_language": {
        "de": ["französisch", "französischkenntnisse", "fließend französisch"],
        "en": ["french", "french language", "fluent french", "business french"],
        "fr": ["français", "langue française", "français courant", "natif français"],
        "sv": ["franska", "franska språket", "flytande franska"],
    },

    "swedish_language": {
        "de": ["schwedisch", "schwedischkenntnisse"],
        "en": ["swedish", "swedish language", "fluent swedish"],
        "fr": ["suédois", "langue suédoise"],
        "sv": ["svenska", "svenska språket", "modersmål svenska", "flytande svenska"],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Education level normalisation (multilingual)
# ─────────────────────────────────────────────────────────────────────────────

EDUCATION_LEVELS: Dict[str, Dict[str, List[str]]] = {
    "phd": {
        "de": ["promotion", "doktor", "dr.", "ph.d.", "doktortitel", "dissertation"],
        "en": ["phd", "doctorate", "ph.d.", "doctor of philosophy", "doctoral"],
        "fr": ["doctorat", "docteur", "ph.d.", "thèse"],
        "sv": ["doktorsexamen", "doktor", "ph.d.", "avhandling"],
    },
    "master": {
        "de": ["master", "masterarbeit", "m.sc.", "m.a.", "magister",
               "diplom", "diplom-kaufmann", "diplom-ingenieur"],
        "en": ["master", "master's degree", "msc", "ma", "mba",
               "master of science", "master of arts", "master of business"],
        "fr": ["master", "mastère", "m.sc.", "m.a.", "mba",
               "master en sciences", "grande école"],
        "sv": ["masterexamen", "master", "m.sc.", "civilingenjör", "civilekonom"],
    },
    "bachelor": {
        "de": ["bachelor", "b.sc.", "b.a.", "bachelorstudium",
               "fachhochschulabschluss", "fh-abschluss"],
        "en": ["bachelor", "bachelor's degree", "bsc", "ba", "undergraduate",
               "bachelor of science", "bachelor of arts"],
        "fr": ["licence", "bachelor", "b.sc.", "b.a.", "licence professionnelle"],
        "sv": ["kandidatexamen", "bachelor", "b.sc.", "högskoleexamen"],
    },
    "vocational": {
        "de": ["ausbildung", "berufsausbildung", "kaufmann", "kauffrau",
               "fachabitur", "berufsschule", "azubi", "apprenticeship"],
        "en": ["vocational training", "apprenticeship", "trade qualification",
               "nvq", "btec", "hnd"],
        "fr": ["bac professionnel", "bts", "dut", "cap", "formation professionnelle"],
        "sv": ["yrkesutbildning", "lärlingsutbildning", "gymnasieexamen yrkesprogrammet"],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Certification mappings
# ─────────────────────────────────────────────────────────────────────────────

CERTIFICATIONS: Dict[str, List[str]] = {
    "pmp": ["pmp", "project management professional", "pmi-pmp"],
    "prince2": ["prince2", "prince 2", "prince2 practitioner"],
    "scrum_master": ["csm", "certified scrum master", "psm", "professional scrum master"],
    "cpa": ["cpa", "certified public accountant", "wirtschaftsprüfer", "expert-comptable"],
    "cia": ["cia", "certified internal auditor"],
    "cfa": ["cfa", "chartered financial analyst"],
    "frm": ["frm", "financial risk manager"],
    "azure_cert": ["az-900", "az-104", "az-204", "az-305", "az-400",
                   "microsoft certified azure", "azure fundamentals",
                   "azure administrator", "azure developer", "azure architect"],
    "aws_cert": ["aws certified", "aws solutions architect", "aws developer",
                 "aws sysops", "aws cloud practitioner"],
    "six_sigma": ["six sigma", "lean six sigma", "black belt", "green belt",
                  "six sigma black belt", "ssbb"],
    "itil": ["itil", "itil 4", "itil foundation", "itil practitioner"],
    "iso_27001": ["iso 27001", "iso/iec 27001", "information security"],
    "cissp": ["cissp", "certified information systems security professional"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build reverse lookup (keyword → canonical)
# ─────────────────────────────────────────────────────────────────────────────

def _build_reverse_lookup() -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for canonical, langs in MULTILINGUAL_SKILLS.items():
        for lang, terms in langs.items():
            for term in terms:
                lookup[term.lower()] = canonical
    return lookup


def _build_edu_reverse_lookup() -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for level, langs in EDUCATION_LEVELS.items():
        for lang, terms in langs.items():
            for term in terms:
                lookup[term.lower()] = level
    return lookup


def _build_cert_reverse_lookup() -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for canonical, terms in CERTIFICATIONS.items():
        for term in terms:
            lookup[term.lower()] = canonical
    return lookup


# Pre-built at import time for O(1) lookups
SKILL_REVERSE: Dict[str, str] = _build_reverse_lookup()
EDU_REVERSE: Dict[str, str] = _build_edu_reverse_lookup()
CERT_REVERSE: Dict[str, str] = _build_cert_reverse_lookup()


def normalise_skill(term: str) -> str | None:
    """Return canonical skill key for a term, or None if not recognised."""
    return SKILL_REVERSE.get(term.lower().strip())


def normalise_education(term: str) -> str | None:
    """Return education level for a term, or None."""
    return EDU_REVERSE.get(term.lower().strip())


def normalise_certification(term: str) -> str | None:
    """Return canonical cert key for a term, or None."""
    return CERT_REVERSE.get(term.lower().strip())


def get_all_terms_for_skill(canonical: str) -> List[str]:
    """Return all multilingual terms for a canonical skill key."""
    skill = MULTILINGUAL_SKILLS.get(canonical, {})
    terms = []
    for lang_terms in skill.values():
        terms.extend(lang_terms)
    return [t.lower() for t in terms]
