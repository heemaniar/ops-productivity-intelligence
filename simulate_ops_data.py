"""
simulate_ops_data.py — Operations Productivity Intelligence synthetic dataset.

Generates Salesforce-style *Case* data for an Operations / Client Services team
that supports financial advisors selling life insurance & annuity products from
multiple carriers (vendors). Output is a clean star schema (4 dims + 2 facts)
designed to land in BigQuery and be analyzed in Looker / Looker Studio, plus
free-text fields rich enough for LLM ticket-pattern clustering and knowledge-base
content generation.

Output (CSVs into ./data/):
    dim_agent.csv          ~8   ops team members
    dim_client.csv         ~120 advisory firms (Salesforce Accounts)
    dim_vendor.csv         ~12  insurance carriers
    dim_case_type.csv      ~28  case-type catalog (the "ticket taxonomy")
    fact_cases.csv         7500 cases (the Salesforce Case object)
    fact_case_comments.csv ~15k threaded client/agent messages

Story baked into the data
─────────────────────────
A knowledge-base (KB) program launches 2025-09-01. After launch, the
KB-addressable case types show ~25% lower handle time & first-response time,
higher first-contact-resolution, and fewer reopens — the "↑25% operational
efficiency" narrative the dashboard is meant to tell.

⚠️  DISCLAIMER: 100% synthetic. Carrier names are real companies used only as
realistic labels; all clients, advisors, agents, cases, messages, dollar
amounts and metrics are fictitious and represent no real person or company.

Run:
    python simulate_ops_data.py
"""

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(7)
np.random.seed(7)

DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(parents=True, exist_ok=True)

# ── Simulation window ─────────────────────────────────────────────────────────
START = datetime(2024, 12, 1)
END   = datetime(2026, 5, 29)
KB_LAUNCH = datetime(2025, 9, 1)        # knowledge-base program go-live
N_CASES = 7500

# ── US business holidays in window (no/low case creation) ─────────────────────
_HOLIDAYS = {
    date(2024, 12, 25), date(2025, 1, 1), date(2025, 1, 20), date(2025, 2, 17),
    date(2025, 5, 26), date(2025, 7, 4), date(2025, 9, 1), date(2025, 11, 27),
    date(2025, 12, 25), date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16),
    date(2026, 5, 25),
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. VENDORS (carriers)
# ══════════════════════════════════════════════════════════════════════════════
# product_lines: A=Annuity, L=Life, B=Both
_VENDORS = [
    # name,                  lines, portal,             avg_proc_days
    ("Pacific Life",          "B", "PacificXpress",      9),
    ("Lincoln Financial",     "B", "LincolnDesktop",    11),
    ("Nationwide",            "B", "Nationwide@Work",    8),
    ("Athene",                "A", "Athene Connect",     7),
    ("Allianz Life",          "A", "Allianz ACT",       10),
    ("Prudential",            "B", "Prudential eOffice", 12),
    ("MassMutual",            "L", "MM FieldNet",       13),
    ("Jackson National",      "A", "Jackson InfoSource", 8),
    ("Brighthouse Financial", "B", "Brighthouse e-App",  9),
    ("Corebridge Financial",  "B", "Corebridge Connect",10),
    ("Equitable",             "B", "Equitable EQ",      11),
    ("Symetra",               "A", "Symetra eApp",       7),
]

vendor_rows = []
for i, (name, lines, portal, proc) in enumerate(_VENDORS, 1):
    vendor_rows.append({
        "vendor_id":        f"VEN{i:03d}",
        "vendor_name":      name,
        "product_lines":    {"A": "Annuity", "L": "Life", "B": "Life & Annuity"}[lines],
        "portal_name":      portal,
        "avg_processing_days": proc,
    })
dim_vendor = pd.DataFrame(vendor_rows)
_VENDOR_LINES = {r["vendor_id"]: lines for r, (_, lines, _, _) in zip(vendor_rows, _VENDORS)}

_LIFE_PRODUCTS = [
    "Term Life", "Whole Life", "Universal Life",
    "Indexed Universal Life (IUL)", "Variable Universal Life (VUL)", "Final Expense",
]
_ANNUITY_PRODUCTS = [
    "Fixed Annuity", "Fixed Indexed Annuity (FIA)", "Variable Annuity",
    "Immediate Annuity (SPIA)", "Deferred Income Annuity", "MYGA", "RILA",
]


# ══════════════════════════════════════════════════════════════════════════════
# 2. AGENTS (ops team — 8 people)
# ══════════════════════════════════════════════════════════════════════════════
_AGENTS = [
    # name,              role,                  specialization,        hire,        seniority
    ("Marcus Bell",      "Operations Team Lead", "New Business",       "2019-03-04", 6.2),
    ("Priya Nair",       "Senior Ops Specialist","Annuity Servicing",  "2020-06-15", 5.0),
    ("Diego Ramirez",    "Senior Ops Specialist","Claims & Maturity",  "2021-01-11", 4.4),
    ("Aisha Khan",       "Ops Specialist",       "New Business",       "2022-09-06", 2.8),
    ("Tom Whitfield",    "Ops Specialist",       "In-Force Service",   "2023-02-20", 2.3),
    ("Yuki Tanaka",      "Ops Specialist",       "Annuity Servicing",  "2023-08-14", 1.8),
    ("Sofia Romano",     "Ops Specialist",       "In-Force Service",   "2024-04-01", 1.2),
    ("Jamal Carter",     "Ops Associate",        "Documents & Intake", "2024-10-07", 0.6),
]
agent_rows = []
for i, (name, role, spec, hire, sen) in enumerate(_AGENTS, 1):
    agent_rows.append({
        "agent_id":       f"AGT{i:02d}",
        "agent_name":     name,
        "role":           role,
        "team":           "Client Services Operations",
        "specialization": spec,
        "hire_date":      hire,
        "seniority_years": sen,
    })
dim_agent = pd.DataFrame(agent_rows)
AGENT_IDS = dim_agent["agent_id"].tolist()
# Routing weight: leads/seniors carry slightly fewer but harder cases.
_AGENT_LOAD = np.array([0.09, 0.13, 0.12, 0.15, 0.15, 0.14, 0.13, 0.09])
_AGENT_SKILL = dict(zip(AGENT_IDS, [0.95, 0.92, 0.90, 0.84, 0.82, 0.80, 0.78, 0.70]))  # FCR / speed multiplier


# ══════════════════════════════════════════════════════════════════════════════
# 3. CLIENTS (Salesforce Accounts — advisory firms / agencies)  ~120
# ══════════════════════════════════════════════════════════════════════════════
_FIRM_PREFIX = [
    "Summit", "Granite", "Beacon", "Cedar", "Harbor", "Pinnacle", "Northstar",
    "Evergreen", "Liberty", "Cornerstone", "Heritage", "Meridian", "Sterling",
    "Oakmont", "Vanguard", "Bluestone", "Keystone", "Trinity", "Anchor", "Magnolia",
    "Crestview", "Redwood", "Birchwood", "Sequoia", "Highland", "Riverbend",
    "Fairway", "Westbridge", "Lakeshore", "Sundial",
]
_FIRM_SUFFIX = [
    "Financial Group", "Wealth Partners", "Insurance Services", "Advisory",
    "Capital", "Retirement Solutions", "Financial Advisors", "Benefits Group",
    "Wealth Management", "Insurance Agency", "Financial Network", "& Associates",
]
_CLIENT_TYPES = ["Independent Advisor", "IMO", "BGA", "RIA", "Bank Channel", "Wirehouse Branch"]
_REGIONS = {
    "West":      ["CA", "WA", "OR", "AZ", "CO", "NV"],
    "Midwest":   ["IL", "OH", "MI", "MN", "WI", "MO"],
    "Northeast": ["NY", "NJ", "MA", "PA", "CT"],
    "South":     ["TX", "FL", "GA", "NC", "TN", "VA"],
}
_FIRST_NAMES = ["James", "Mary", "Robert", "Linda", "Michael", "Patricia", "David",
                "Jennifer", "William", "Elizabeth", "Richard", "Susan", "Joseph",
                "Karen", "Daniel", "Nancy", "Paul", "Carol", "Mark", "Sandra",
                "George", "Donna", "Kevin", "Sharon", "Brian", "Cynthia"]
_LAST_NAMES = ["Anderson", "Thompson", "Martinez", "Robinson", "Clark", "Walker",
               "Hall", "Allen", "Young", "King", "Wright", "Scott", "Green",
               "Baker", "Adams", "Nelson", "Hill", "Mitchell", "Roberts", "Turner",
               "Phillips", "Campbell", "Parker", "Evans", "Edwards", "Collins"]

def _person():
    return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"

_used_firms = set()
client_rows = []
for i in range(1, 121):
    while True:
        name = f"{random.choice(_FIRM_PREFIX)} {random.choice(_FIRM_SUFFIX)}"
        if name not in _used_firms:
            _used_firms.add(name)
            break
    region = random.choice(list(_REGIONS))
    ctype = random.choices(_CLIENT_TYPES, weights=[30, 12, 14, 20, 12, 12])[0]
    book = int(np.random.lognormal(mean=5.0, sigma=0.9))   # policies under management
    book = max(8, min(book, 2400))
    if book >= 600:
        segment = "Enterprise"
    elif book >= 120:
        segment = "Mid-Market"
    else:
        segment = "Small"
    onboard = (START - timedelta(days=random.randint(60, 2200))).date()
    client_rows.append({
        "client_id":        f"CLI{i:04d}",
        "client_name":      name,
        "client_type":      ctype,
        "segment":          segment,
        "region":           region,
        "state":            random.choice(_REGIONS[region]),
        "book_size_policies": book,
        "primary_contact":  _person(),
        "onboarded_date":   onboard.isoformat(),
    })
dim_client = pd.DataFrame(client_rows)
CLIENT_IDS = dim_client["client_id"].tolist()
# Bigger books open more cases.
_client_weight = dim_client["book_size_policies"].to_numpy(dtype=float)
_client_weight = _client_weight / _client_weight.sum()
_CLIENT_CONTACT = dict(zip(dim_client["client_id"], dim_client["primary_contact"]))


# ══════════════════════════════════════════════════════════════════════════════
# 4. CASE-TYPE CATALOG (the ticket taxonomy)  — 28 types
# ══════════════════════════════════════════════════════════════════════════════
# Fields per type:
#   category, subcategory, name, default_priority, sla_hours,
#   base_handle_min, fcr_rate, reopen_rate, escalation_rate, weight, kb_addressable
_CASE_TYPES = [
    # ── Product Information & Suitability ────────────────────────────────────
    ("Product Information", "Features & Riders", "Product feature / rider question",
        "Medium", 24,  22, 0.78, 0.05, 0.03, 6.0, True),
    ("Product Information", "Rates & Crediting", "Annuity rate / crediting question",
        "Medium", 24,  18, 0.80, 0.04, 0.02, 5.0, True),
    ("Product Information", "Comparison", "Cross-vendor product comparison",
        "Low",    48,  35, 0.60, 0.07, 0.04, 3.5, True),
    ("Product Information", "Suitability", "Suitability / illustration request",
        "Medium", 24,  40, 0.55, 0.10, 0.08, 4.5, False),
    # ── New Business: Application & Submission ───────────────────────────────
    ("New Business", "Application Help", "Application form completion help",
        "Medium", 24,  28, 0.62, 0.10, 0.05, 7.5, True),
    ("New Business", "NIGO", "Missing / incomplete application info (NIGO)",
        "High",   16,  34, 0.45, 0.22, 0.10, 9.0, True),
    ("New Business", "E-Signature", "E-signature / DocuSign issue",
        "High",   8,   16, 0.70, 0.08, 0.06, 5.5, True),
    ("New Business", "Submission", "Submission to carrier portal failed",
        "High",   8,   24, 0.58, 0.12, 0.14, 4.5, False),
    ("New Business", "Status", "Application status check",
        "Low",    24,  10, 0.88, 0.06, 0.02, 8.5, True),
    ("New Business", "Underwriting", "Underwriting requirement / medical exam",
        "Medium", 24,  30, 0.50, 0.16, 0.12, 5.5, False),
    # ── Documents & Forms ────────────────────────────────────────────────────
    ("Documents", "Form Request", "Required documents / forms list request",
        "Low",    24,  12, 0.85, 0.05, 0.02, 6.5, True),
    ("Documents", "Wrong Form", "Wrong / outdated form version",
        "Medium", 24,  15, 0.72, 0.10, 0.04, 3.5, True),
    ("Documents", "Upload", "Document upload failure",
        "Medium", 16,  14, 0.74, 0.09, 0.05, 3.0, True),
    ("Documents", "1035 Exchange", "Replacement / 1035 exchange paperwork",
        "High",   24,  45, 0.40, 0.20, 0.16, 4.0, False),
    # ── In-Force Policy Servicing ────────────────────────────────────────────
    ("Policy Servicing", "Beneficiary", "Beneficiary change request",
        "Medium", 24,  20, 0.68, 0.12, 0.05, 6.0, True),
    ("Policy Servicing", "Contact Update", "Address / contact info update",
        "Low",    24,  10, 0.90, 0.04, 0.01, 4.5, True),
    ("Policy Servicing", "Billing", "Premium payment / billing question",
        "Medium", 16,  22, 0.66, 0.12, 0.06, 5.5, True),
    ("Policy Servicing", "Cash Value", "Policy values / cash value inquiry",
        "Low",    24,  18, 0.75, 0.07, 0.03, 4.5, True),
    ("Policy Servicing", "Loan/Withdrawal", "Policy loan or withdrawal request",
        "Medium", 24,  30, 0.55, 0.14, 0.08, 3.5, False),
    ("Policy Servicing", "Annuity Growth", "Annuity annual growth / statement question",
        "Low",    24,  20, 0.72, 0.08, 0.03, 5.0, True),
    # ── Process & Workflow ───────────────────────────────────────────────────
    ("Process", "Commission", "Commission / compensation question",
        "Medium", 24,  24, 0.64, 0.12, 0.07, 4.0, True),
    ("Process", "Licensing", "Carrier appointment / licensing question",
        "Medium", 24,  26, 0.60, 0.12, 0.06, 3.5, True),
    ("Process", "How-To", "General process / how-to question",
        "Low",    24,  14, 0.82, 0.05, 0.02, 5.0, True),
    # ── Claims & Maturity ────────────────────────────────────────────────────
    ("Claims & Maturity", "Death Claim", "Death claim filing assistance",
        "Critical", 8,  50, 0.35, 0.18, 0.20, 2.5, False),
    ("Claims & Maturity", "Annuitization", "Annuitization / maturity question",
        "Medium", 24,  34, 0.52, 0.12, 0.08, 2.5, False),
    ("Claims & Maturity", "Surrender", "Surrender / full withdrawal request",
        "High",   16,  32, 0.50, 0.14, 0.10, 2.5, False),
    # ── Technical / Access & Data ────────────────────────────────────────────
    ("Technical", "Access", "Portal login / access issue",
        "High",   8,   12, 0.76, 0.08, 0.05, 4.0, True),
    ("Technical", "Data Request", "Book-of-business data / report request",
        "Low",    24,  26, 0.70, 0.08, 0.04, 4.5, True),
]

ctype_rows, _CT = [], {}
for i, (cat, sub, name, pri, sla, hand, fcr, reo, esc, wt, kb) in enumerate(_CASE_TYPES, 1):
    cid = f"CT{i:03d}"
    ctype_rows.append({
        "case_type_id":     cid,
        "category":         cat,
        "subcategory":      sub,
        "case_type_name":   name,
        "default_priority": pri,
        "sla_target_hours": sla,
        "base_handle_minutes": hand,
        "fcr_rate":         fcr,
        "reopen_rate":      reo,
        "escalation_rate":  esc,
        "kb_addressable":   kb,
    })
    _CT[cid] = dict(cat=cat, sub=sub, name=name, pri=pri, sla=sla, hand=hand,
                    fcr=fcr, reo=reo, esc=esc, wt=wt, kb=kb)
dim_case_type = pd.DataFrame(ctype_rows)
CT_IDS = list(_CT)
_CT_WEIGHTS = np.array([_CT[c]["wt"] for c in CT_IDS])
_CT_WEIGHTS = _CT_WEIGHTS / _CT_WEIGHTS.sum()


# ══════════════════════════════════════════════════════════════════════════════
# 5. DESCRIPTION TEMPLATES (client's inbound message) per case type
# ══════════════════════════════════════════════════════════════════════════════
# Each list = subject + body templates with slots {vendor}{product}{client}
# {policy}{amount}{days}{contact}. Multiple variants → realistic clustering.
_TPL = {
    "CT001": ["Hi team, my client is asking which riders are available on the {product} from {vendor}. Can you confirm if a long-term care rider is offered and the cost?",
              "Quick question on {vendor} {product} — does it include a guaranteed income rider, and what's the rider charge?",
              "Client wants to add a chronic illness rider to the {product} we're writing with {vendor}. Is that available and what are the limits?"],
    "CT002": ["What is the current cap rate and participation rate on the {vendor} {product}? Client is comparing crediting strategies.",
              "Can you pull the latest declared rate for the {vendor} {product}? Quoting a client this afternoon.",
              "Client on the {vendor} {product} wants to know the renewal rate for year 2 — where do I find that?"],
    "CT003": ["I need to compare the {product} across {vendor} and one other carrier for a client. Can ops put together a side-by-side?",
              "Which carrier has the strongest {product} right now for a 62-year-old? Looking at {vendor} but open to alternatives."],
    "CT004": ["Please run a suitability illustration on the {product} with {vendor} for a {amount} premium, client age 58.",
              "Need a {product} illustration from {vendor} showing income at age 65 on a {amount} deposit."],
    "CT005": ["I'm filling out the {vendor} application for a {product} and I'm stuck on the financial suitability section. Can you walk me through it?",
              "Help — the {vendor} e-App for the {product} won't let me move past the replacement questions. What am I missing?",
              "First time submitting to {vendor}. Which sections of the {product} app are required vs optional?"],
    "CT006": ["{vendor} kicked back the {product} application as NIGO — missing the signed disclosure form. Can you tell me exactly what they need?",
              "Got a NIGO notice from {vendor} on policy {policy}. The {product} app is missing a date on the owner signature. How do I fix it?",
              "My {product} submission to {vendor} is showing NIGO for 'incomplete beneficiary info.' What needs to be corrected?"],
    "CT007": ["The DocuSign envelope for my client's {vendor} {product} app expired before they signed. Can you resend it?",
              "Client says they never got the e-signature email for the {product} with {vendor}. Can ops re-trigger it to {contact}?",
              "E-signature on the {vendor} {product} is stuck 'in progress' — the second signer can't access it."],
    "CT008": ["I tried submitting the {product} app on {vendor}'s portal and it failed with an error. Order isn't showing up. Help?",
              "The {vendor} {portal} submission for policy {policy} errored out twice. Did it go through or do I resubmit?"],
    "CT009": ["Can you check the status of my {product} application with {vendor} for {contact}? Submitted {days} days ago.",
              "Any update on the {vendor} {product} app for policy {policy}? Client keeps asking.",
              "Where does my pending {product} case with {vendor} stand — still in underwriting?"],
    "CT010": ["{vendor} is requiring a paramed exam for the {product}. How does my client schedule it and what's the turnaround?",
              "Underwriting on the {product} with {vendor} asked for an APS. What is that and how long will it add?"],
    "CT011": ["What forms do I need to submit a {product} with {vendor}? Want to get everything in good order up front.",
              "Can you send me the full document checklist for a {vendor} {product} application?"],
    "CT012": ["I think I used an old version of the {vendor} {product} replacement form. Can you send the current one?",
              "{vendor} says the {product} form I submitted is outdated. Which version should I be using?"],
    "CT013": ["The document upload on {vendor}'s {portal} keeps failing for my {product} case. File is a PDF under 5MB.",
              "I can't attach the client's ID to the {product} submission on {vendor} — upload spins and fails."],
    "CT014": ["Client wants to 1035 exchange an old annuity into the {vendor} {product}. What paperwork is required and how long does it take?",
              "Doing a 1035 exchange of {amount} into a {product} at {vendor}. Need the transfer forms and a timeline."],
    "CT015": ["Client needs to change the beneficiary on policy {policy} with {vendor}. What form and does it need a signature guarantee?",
              "Please help me update beneficiaries on a {vendor} {product} — client is divorcing and wants ex removed."],
    "CT016": ["Client moved. Need to update the mailing address on their {vendor} {product}, policy {policy}.",
              "Please update the phone and email on file for {contact} on their {vendor} policy."],
    "CT017": ["Client's premium payment on the {vendor} {product} didn't draft this month. Can you check why?",
              "How do I switch policy {policy} with {vendor} from annual to monthly EFT billing?"],
    "CT018": ["Client wants to know the current cash value on their {vendor} {product}, policy {policy}.",
              "What's the surrender value today on the {product} with {vendor}? Client is weighing options."],
    "CT019": ["Client needs to take a {amount} withdrawal from their {vendor} {product}. What's the process and any penalty?",
              "How do we set up a policy loan against the {vendor} {product} for {contact}?"],
    "CT020": ["Client got their annual statement and wants to understand how the {vendor} {product} grew this year. Can you explain the interest credited?",
              "The {product} with {vendor} shows lower growth than expected on the annual statement. Can ops break down the crediting?",
              "Client asks why their fixed indexed annuity at {vendor} credited 0% this period. Help me explain it."],
    "CT021": ["I haven't received commission on the {vendor} {product} that issued {days} days ago. Can you check the comp?",
              "Commission on policy {policy} looks short. Can ops confirm the rate paid on the {product}?"],
    "CT022": ["I need to get appointed with {vendor} to sell the {product}. What's the process and how long?",
              "Is my appointment with {vendor} active? Trying to submit a {product} and it's blocking me."],
    "CT023": ["New to the platform — how do I submit a {product} case end to end? Looking for a step-by-step.",
              "What's the workflow for getting a {vendor} {product} from quote to issue? Just want to understand the process."],
    "CT024": ["My client passed away. Need to start a death claim on their {vendor} {product}, policy {policy}. What does the family need to provide?",
              "Filing a death claim on a {vendor} {product}. Beneficiary is asking about timeline and documents — please advise."],
    "CT025": ["Client's deferred annuity with {vendor} is reaching maturity. How do we annuitize and what are the payout options?",
              "The {product} at {vendor} matures next month. Client wants lifetime income — walk me through annuitization."],
    "CT026": ["Client wants to fully surrender their {vendor} {product}, policy {policy}. What's the surrender charge and tax impact?",
              "Need to process a full surrender of {amount} on the {product} with {vendor}. Send me the forms."],
    "CT027": ["I can't log into {vendor}'s {portal} — password reset isn't working. Need access to submit a {product} today.",
              "Locked out of {portal} for {vendor}. Can you help me regain access?"],
    "CT028": ["Can ops pull a book-of-business report for all my in-force policies with {vendor}? Need it for a client review.",
              "I need a data export of my pending and issued {product} cases this quarter. Can you generate that?"],
}

# ── Text-noising layer ────────────────────────────────────────────────────────
# Real inbound messages are messy: greetings, filler, sign-offs, typos, and
# shared vocabulary across ticket types. Without this the templated text is
# trivially separable and any clustering "discovery" would be circular. This
# injects realistic noise + cross-type lexical overlap so an unsupervised model
# (and the ARI validation in ml_patterns.py) faces a fair task.
# NOTE: boilerplate vocabulary is deliberately DISJOINT from ticket content words
# (no "form", "missing", "wrong", "status", "time", etc.) so it adds realistic
# noise without colliding with real signal. The exact tokens are written to
# data/boilerplate_stopwords.txt for ml_patterns.py to curate out.
_GREETINGS = ["Hi team, ", "Hey ops, ", "Hello, ", "Good morning, ", "Hi folks, ",
              "Quick one — ", "Morning all, ", "Hi, ", "", "", ""]
_FILLERS = ["", "", " Let me know whenever you get a chance.", " No big rush on my end.",
            " Happy to jump on a call if that's easier.", " Reaching out on behalf of my advisor.",
            " Wanted to get this in front of you.", " Cc'ing myself here for the record.",
            " Looping you in early on this one.", " Whenever you get a sec."]
_SIGNOFFS = ["", "", " Thanks!", " Cheers.", " Appreciate it.",
             " Regards.", " TIA.", " Thank you!", " Thanks so much."]
_SYNONYMS = {  # applied probabilistically → cross-type vocabulary overlap
    "application": ["application", "app", "submission"],
    "client": ["client", "customer", "policyholder"],
    "documents": ["documents", "docs", "paperwork"],
    "question": ["question", "query"],
    "Can you": ["Can you", "Could you", "Would you be able to"],
    "Need to": ["Need to", "I need to", "Have to"],
}

def _typo(word):
    """Occasionally introduce a realistic typo (drop/swap a char)."""
    if len(word) < 4 or random.random() > 0.04:
        return word
    i = random.randint(1, len(word) - 2)
    if random.random() < 0.5:                       # drop a char
        return word[:i] + word[i + 1:]
    return word[:i] + word[i + 1] + word[i] + word[i + 2:]  # swap adjacent

def _noise(text):
    for canonical, variants in _SYNONYMS.items():
        if canonical in text and random.random() < 0.6:
            text = text.replace(canonical, random.choice(variants), 1)
    text = " ".join(_typo(w) for w in text.split())
    return f"{random.choice(_GREETINGS)}{text}{random.choice(_FILLERS)}{random.choice(_SIGNOFFS)}".strip()

def _fill(cid, vendor_name, portal, product, contact):
    tpl = random.choice(_TPL[cid])
    filled = tpl.format(
        vendor=vendor_name, portal=portal, product=product, contact=contact,
        policy=f"{random.randint(10**7, 10**8 - 1)}",
        amount=f"${random.choice([25,50,75,100,150,200,250,500])},000",
        days=random.choice([3, 5, 7, 10, 14, 21]),
    )
    return _noise(filled)

# Short agent resolution summaries (seed KB content) per category.
_RESOLUTION = {
    "Product Information": "Provided product spec/rate details and confirmed rider availability; advisor able to proceed.",
    "New Business":        "Identified the in-good-order requirement, corrected the application, and confirmed clean resubmission.",
    "Documents":           "Supplied the current form/checklist and confirmed successful submission.",
    "Policy Servicing":    "Processed the in-force service request and confirmed the update with the carrier.",
    "Process":             "Explained the workflow/comp/appointment step and provided reference materials.",
    "Claims & Maturity":   "Initiated the claim/maturity workflow, listed required documents, and set timeline expectations.",
    "Technical":           "Restored portal access / delivered the requested data export.",
}


# ══════════════════════════════════════════════════════════════════════════════
# 6. TIME-SAMPLING HELPERS
# ══════════════════════════════════════════════════════════════════════════════
_TOTAL_DAYS = (END - START).days

def _sample_created():
    """Business-hours-weighted, weekday-weighted, mildly growing creation time."""
    for _ in range(50):
        # Growth: more recent days slightly more likely.
        u = np.random.random()
        frac = u ** 0.85
        d = START + timedelta(days=int(frac * _TOTAL_DAYS))
        wd = d.weekday()
        if wd >= 5 and random.random() < 0.92:      # mostly skip weekends
            continue
        if d.date() in _HOLIDAYS and random.random() < 0.9:
            continue
        break
    # Business-hours: peak 9–12 and 13–16, tail to 18, rare off-hours.
    hour = int(np.random.choice(
        range(7, 20),
        p=np.array([1,4,9,11,11,7,9,11,10,7,4,2,1]) / 87.0))
    minute = random.randint(0, 59)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)

def _add_business_hours(start_dt, hours):
    """Advance by `hours` counting only Mon–Fri 8:00–18:00."""
    remaining = timedelta(hours=hours)
    cur = start_dt
    step = timedelta(minutes=15)
    while remaining > timedelta(0):
        cur += step
        if cur.weekday() < 5 and 8 <= cur.hour < 18 and cur.date() not in _HOLIDAYS:
            remaining -= step
    return cur.replace(second=0, microsecond=0)


# ══════════════════════════════════════════════════════════════════════════════
# 7. GENERATE CASES
# ══════════════════════════════════════════════════════════════════════════════
_ORIGINS = ["Email", "Phone", "Web Portal", "Chat"]
_ORIGIN_W = [0.46, 0.24, 0.20, 0.10]
_PRIORITY_SPEED = {"Low": 1.15, "Medium": 1.0, "High": 0.8, "Critical": 0.6}

# Intake mis-tagging: whoever opens the case sometimes picks the wrong queue.
# Flips only happen between genuinely confusable categories, mirroring real
# Salesforce data — and it's the reason LLM re-classification has value.
_MISTAG_RATE = 0.12
_CONFUSABLE = {
    "New Business":        ["Documents", "Technical", "Process"],
    "Documents":           ["New Business", "Policy Servicing"],
    "Technical":           ["New Business"],
    "Process":             ["New Business", "Product Information"],
    "Policy Servicing":    ["Claims & Maturity", "Product Information", "Documents"],
    "Claims & Maturity":   ["Policy Servicing"],
    "Product Information": ["Policy Servicing", "Process"],
}

def _tag_category(true_cat):
    """Return (recorded_category, is_mistagged)."""
    if random.random() < _MISTAG_RATE and _CONFUSABLE.get(true_cat):
        return random.choice(_CONFUSABLE[true_cat]), True
    return true_cat, False

rows = []
comment_rows = []
case_counter = 100001

# Pre-sample creation datetimes and sort so case numbers are chronological.
created_list = sorted(_sample_created() for _ in range(N_CASES))

for created in created_list:
    case_counter += 1
    case_number = f"{case_counter:08d}"
    case_id = f"500A{random.randint(10**11, 10**12 - 1)}"

    # Case type & vendor (vendor must match product line).
    cid = np.random.choice(CT_IDS, p=_CT_WEIGHTS)
    ct = _CT[cid]
    category_tagged, is_mistagged = _tag_category(ct["cat"])
    vrow = dim_vendor.sample(1).iloc[0]
    vlines = _VENDOR_LINES[vrow["vendor_id"]]
    if vlines == "A":
        product = random.choice(_ANNUITY_PRODUCTS)
        product_line = "Annuity"
    elif vlines == "L":
        product = random.choice(_LIFE_PRODUCTS)
        product_line = "Life"
    else:
        if random.random() < 0.5:
            product, product_line = random.choice(_LIFE_PRODUCTS), "Life"
        else:
            product, product_line = random.choice(_ANNUITY_PRODUCTS), "Annuity"

    client_id = np.random.choice(CLIENT_IDS, p=_client_weight)
    contact = _CLIENT_CONTACT[client_id]
    owner = np.random.choice(AGENT_IDS, p=_AGENT_LOAD)
    skill = _AGENT_SKILL[owner]

    origin = random.choices(_ORIGINS, weights=_ORIGIN_W)[0]
    priority = ct["pri"]

    # Post-KB efficiency lift for KB-addressable types.
    post_kb = created >= KB_LAUNCH
    kb_lift = 1.0
    if post_kb and ct["kb"]:
        # ramp from 1.0 at launch toward ~0.64 (≈36% faster) as KB matures
        months = (created - KB_LAUNCH).days / 30.0
        kb_lift = max(0.64, 1.0 - 0.065 * months)

    # ── First response (created → first agent touch), business-aware ──────────
    fr_base = {"Email": 90, "Phone": 4, "Web Portal": 120, "Chat": 6}[origin]
    fr_min = max(1, np.random.lognormal(np.log(fr_base), 0.7)
                 * _PRIORITY_SPEED[priority] * (2 - skill) * kb_lift)
    first_response_at = _add_business_hours(created, fr_min / 60.0)
    first_response_minutes = round((first_response_at - created).total_seconds() / 60.0, 1)

    # ── Active handle time (touch time) ──────────────────────────────────────
    handle = np.random.lognormal(np.log(ct["hand"]), 0.45) \
             * _PRIORITY_SPEED[priority] * (2 - skill) * kb_lift
    handle_time_minutes = round(max(2.0, handle), 1)

    # ── Resolution time (created → closed, business hours) ───────────────────
    # Complex/escalating types wait on carriers → longer calendar spans.
    base_res = ct["sla"] * np.random.lognormal(-0.45, 0.5)
    if not ct["kb"]:
        base_res *= 1.5
    base_res *= kb_lift
    resolution_hours = round(max(0.3, base_res), 1)

    # ── Status: most closed; recent ones may be open ─────────────────────────
    days_since = (END - created).days
    p_open = 0.55 if days_since < 2 else 0.28 if days_since < 5 else 0.08 if days_since < 12 else 0.0
    if random.random() < p_open:
        status = random.choices(
            ["New", "In Progress", "Waiting on Client", "Waiting on Carrier", "Escalated"],
            weights=[0.18, 0.34, 0.20, 0.22, 0.06])[0]
        closed_date = None
        resolution_hours = None
    else:
        status = "Closed"
        closed_date = _add_business_hours(created, resolution_hours)
        if closed_date > END:
            closed_date = None
            status = "In Progress"
            resolution_hours = None

    # ── Reopen / escalation ──────────────────────────────────────────────────
    reopened = 0
    if status == "Closed" and random.random() < ct["reo"] * (kb_lift if ct["kb"] else 1.0):
        reopened = random.choices([1, 2], weights=[0.85, 0.15])[0]
    escalated = (status == "Escalated") or (random.random() < ct["esc"])

    # ── SLA ──────────────────────────────────────────────────────────────────
    sla_target = ct["sla"]
    if status == "Closed":
        sla_met = resolution_hours <= sla_target * np.random.uniform(0.95, 1.15)
        if escalated and random.random() < 0.5:
            sla_met = False
    else:
        sla_met = None

    # ── First-contact resolution ─────────────────────────────────────────────
    fcr = (status == "Closed" and reopened == 0 and not escalated
           and random.random() < ct["fcr"] * (1.1 if (post_kb and ct["kb"]) else 1.0))

    # ── CSAT (survey response ~58% of closed) ───────────────────────────────
    csat = None
    csat_comment = ""
    if status == "Closed" and random.random() < 0.58:
        base = 4.25
        if sla_met: base += 0.4
        else:       base -= 0.9
        if fcr:     base += 0.3
        if reopened: base -= 0.7 * reopened
        if escalated: base -= 0.5
        if post_kb and ct["kb"]: base += 0.2
        csat = int(min(5, max(1, round(np.random.normal(base, 0.6)))))
        if csat <= 2:
            csat_comment = random.choice([
                "Took too long to get a clear answer.",
                "Had to follow up multiple times.",
                "Issue came back after it was closed.",
                "Wanted more detail on next steps."])
        elif csat == 5:
            csat_comment = random.choice([
                "Fast and exactly what I needed.",
                "Great help, resolved on first contact.",
                "Clear explanation, thank you!", ""])

    subject = ct["name"]
    description = _fill(cid, vrow["vendor_name"], vrow["portal_name"], product, contact)
    resolution_summary = _RESOLUTION[ct["cat"]] if status == "Closed" else ""
    reason_code = ct["sub"]

    rows.append({
        "case_id":               case_id,
        "case_number":           case_number,
        "created_date":          created.isoformat(sep=" "),
        "first_response_at":     first_response_at.isoformat(sep=" "),
        "closed_date":           closed_date.isoformat(sep=" ") if closed_date else "",
        "status":                status,
        "origin":                origin,
        "priority":              priority,
        "client_id":             client_id,
        "contact_name":          contact,
        "owner_agent_id":        owner,
        "vendor_id":             vrow["vendor_id"],
        "product_line":          product_line,
        "product_type":          product,
        "case_type_id":          cid,
        "category":              ct["cat"],
        "category_tagged":       category_tagged,
        "is_mistagged":          is_mistagged,
        "subcategory":           ct["sub"],
        "subject":               subject,
        "description":           description,
        "reason_code":           reason_code,
        "first_response_minutes": first_response_minutes,
        "handle_time_minutes":   handle_time_minutes,
        "resolution_time_hours": resolution_hours if resolution_hours is not None else "",
        "reopened_count":        reopened,
        "escalated":             escalated,
        "sla_target_hours":      sla_target,
        "sla_met":               "" if sla_met is None else bool(sla_met),
        "is_first_contact_resolution": bool(fcr),
        "csat_score":            "" if csat is None else csat,
        "csat_comment":          csat_comment,
        "resolution_summary":    resolution_summary,
        "kb_addressable":        bool(ct["kb"]),
    })

    # ── Threaded comments (client ↔ agent) ───────────────────────────────────
    n_comments = random.choices([1, 2, 3, 4], weights=[0.30, 0.38, 0.22, 0.10])[0]
    t = created
    comment_rows.append({
        "case_number": case_number, "seq": 1, "author_type": "Client",
        "author": contact, "created_at": t.isoformat(sep=" "), "body": description,
    })
    for s in range(2, n_comments + 1):
        t = _add_business_hours(t, random.uniform(0.5, 6.0))
        if closed_date and t > closed_date:
            break
        is_agent = (s % 2 == 0)
        if is_agent:
            body = random.choice([
                "Thanks for reaching out — looking into this now and will confirm shortly.",
                f"Confirmed with {vrow['vendor_name']}. Here are the details and next steps.",
                "I've sent over the corrected form/checklist — please review and resubmit.",
                "Got it processed on our end; you should see the update reflected soon.",
                "Sharing the requirement from the carrier so we can get this in good order."])
            author, atype = dim_agent.loc[dim_agent.agent_id == owner, "agent_name"].iloc[0], "Agent"
        else:
            body = random.choice([
                "Thanks — one more question on this before we proceed.",
                "Got it, that worked. Appreciate the quick turnaround.",
                "Still seeing the issue on my end, can you double-check?",
                "Perfect, please go ahead and submit."])
            author, atype = contact, "Client"
        comment_rows.append({
            "case_number": case_number, "seq": s, "author_type": atype,
            "author": author, "created_at": t.isoformat(sep=" "), "body": body,
        })

fact_cases = pd.DataFrame(rows)
fact_case_comments = pd.DataFrame(comment_rows)


# ══════════════════════════════════════════════════════════════════════════════
# 8. WRITE
# ══════════════════════════════════════════════════════════════════════════════
# Dimensions are dbt seeds — write them to both data/ and dbt/seeds/ so the
# warehouse stays in sync after a regenerate. Facts are loaded via load_bigquery.py.
SEEDS = Path(__file__).resolve().parent / "dbt" / "seeds"
SEEDS.mkdir(parents=True, exist_ok=True)
for name, df in [("dim_vendor", dim_vendor), ("dim_agent", dim_agent),
                 ("dim_client", dim_client), ("dim_case_type", dim_case_type)]:
    df.to_csv(DATA / f"{name}.csv", index=False)
    df.to_csv(SEEDS / f"{name}.csv", index=False)
fact_cases.to_csv(DATA / "fact_cases.csv", index=False)
fact_case_comments.to_csv(DATA / "fact_case_comments.csv", index=False)

# Boilerplate tokens (greetings/fillers/sign-offs) → curated stop-list for NLP.
import re as _re
_boiler = set()
for _phrase in _GREETINGS + _FILLERS + _SIGNOFFS:
    for _w in _re.findall(r"[a-z]+", _phrase.lower()):
        if len(_w) > 1:
            _boiler.add(_w)
(DATA / "boilerplate_stopwords.txt").write_text("\n".join(sorted(_boiler)))

# ── Console summary ───────────────────────────────────────────────────────────
closed = fact_cases[fact_cases.status == "Closed"]
pre  = closed[pd.to_datetime(closed.created_date) <  KB_LAUNCH]
post = closed[pd.to_datetime(closed.created_date) >= KB_LAUNCH]
kb_pre  = pre[pre.kb_addressable]
kb_post = post[post.kb_addressable]

print("✅  Operations Productivity Intelligence dataset generated\n")
print(f"  dim_vendor          {len(dim_vendor):>6,} carriers")
print(f"  dim_agent           {len(dim_agent):>6,} ops team members")
print(f"  dim_client          {len(dim_client):>6,} advisory firms")
print(f"  dim_case_type       {len(dim_case_type):>6,} case types")
print(f"  fact_cases          {len(fact_cases):>6,} cases")
print(f"  fact_case_comments  {len(fact_case_comments):>6,} messages")
print(f"\n  Status mix:")
for s, n in fact_cases.status.value_counts().items():
    print(f"    {s:<18} {n:>6,}")
print(f"\n  Avg handle time (KB-addressable cases):")
print(f"    pre-KB  ({len(kb_pre):>4} cases): {kb_pre.handle_time_minutes.mean():5.1f} min")
print(f"    post-KB ({len(kb_post):>4} cases): {kb_post.handle_time_minutes.mean():5.1f} min")
if len(kb_pre) and len(kb_post):
    lift = 1 - kb_post.handle_time_minutes.mean() / kb_pre.handle_time_minutes.mean()
    print(f"    → {lift*100:.0f}% efficiency improvement after KB launch ({KB_LAUNCH.date()})")
print(f"\n  Overall SLA met: {closed.sla_met.eq(True).mean()*100:.0f}%   "
      f"FCR: {closed.is_first_contact_resolution.mean()*100:.0f}%   "
      f"Avg CSAT: {pd.to_numeric(closed.csat_score, errors='coerce').mean():.2f}")
print(f"\n  Top 8 case types by volume:")
top = fact_cases.subject.value_counts().head(8)
for name, n in top.items():
    print(f"    {n:>5,}  {name}")
print(f"\n  CSVs written to: {DATA}")
