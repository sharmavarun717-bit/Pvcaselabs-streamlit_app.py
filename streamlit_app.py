"""PV Case Lab: persistent pharmacovigilance training simulation.

Training use only. The SQLite database is the source of truth; Streamlit session
state is used only for temporary UI selections, never for case records.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import mimetypes

import streamlit as st

import pv_storage as storage

st.set_page_config(page_title="PV Case Lab", page_icon="🧬", layout="wide")
storage.init_db()

STAGES = storage.STAGES
DOC_CATEGORIES = [
    "Initial Source Document", "Follow-up Source Document", "Medical Records",
    "Discharge Summary", "Laboratory Reports", "Prescription",
    "Clinical Trial Documents", "Literature Articles", "Patient Consent",
    "Reporter Correspondence", "QC Documents", "Medical Review Documents", "Other",
]
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"}
MAX_FILE_SIZE = 10 * 1024 * 1024
ROLES = ["System Administrator", "PV Manager", "Intake User", "Triage User", "Data Entry User", "QC Reviewer", "Medical Reviewer", "Submission User", "Student", "Faculty/Trainer"]


def current_user() -> str:
    return f"Demo {st.session_state.get('demo_role', 'Student')}"


def get_cases(search: str = "") -> list[dict]:
    """Always read cases from SQLite so data survives a browser logout/session reset."""
    return storage.get_cases(search)


def case_label(case: dict) -> str:
    return f"{case['case_id']} | {case['stage']} | {case['status']}"


def field_value(data: dict, *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", " "):
            return str(value)
    return "Not Reported"


def generate_narrative(case_id: str, data: dict) -> str:
    """Create an editable enterprise-inspired training narrative from saved data."""
    return f"""CASE NARRATIVE — TRAINING TEMPLATE

CASE IDENTIFICATION
Case ID: {case_id}
Worldwide Unique Case ID: {field_value(data, 'WWUID')}
Report type: {field_value(data, 'Initial / Follow-up', 'Initial/follow-up classification', 'Case Type')}
Source: {field_value(data, 'Source type', 'Source Category', 'Source')}
Country: {field_value(data, 'Country')}
Date received: {field_value(data, 'Date received', 'Date Source Received', 'Receipt Date')}
Seriousness: {field_value(data, 'Case Seriousness')}

PATIENT AND REPORTER
Patient: {field_value(data, 'Patient initials', 'Patient Training ID', 'Patient ID')}
Age/sex: {field_value(data, 'Age')} {field_value(data, 'Age Unit')} / {field_value(data, 'Sex')}
Medical history: {field_value(data, 'Medical history', 'Medical History')}
Reporter type/qualification: {field_value(data, 'Reporter type', 'Reporter Type', 'Qualification')}

PRODUCT AND EXPOSURE
Reported suspect product: {field_value(data, 'Reported product name', 'Product Name', 'Suspect Product')}
Active ingredient: {field_value(data, 'Active ingredient', 'Active Ingredient')}
Indication: {field_value(data, 'Indication', 'Reported Indication')}
Dose, route, frequency: {field_value(data, 'Dose', 'Dosage')}; {field_value(data, 'Route')}; {field_value(data, 'Frequency')}
Exposure dates: {field_value(data, 'Product start date', 'Therapy Start Date')} to {field_value(data, 'Product stop date', 'Therapy Stop Date')}
Dechallenge/rechallenge: {field_value(data, 'Dechallenge')} / {field_value(data, 'Rechallenge')}

ADVERSE EVENT AND CLINICAL COURSE
Reported event: {field_value(data, 'Reported verbatim term', 'Verbatim Event', 'Reported Event', 'Reported Adverse Event')}
MedDRA coded term (if supplied): {field_value(data, 'MedDRA PT')} / {field_value(data, 'MedDRA LLT')}
Onset date: {field_value(data, 'Event onset date', 'Event Onset Date')}
Seriousness criteria: {field_value(data, 'Seriousness criteria', 'Seriousness Criteria')}
Outcome: {field_value(data, 'Event outcome', 'Event Outcome')}
Clinical course/treatment: {field_value(data, 'Clinical course', 'Treatment and management')}
Laboratory findings: {field_value(data, 'Laboratory findings', 'Test Result')}

CAUSALITY AND CASE SUMMARY
WHO-UMC assessment: {field_value(data, 'WHO-UMC Category')}
Assessment rationale: {field_value(data, 'Assessment rationale', 'Assessment Rationale')}

This is an editable training narrative based only on information entered in this synthetic case. Missing information is displayed as Not Reported. Human review is required; this is not a validated Argus, ARISg, or regulatory narrative format.
"""


def render_dashboard() -> None:
    st.header("Training Dashboard")
    cases = get_cases()
    total = len(cases)
    complete = sum(case["stage"] == "Completed" for case in cases)
    metrics = st.columns(3)
    metrics[0].metric("Total Cases", total)
    metrics[1].metric("Open Cases", total - complete)
    metrics[2].metric("Completed Cases", complete)
    st.subheader("Workflow Overview")
    for stage in STAGES:
        st.write(f"**{stage}:** {sum(case['stage'] == stage for case in cases)} cases")
    st.subheader("Recent Cases")
    for case in cases[:10]:
        st.write(f"**{case['case_id']}** — {case['stage']} — {case['status']}")
    if not cases:
        st.info("No cases yet. Create a synthetic training case to begin.")


def render_intake() -> None:
    st.header("Case Intake")
    with st.form("intake_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        source = col1.selectbox("Source type", ["Spontaneous", "Clinical Trial", "Literature", "Solicited", "Patient Support Program", "Regulatory Authority", "Other"])
        classification = col2.selectbox("Initial / Follow-up", ["Initial", "Follow-up"])
        country = col1.text_input("Country")
        received = col2.date_input("Date received", value=date.today())
        awareness = col1.date_input("Date of awareness", value=date.today())
        reporter = col2.text_input("Reporter type")
        product = col1.text_input("Suspect product")
        event = col2.text_input("Reported adverse event")
        seriousness = col1.selectbox("Case seriousness", ["Unknown", "Serious", "Non-serious"])
        wwuid = col2.text_input("Worldwide Unique Case ID (optional)")
        assigned = col1.text_input("Assigned user", value=current_user())
        comments = st.text_area("Intake comments")
        submitted = st.form_submit_button("Save Case", type="primary")
    if submitted:
        if not country.strip():
            st.error("Enter a country before saving the case.")
            return
        payload = {
            "Source type": source, "Initial / Follow-up": classification,
            "Country": country.strip(), "Date received": str(received),
            "Date of awareness": str(awareness), "Reporter type": reporter.strip(),
            "Suspect Product": product.strip(), "Reported Adverse Event": event.strip(),
            "Case Seriousness": seriousness, "WWUID": wwuid.strip(),
            "Assigned User": assigned.strip(), "Intake Comments": comments.strip(),
        }
        try:
            case_id = storage.create_case(payload, current_user())
            st.success(f"Case {case_id} saved to the persistent database.")
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                st.error("That WWUID is already assigned to another case.")
            else:
                st.error(f"Could not save the case: {exc}")


def save_section(case_id: str, section: str, values: dict) -> None:
    case = storage.get_case(case_id)
    data = case["data"]
    data.update(values)
    try:
        storage.update_case(case_id, data, current_user(), f"{section} information saved")
        st.success(f"{section} saved to the persistent database.")
    except Exception as exc:
        st.error(f"Could not save {section}: {exc}")


def render_processing() -> None:
    st.header("ICSR Case Processing")
    cases = get_cases()
    if not cases:
        st.info("Create a case first.")
        return
    case_id = st.selectbox("Select Case ID", [case["case_id"] for case in cases], format_func=lambda value: next((case_label(c) for c in cases if c["case_id"] == value), value))
    case = storage.get_case(case_id)
    data = case["data"]
    st.info(f"**{case_id}** · Stage: **{case['stage']}** · Status: **{case['status']}**")

    fields_by_tab = {
        "General": ["WWUID", "Case Type", "Initial / Follow-up", "Awareness Date", "Date received", "Most recent information date", "Country", "Source type", "Case validity", "Case Seriousness", "Reportability", "Case status"],
        "Source": ["Primary source", "Secondary source", "Literature source", "Regulatory authority", "Company reference", "Report source", "Receipt dates"],
        "Reporter": ["Reporter type", "First name", "Last name", "Qualification", "Organization", "Reporter country", "Email", "Telephone", "Primary reporter indicator"],
        "Patient": ["Patient initials", "Patient ID", "Date of birth", "Age", "Age Unit", "Sex", "Weight", "Height", "Medical history", "Relevant medical conditions", "Pregnancy information", "Patient medical history comments"],
        "Clinical Trial": ["Study ID", "Protocol number", "Investigator", "Sponsor", "Study type", "Study blind status", "Trial site", "Randomization number", "Treatment arm"],
        "Product": ["Reported product name", "Product role", "Generic name", "Active ingredient", "Manufacturer", "Product country", "Strength", "Dosage form", "Route", "Dose", "Frequency", "Product start date", "Product stop date", "Indication", "Batch number", "Expiry date", "Dechallenge", "Rechallenge", "WHODrug preferred name", "Drug code", "ATC code", "WHODrug version", "Product coding status", "Product coding comments"],
        "Event": ["Reported verbatim term", "Event description", "Event onset date", "Event end date", "Case Seriousness", "Seriousness criteria", "Event outcome", "Hospitalization", "Life-threatening status", "Disability", "Congenital anomaly", "Other medically important condition", "Event comments", "LLT", "LLT code", "PT", "PT code", "HLT", "HLGT", "SOC", "Primary SOC", "MedDRA version", "Event coding status", "Coding comments"],
        "Causality": ["WHO-UMC Category", "Assessment rationale", "Reviewer", "Assessment date", "Assessment comments"],
        "Narrative": ["Structured Case Narrative"],
    }
    tabs = st.tabs(list(fields_by_tab) + ["Documents", "Laboratory", "Literature"])
    for tab, (section, fields) in zip(tabs[:len(fields_by_tab)], fields_by_tab.items()):
        with tab:
            st.subheader(f"{section} Information")
            with st.form(f"save_{section}_{case_id}"):
                values = {}
                for field in fields:
                    current = str(data.get(field, ""))
                    if field == "WHO-UMC Category":
                        choices = ["Certain", "Probable/Likely", "Possible", "Unlikely", "Conditional/Unclassified", "Unassessable/Unclassifiable"]
                        values[field] = st.selectbox(field, choices, index=choices.index(current) if current in choices else 0)
                    elif field == "Structured Case Narrative":
                        default = current or generate_narrative(case_id, data)
                        values[field] = st.text_area(field, value=default, height=350)
                    elif field in {"Event description", "Medical history", "Relevant medical conditions", "Patient medical history comments", "Assessment rationale", "Assessment comments", "Product coding comments", "Coding comments"}:
                        values[field] = st.text_area(field, value=current)
                    else:
                        values[field] = st.text_input(field, value=current)
                if st.form_submit_button(f"Save {section}"):
                    save_section(case_id, section, values)

    with tabs[len(fields_by_tab)]:
        st.subheader("Case Documents")
        st.caption("Attachments are saved to persistent server storage and linked to this case. Synthetic files only; maximum 10 MB per file.")
        with st.form(f"upload_documents_{case_id}"):
            uploads = st.file_uploader("Attach documents (PDF, Word, Excel, or image)", type=sorted(ALLOWED_EXTENSIONS), accept_multiple_files=True)
            category = st.selectbox("Document category", DOC_CATEGORIES)
            description = st.text_input("Description")
            add = st.form_submit_button("Save documents")
        if add:
            if not uploads:
                st.warning("Select at least one file.")
            else:
                saved = 0
                for upload in uploads:
                    extension = Path(upload.name).suffix.lower().lstrip(".")
                    if extension not in ALLOWED_EXTENSIONS:
                        st.error(f"{upload.name}: unsupported file type.")
                    elif upload.size > MAX_FILE_SIZE:
                        st.error(f"{upload.name}: exceeds the 10 MB limit.")
                    else:
                        try:
                            storage.add_document(case_id, Path(upload.name).name, category, upload.type or mimetypes.guess_type(upload.name)[0] or "application/octet-stream", upload.getvalue(), description, "", "", current_user())
                            saved += 1
                        except Exception as exc:
                            st.error(f"Could not save {upload.name}: {exc}")
                if saved:
                    st.success(f"Saved {saved} document(s) persistently.")
                    st.rerun()
        documents = storage.list_documents(case_id)
        for document in documents:
            with st.expander(f"{document['name']} · {document['category']} · v{document['current_version']}"):
                st.write(document["description"] or "No description")
                path = Path(document["stored_path"])
                if path.is_file():
                    file_bytes = path.read_bytes()
                    st.download_button("Download", file_bytes, file_name=document["name"], mime=document["content_type"], key=f"download_{document['document_id']}")
                    if Path(document["name"]).suffix.lower() == ".pdf" and hasattr(st, "pdf"):
                        st.pdf(file_bytes)
                else:
                    st.error("Stored document file is missing. Restore it from backup.")

    with tabs[len(fields_by_tab) + 1]:
        st.subheader("Laboratory Information")
        with st.form(f"laboratory_{case_id}"):
            lab_fields = ["Test Name", "Test Date", "Test Result", "Unit", "Reference Range", "Abnormal Indicator", "Comments"]
            values = {field: st.text_input(field, value=str(data.get(field, "")), key=f"lab_{case_id}_{field}") for field in lab_fields}
            if st.form_submit_button("Save Laboratory Information"):
                save_section(case_id, "Laboratory", values)

    with tabs[len(fields_by_tab) + 2]:
        st.subheader("Literature Information")
        with st.form(f"literature_{case_id}"):
            lit_fields = ["Article Title", "Authors", "Journal", "DOI", "Publication Year", "PMID", "Literature Reference", "Literature Assessment"]
            values = {field: st.text_input(field, value=str(data.get(field, "")), key=f"literature_{case_id}_{field}") for field in lit_fields}
            if st.form_submit_button("Save Literature Information"):
                save_section(case_id, "Literature", values)

    st.divider()
    st.subheader("Workflow Handover")
    current_stage = case["stage"]
    st.write(f"Current stage: **{current_stage}**")
    if current_stage != "Completed":
        current_index = STAGES.index(current_stage)
        next_stage = STAGES[current_index + 1]
        if current_stage in ("Quality Control Review", "Medical Review"):
            decision = st.selectbox("Review decision", ["Select decision", "Pass", "Return for Rework"], key=f"review_decision_{case_id}")
        else:
            decision = "Pass"
        comments = st.text_area("Handover comments (required)", key=f"handover_comments_{case_id}")
        if st.button("Confirm handover", key=f"handover_{case_id}"):
            if not comments.strip():
                st.error("Comments are required for a handover.")
            elif decision == "Select decision":
                st.error("Select Pass or Return for Rework.")
            else:
                destination = "Data Entry" if decision == "Return for Rework" else next_stage
                action = "Return for Rework" if decision == "Return for Rework" else "Pass"
                try:
                    storage.transition_case(case_id, destination, action, comments, current_user())
                    st.success(f"Case moved to {destination}; saved persistently.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    else:
        st.success("This case is completed.")
    history = storage.get_workflow(case_id)
    if history:
        st.subheader("Case workflow history")
        for item in reversed(history):
            st.write(f"{item['timestamp']} · {item['from_stage'] or 'New'} → {item['to_stage']} · {item['action']} · {item['comments']}")


def render_queue() -> None:
    st.header("Case Queue")
    query = st.text_input("Search by case ID, WWUID, product, or event")
    cases = get_cases(query)
    if not cases:
        st.info("No matching cases.")
        return
    for case in cases:
        with st.expander(case_label(case)):
            st.write(f"Created: {case['created_at']} · Assigned: {case['assigned_user'] or 'Unassigned'} · Due: {case['due_date'] or 'Not set'}")
            st.json(case["data"])


def render_history() -> None:
    st.header("Workflow History")
    cases = get_cases()
    if not cases:
        st.info("No cases available.")
        return
    case_id = st.selectbox("Filter case", ["All cases"] + [case["case_id"] for case in cases])
    rows = storage.get_workflow("" if case_id == "All cases" else case_id)
    if rows:
        for item in reversed(rows):
            st.write(f"{item['timestamp']} · {item['case_id']} · {item['from_stage'] or 'New'} → {item['to_stage']} · {item['action']} · {item['comments']}")
    else:
        st.info("No workflow actions recorded.")


def render_audit() -> None:
    st.header("Audit Trail")
    cases = get_cases()
    case_id = st.selectbox("Filter case", ["All cases"] + [case["case_id"] for case in cases])
    rows = storage.get_audit("" if case_id == "All cases" else case_id)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("Training audit records are persistent but not immutable or regulatory validated.")
    else:
        st.info("No audit records yet.")


def main() -> None:
    with st.sidebar:
        st.title("PV Case Lab")
        page = st.radio("Navigation", ["Dashboard", "Case Intake", "Case Queue", "ICSR Case Processing", "Workflow History", "Audit Trail"])
        st.page_link("pages/1_Coding_Workspaces.py", label="MedDRA / WHODrug Coding", icon="🧾")
        st.selectbox("Demo role (not authentication)", ROLES, key="demo_role")
        st.caption("Demo role selection is not a security control.")
    st.title("🧬 PV CASE LAB")
    st.caption("Training simulation · Synthetic data only · SQLite persistence enabled")
    if page == "Dashboard":
        render_dashboard()
    elif page == "Case Intake":
        render_intake()
    elif page == "Case Queue":
        render_queue()
    elif page == "ICSR Case Processing":
        render_processing()
    elif page == "Workflow History":
        render_history()
    elif page == "Audit Trail":
        render_audit()
    st.divider()
    st.caption(f"SQLite database: {storage.DB_PATH} · Documents: {storage.DOCUMENT_DIR} · Educational use only; not a validated production PV system.")


main()
