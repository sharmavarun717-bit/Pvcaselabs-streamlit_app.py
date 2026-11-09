import streamlit as st
from datetime import datetime, date
import uuid

st.set_page_config(
    page_title="PV Case Lab",
    page_icon="🧬",
    layout="wide"
)

# ---------------- SESSION DATA ----------------

if "cases" not in st.session_state:
    st.session_state.cases = {}

if "audit" not in st.session_state:
    st.session_state.audit = []

STAGES = [
    "Intake",
    "Triage",
    "Data Entry",
    "Quality Review",
    "Medical Review",
    "Submission",
    "Completed"
]


def log_action(case_id, action):
    st.session_state.audit.append({
        "Case ID": case_id,
        "Action": action,
        "User": "Demo User",
        "Timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    })


def create_case():
    case_id = "PV-" + datetime.now().strftime("%Y%m%d") + "-" + str(uuid.uuid4())[:6].upper()
    st.session_state.cases[case_id] = {
        "stage": "Intake",
        "status": "In Progress",
        "data": {},
        "comments": [],
        "history": ["Case created"],
        "created": datetime.now().strftime("%d-%m-%Y %H:%M")
    }
    log_action(case_id, "Case created")
    return case_id


# ---------------- NARRATIVE TEMPLATE ----------------

def _value(data, *keys):
    for key in keys:
        val = data.get(key)
        if val not in (None, "", " "):
            return str(val)
    return "Not Reported"


def generate_argus_like_narrative(case_id, case):
    data = case.get("data", {})

    age = _value(data, "Age", "Patient Age")
    age_unit = _value(data, "Age Unit", "Patient Age Unit")
    sex = _value(data, "Sex")
    product = _value(data, "Suspect Product", "Product Name", "Reported product name")
    event = _value(data, "Reported Adverse Event", "Verbatim Event", "Reported verbatim term")
    seriousness = _value(data, "Case Seriousness", "Seriousness Criteria")
    country = _value(data, "Country", "Country of Receipt")
    source = _value(data, "Source", "Source Category", "Source type")
    reporter = _value(data, "Reporter Type", "Reporter Initials", "Reporter type")
    indication = _value(data, "Indication", "Reported Indication")
    onset = _value(data, "Event Onset Date", "Onset Date")
    outcome = _value(data, "Event Outcome", "Outcome")
    causality = _value(data, "WHO-UMC Category", "Causality Category")
    narrative_text = _value(data, "Structured Case Narrative")

    if narrative_text != "Not Reported":
        return narrative_text

    return f"""CASE NARRATIVE
========================================

CASE IDENTIFICATION
- Case ID: {case_id}
- Source: {source}
- Country: {country}
- Initial/Follow-up: {_value(data, 'Initial / Follow-up', 'Initial/follow-up classification', 'Case Type')}
- Date of Receipt: {_value(data, 'Receipt Date', 'Date received', 'Date Received')}
- Seriousness: {seriousness}
- Reporter Type: {reporter}

PATIENT INFORMATION
- Patient demographics: age {age} {age_unit}, sex {sex}
- Medical history: {_value(data, 'Medical History', 'Relevant medical conditions', 'Patient medical history comments')}
- Relevant concomitant medications: {_value(data, 'Concomitant Medications', 'Concomitant medication')}

SOURCE INFORMATION
- Reported source: {source}
- Reporter/Informant: {reporter}
- Company/organization: {_value(data, 'Organisation', 'Organization')}

SUSPECT PRODUCT / EXPOSURE
- Suspect product: {product}
- Active ingredient: {_value(data, 'Active Ingredient', 'Active ingredient')}
- Indication: {indication}
- Dose / frequency: {_value(data, 'Dosage', 'Dose', 'Frequency')}
- Route: {_value(data, 'Route')}
- Therapy start / stop date: {_value(data, 'Therapy Start Date', 'Product start date')} / {_value(data, 'Therapy Stop Date', 'Product stop date')}
- Dechallenge / rechallenge: {_value(data, 'Dechallenge')} / {_value(data, 'Rechallenge')}

ADVERSE EVENT
- Verbatim event: {event}
- MedDRA PT / LLT: {_value(data, 'MedDRA PT')} / {_value(data, 'MedDRA LLT')}
- Event onset date: {onset}
- Event outcome: {outcome}
- Seriousness criteria: {_value(data, 'Seriousness Criteria')}
- Hospitalization / medically important condition: {_value(data, 'Hospitalization', 'Other medically important condition')}

CLINICAL COURSE AND LABORATORY FINDINGS
- Clinical course / treatment received: {_value(data, 'Clinical Course', 'Treatment and management')}
- Laboratory findings: {_value(data, 'Test Result', 'Laboratory Findings', 'Lab Tests')}

CAUSALITY ASSESSMENT
- WHO-UMC causality assessment: {causality}
- Assessment rationale: {_value(data, 'Assessment Rationale', 'Assessment rationale')}

CASE SUMMARY
This is a synthetic educational pharmacovigilance case. The report describes a {seriousness.lower()} adverse event associated with {product}. The event was reported from {country} and was characterized as {event}. The event onset occurred on {onset}. Based on the available information, the case is currently assessed as {causality}. No additional clinical details were available for inclusion beyond the reported information.

NARRATIVE REVIEW STATUS
- Narrative prepared by: Demo User
- Narrative review: Pending human review before final approval.
"""


# ---------------- HEADER ----------------

st.title("🧬 PV CASE LAB")
st.caption("Pharmacovigilance Case Processing & Training Simulation")

with st.sidebar:
    st.title("PV Case Lab")
    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Create Case",
            "Case Queue",
            "ICSR Case Processing",
            "Workflow History",
            "Audit Log"
        ]
    )

    selected_stage = None

    if page == "ICSR Case Processing":
        with st.expander("Select Workflow", expanded=True):
            selected_stage = st.radio(
                "Workflow Stages",
                [
                    "Intake",
                    "Triage",
                    "Data Entry",
                    "Quality Review",
                    "Medical Review",
                    "Submission",
                    "Completed"
                ],
                key="workflow_stage"
            )

        page = "ICSR Data Entry"

    st.divider()
    st.caption("Educational simulation using fictional training data.")

# ---------------- DASHBOARD ----------------

if page == "Dashboard":
    st.header("Training Dashboard")

    cases = st.session_state.cases
    total = len(cases)
    completed = sum(c["stage"] == "Completed" for c in cases.values())
    pending = total - completed

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Cases", total)
    c2.metric("Pending Cases", pending)
    c3.metric("Completed Cases", completed)

    st.divider()
    st.subheader("Workflow Overview")

    for stage in STAGES:
        count = sum(c["stage"] == stage for c in cases.values())
        st.write(f"**{stage}:** {count} cases")

    st.divider()
    st.subheader("Recent Cases")

    if cases:
        for cid, case in list(cases.items())[-10:]:
            st.write(f"**{cid}** — {case['stage']} — {case['status']}")
    else:
        st.info("No cases created yet. Start by creating a new case.")

# ---------------- CREATE CASE ----------------

elif page == "Create Case":
    st.header("Intake – Create New Case")

    with st.form("new_case"):
        source = st.selectbox(
            "Report Source",
            ["Spontaneous", "Literature", "Clinical Trial", "Other"]
        )
        country = st.text_input("Country")
        receipt_date = st.date_input("Date of Receipt", value=date.today())
        reporter = st.text_input("Reporter Type")
        suspect_product = st.text_input("Suspect Product")
        event = st.text_input("Reported Adverse Event")

        submitted = st.form_submit_button("Create Case")

        if submitted:
            cid = create_case()
            st.session_state.cases[cid]["data"].update({
                "Source": source,
                "Country": country,
                "Receipt Date": str(receipt_date),
                "Reporter Type": reporter,
                "Suspect Product": suspect_product,
                "Reported Event": event
            })
            st.success(f"Case created successfully: {cid}")
            st.info("The case is now in the Intake workflow.")

# ---------------- CASE QUEUE ----------------

elif page == "Case Queue":
    st.header("Case Queue")

    if not st.session_state.cases:
        st.info("No cases available.")
    else:
        for cid, case in st.session_state.cases.items():
            with st.expander(f"{cid} | {case['stage']} | {case['status']}"):
                st.write("Created:", case["created"])
                st.write("Current stage:", case["stage"])
                st.write("Status:", case["status"])

                if case["comments"]:
                    st.write("Rework comments:")
                    for comment in case["comments"]:
                        st.warning(comment)

# ---------------- ICSR DATA ENTRY ----------------

elif page == "ICSR Data Entry":
    st.header("ICSR Case Processing")

    if not st.session_state.cases:
        st.warning("Create a case first.")
    else:
        cid = st.selectbox(
            "Select Case ID",
            list(st.session_state.cases.keys())
        )

        case = st.session_state.cases[cid]
        st.write("Current workflow:", f"**{case['stage']}**")

        tabs = st.tabs([
            "General", "Source", "Reporter", "Patient",
            "Clinical Trial", "Product", "Event",
            "Lab Tests", "Causality", "Literature", "Narrative"
        ])

        fields = {
            "General": [
                "Case Type", "Initial / Follow-up", "Awareness Date",
                "Country", "Case Seriousness"
            ],
            "Source": [
                "Source Category", "Source Reference",
                "Date Source Received"
            ],
            "Reporter": [
                "Reporter Initials", "Qualification",
                "Organisation", "Reporter Country"
            ],
            "Patient": [
                "Patient Training ID", "Age", "Age Unit",
                "Sex", "Weight", "Medical History"
            ],
            "Clinical Trial": [
                "Study ID", "Protocol Number",
                "Study Site", "Investigator"
            ],
            "Product": [
                "Product Name",
                "Active Ingredient",
                "Product Classification",
                "Dosage",
                "Route",
                "Frequency",
                "Indication",
                "Reported Indication",
                "MedDRA Indication Coded Term",
                "MedDRA Indication Code",
                "Indication Coding Status",
                "Indication Dictionary Version",
                "WHODrug Preferred Name",
                "WHODrug Drug Code",
                "ATC Code",
                "Strength",
                "Dosage Form",
                "WHODrug Version",
                "Product Coding Status",
                "Batch Number",
                "Therapy Start Date",
                "Therapy Stop Date",
                "Dechallenge",
                "Rechallenge"
            ],
            "Event": [
                "Verbatim Event",
                "MedDRA LLT",
                "MedDRA LLT Code",
                "MedDRA PT",
                "MedDRA PT Code",
                "MedDRA HLT",
                "MedDRA HLGT",
                "MedDRA SOC",
                "Primary SOC",
                "MedDRA Version",
                "Event Coding Status",
                "Coding Comments",
                "Event Onset Date",
                "Event Outcome",
                "Seriousness Criteria"
            ],
            "Lab Tests": [
                "Test Name", "Test Result",
                "Unit", "Reference Range"
            ],
            "Causality": [
                "WHO-UMC Category", "Assessment Rationale"
            ],
            "Literature": [
                "Article Title", "Authors",
                "Journal", "DOI", "Publication Year"
            ],
            "Narrative": [
                "Structured Case Narrative"
            ]
        }

        for tab, name in zip(tabs, fields.keys()):
            with tab:
                st.subheader(name + " Information")

                with st.form("form_" + name):
                    values = {}
                    for field in fields[name]:
                        if field == "WHO-UMC Category":
                            values[field] = st.selectbox(
                                field,
                                ["Certain", "Probable/Likely", "Possible",
                                 "Unlikely", "Conditional/Unclassified",
                                 "Unassessable/Unclassifiable"]
                            )
                        elif field == "Structured Case Narrative":
                            generated = generate_argus_like_narrative(cid, case)
                            values[field] = st.text_area(
                                field,
                                value=generated,
                                height=300,
                                help="ARGUS/ARISg-inspired narrative template with structured case sections."
                            )
                        else:
                            values[field] = st.text_input(field)

                    save = st.form_submit_button("Save " + name)

                    if save:
                        case["data"].update(values)
                        log_action(cid, name + " information saved")
                        st.success(name + " information saved.")

        # ---------------- SUBMIT TO NEXT WORKFLOW ----------------

        st.divider()
        st.subheader("Submit to Next Workflow")

        current = case["stage"]
        st.write("Current Stage:", f"**{current}**")

        if current != "Completed":

            next_stage = STAGES[STAGES.index(current) + 1]

            decision = "Pass to Next Stage"

            if current == "Quality Review":
                decision = st.selectbox(
                    "QC Decision",
                    [
                        "Select decision",
                        "Pass to Medical Review",
                        "Return for Rework"
                    ],
                    key=f"qc_decision_{cid}"
                )

            elif current == "Medical Review":
                decision = st.selectbox(
                    "Medical Decision",
                    [
                        "Select decision",
                        "Pass to Submission",
                        "Return for Rework"
                    ],
                    key=f"medical_decision_{cid}"
                )

            submit_key = f"show_submit_{cid}"

            if st.button(
                "Submit to Next Workflow",
                key=f"open_submit_{cid}"
            ):
                st.session_state[submit_key] = True

            if st.session_state.get(submit_key, False):

                comment = st.text_area(
                    "Submit Comments (Mandatory)",
                    key=f"submit_comment_{cid}"
                )

                if st.button(
                    "Confirm Submit",
                    key=f"confirm_submit_{cid}"
                ):

                    if not comment.strip():
                        st.error("Please enter submission comments.")

                    elif current in ["Quality Review", "Medical Review"] and decision == "Select decision":
                        st.error("Please select a review decision first.")

                    else:
                        case.setdefault("comments", []).append(comment)

                        if decision == "Return for Rework":

                            case["stage"] = "Data Entry"
                            case["status"] = "Returned for Rework"

                            case["history"].append(
                                f"{current}: Returned to Data Entry. Comment: {comment}"
                            )

                            log_action(
                                cid,
                                f"{current}: Returned for rework. Comment: {comment}"
                            )

                        else:

                            case["stage"] = next_stage

                            case["status"] = (
                                "Completed"
                                if next_stage == "Completed"
                                else "In Progress"
                            )

                            case["history"].append(
                                f"Submitted from {current} to {next_stage}. Comment: {comment}"
                            )

                            log_action(
                                cid,
                                f"Submitted from {current} to {next_stage}. Comment: {comment}"
                            )

                        st.session_state[submit_key] = False

                        st.success(
                            f"Case successfully submitted to {case['stage']}!"
                        )

                        st.rerun()

        else:
            st.success("This case is completed.")

# ---------------- WORKFLOW HISTORY ----------------

elif page == "Workflow History":
    st.header("Workflow History")

    for cid, case in st.session_state.cases.items():
        with st.expander(cid):
            for item in case["history"]:
                st.write("•", item)

# ---------------- AUDIT LOG ----------------

elif page == "Audit Log":
    st.header("Audit Trail")

    if st.session_state.audit:
        st.dataframe(
            st.session_state.audit,
            use_container_width=True
        )
    else:
        st.info("No audit activity yet.")

st.divider()
st.caption(
    "PV Case Lab | Educational simulation only | "
    "Use synthetic patient and reporter information."
)


# EOF
