import streamlit as st
from datetime import datetime, date
import uuid

st.set_page_config(page_title="PV Case Lab", page_icon="🧬", layout="wide")

if "cases" not in st.session_state:
    st.session_state.cases = {}
if "audit" not in st.session_state:
    st.session_state.audit = []

STAGES = ["Intake", "Triage", "Data Entry", "Quality Review", "Medical Review", "Submission", "Completed"]
DOC_CATEGORIES = [
    "Initial Source Document", "Follow-up Source Document", "Medical Records",
    "Discharge Summary", "Laboratory Reports", "Prescription",
    "Clinical Trial Documents", "Literature Articles", "Patient Consent",
    "Reporter Correspondence", "QC Documents", "Medical Review Documents", "Other",
]


def log_action(case_id, action):
    st.session_state.audit.append({
        "Case ID": case_id,
        "Action": action,
        "User": "Demo User",
        "Timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
    })


def create_case():
    case_id = "PV-" + datetime.now().strftime("%Y%m%d") + "-" + str(uuid.uuid4())[:6].upper()
    st.session_state.cases[case_id] = {
        "stage": "Intake", "status": "In Progress", "data": {},
        "documents": [], "comments": [], "history": ["Case created"],
        "created": datetime.now().strftime("%d-%m-%Y %H:%M"),
    }
    log_action(case_id, "Case created")
    return case_id


def _value(data, *keys):
    for key in keys:
        value = data.get(key)
        if value not in (None, "", " "):
            return str(value)
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
    return f"""CASE NARRATIVE\n========================================\n\nCASE IDENTIFICATION\n- Case ID: {case_id}\n- Source: {source}\n- Country: {country}\n- Initial/Follow-up: {_value(data, 'Initial / Follow-up', 'Initial/follow-up classification', 'Case Type')}\n- Date of Receipt: {_value(data, 'Receipt Date', 'Date received', 'Date Received')}\n- Seriousness: {seriousness}\n- Reporter Type: {reporter}\n\nPATIENT INFORMATION\n- Patient demographics: age {age} {age_unit}, sex {sex}\n- Medical history: {_value(data, 'Medical History', 'Relevant medical conditions')}\n- Concomitant medications: {_value(data, 'Concomitant Medications', 'Concomitant medication')}\n\nSOURCE INFORMATION\n- Reported source: {source}\n- Reporter/Informant: {reporter}\n- Organization: {_value(data, 'Organisation', 'Organization')}\n\nSUSPECT PRODUCT / EXPOSURE\n- Suspect product: {product}\n- Active ingredient: {_value(data, 'Active Ingredient')}\n- Indication: {indication}\n- Dose/frequency: {_value(data, 'Dosage', 'Dose')} / {_value(data, 'Frequency')}\n- Route: {_value(data, 'Route')}\n- Therapy start/stop: {_value(data, 'Therapy Start Date')} / {_value(data, 'Therapy Stop Date')}\n- Dechallenge/rechallenge: {_value(data, 'Dechallenge')} / {_value(data, 'Rechallenge')}\n\nADVERSE EVENT\n- Verbatim event: {event}\n- MedDRA PT / LLT: {_value(data, 'MedDRA PT')} / {_value(data, 'MedDRA LLT')}\n- Onset date: {onset}\n- Outcome: {outcome}\n- Seriousness criteria: {_value(data, 'Seriousness Criteria')}\n\nCLINICAL COURSE AND LABORATORY FINDINGS\n- Clinical course/treatment: {_value(data, 'Clinical Course', 'Treatment and management')}\n- Laboratory findings: {_value(data, 'Test Result', 'Laboratory Findings')}\n\nCAUSALITY ASSESSMENT\n- WHO-UMC assessment: {causality}\n- Rationale: {_value(data, 'Assessment Rationale')}\n\nCASE SUMMARY\nSynthetic training case. Information not provided is identified as Not Reported. This narrative requires human review before approval.\n"""


st.title("🧬 PV CASE LAB")
st.caption("Pharmacovigilance Case Processing & Training Simulation — synthetic training data only")
with st.sidebar:
    st.title("PV Case Lab")
    page = st.radio("Navigation", ["Dashboard", "Create Case", "Case Queue", "ICSR Case Processing", "Workflow History", "Audit Log"])
    st.page_link("pages/1_Coding_Workspaces.py", label="MedDRA / WHODrug Coding", icon="🧾")
    st.caption("Educational simulation only.")

if page == "Dashboard":
    st.header("Training Dashboard")
    cases = st.session_state.cases
    total = len(cases)
    completed = sum(c["stage"] == "Completed" for c in cases.values())
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Cases", total)
    c2.metric("Pending Cases", total - completed)
    c3.metric("Completed Cases", completed)
    st.divider()
    st.subheader("Workflow Overview")
    for stage in STAGES:
        st.write(f"**{stage}:** {sum(c['stage'] == stage for c in cases.values())} cases")
    st.subheader("Recent Cases")
    if cases:
        for cid, case in list(cases.items())[-10:]:
            st.write(f"**{cid}** — {case['stage']} — {case['status']}")
    else:
        st.info("No cases created yet. Start by creating a new case.")

elif page == "Create Case":
    st.header("Intake – Create New Case")
    with st.form("new_case"):
        source = st.selectbox("Report Source", ["Spontaneous", "Literature", "Clinical Trial", "Other"])
        country = st.text_input("Country")
        receipt_date = st.date_input("Date of Receipt", value=date.today())
        reporter = st.text_input("Reporter Type")
        product = st.text_input("Suspect Product")
        event = st.text_input("Reported Adverse Event")
        submitted = st.form_submit_button("Create Case")
    if submitted:
        cid = create_case()
        st.session_state.cases[cid]["data"].update({"Source": source, "Country": country, "Receipt Date": str(receipt_date), "Reporter Type": reporter, "Suspect Product": product, "Reported Event": event})
        st.success(f"Case created successfully: {cid}")

elif page == "Case Queue":
    st.header("Case Queue")
    if not st.session_state.cases:
        st.info("No cases available.")
    for cid, case in st.session_state.cases.items():
        with st.expander(f"{cid} | {case['stage']} | {case['status']}"):
            st.write("Created:", case["created"])
            if case["comments"]:
                st.write("Rework comments:")
                for comment in case["comments"]:
                    st.warning(comment)

elif page == "ICSR Case Processing":
    st.header("ICSR Case Processing")
    if not st.session_state.cases:
        st.warning("Create a case first.")
    else:
        cid = st.selectbox("Select Case ID", list(st.session_state.cases.keys()))
        case = st.session_state.cases[cid]
        st.write("Current workflow:", f"**{case['stage']}**")
        section_fields = {
            "General": ["Case Type", "Initial / Follow-up", "Awareness Date", "Country", "Case Seriousness"],
            "Source": ["Source Category", "Source Reference", "Date Source Received"],
            "Reporter": ["Reporter Initials", "Qualification", "Organisation", "Reporter Country"],
            "Patient": ["Patient Training ID", "Age", "Age Unit", "Sex", "Weight", "Medical History"],
            "Clinical Trial": ["Study ID", "Protocol Number", "Study Site", "Investigator"],
            "Product": ["Product Name", "Active Ingredient", "Product Classification", "Dosage", "Route", "Frequency", "Indication", "Reported Indication", "MedDRA Indication Coded Term", "MedDRA Indication Code", "Indication Coding Status", "Indication Dictionary Version", "WHODrug Preferred Name", "WHODrug Drug Code", "ATC Code", "Strength", "Dosage Form", "WHODrug Version", "Product Coding Status", "Batch Number", "Therapy Start Date", "Therapy Stop Date", "Dechallenge", "Rechallenge"],
            "Event": ["Verbatim Event", "MedDRA LLT", "MedDRA LLT Code", "MedDRA PT", "MedDRA PT Code", "MedDRA HLT", "MedDRA HLGT", "MedDRA SOC", "Primary SOC", "MedDRA Version", "Event Coding Status", "Coding Comments", "Event Onset Date", "Event Outcome", "Seriousness Criteria"],
            "Laboratory": ["Test Name", "Test Result", "Unit", "Reference Range"],
            "Causality": ["WHO-UMC Category", "Assessment Rationale"],
            "Literature": ["Article Title", "Authors", "Journal", "DOI", "Publication Year"],
            "Narrative": ["Structured Case Narrative"],
        }
        tab_names = list(section_fields) + ["Documents"]
        tabs = st.tabs(tab_names)
        for tab, (section, fields) in zip(tabs[:-1], section_fields.items()):
            with tab:
                st.subheader(f"{section} Information")
                with st.form(f"form_{section}_{cid}"):
                    values = {}
                    for field in fields:
                        if field == "WHO-UMC Category":
                            choices = ["Certain", "Probable/Likely", "Possible", "Unlikely", "Conditional/Unclassified", "Unassessable/Unclassifiable"]
                            current_value = case["data"].get(field, choices[0])
                            values[field] = st.selectbox(field, choices, index=choices.index(current_value) if current_value in choices else 0)
                        elif field == "Structured Case Narrative":
                            generated = generate_argus_like_narrative(cid, case)
                            values[field] = st.text_area(field, value=case["data"].get(field, generated), height=350, help="Original ARGUS/ARISg-inspired training format; not a copied proprietary template.")
                        else:
                            values[field] = st.text_input(field, value=str(case["data"].get(field, "")))
                    if st.form_submit_button("Save " + section):
                        case["data"].update(values)
                        log_action(cid, section + " information saved")
                        st.success(section + " information saved.")

        # Document Management is an ICSR tab immediately after Narrative (not a navigation page).
        with tabs[-1]:
            st.subheader("Case Documents")
            st.caption("Attach supporting training documents to this case. PDF is supported. Files are stored for this Streamlit session; use synthetic material only.")
            with st.form(f"document_upload_form_{cid}"):
                uploaded_files = st.file_uploader("Attach documents (PDF, Word, Excel, or image)", type=["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"case_documents_{cid}")
                category = st.selectbox("Document category", DOC_CATEGORIES, key=f"document_category_{cid}")
                description = st.text_input("Description", key=f"document_description_{cid}")
                add_documents = st.form_submit_button("Add documents")
            if add_documents:
                if not uploaded_files:
                    st.warning("Select at least one file to attach.")
                else:
                    documents = case.setdefault("documents", [])
                    existing = {doc["name"] for doc in documents}
                    added = 0
                    for uploaded in uploaded_files:
                        if uploaded.size > 10 * 1024 * 1024:
                            st.error(f"{uploaded.name} exceeds the 10 MB per-file limit.")
                        elif uploaded.name in existing:
                            st.warning(f"{uploaded.name} is already attached.")
                        else:
                            documents.append({"name": uploaded.name, "category": category, "description": description, "content_type": uploaded.type or "application/octet-stream", "content": uploaded.getvalue(), "size": uploaded.size, "uploaded": datetime.now().strftime("%d-%m-%Y %H:%M:%S")})
                            existing.add(uploaded.name)
                            added += 1
                    if added:
                        log_action(cid, f"{added} document(s) attached")
                        st.success(f"Attached {added} document(s).")
            documents = case.setdefault("documents", [])
            if documents:
                st.markdown("#### Attached documents")
                for index, document in enumerate(documents):
                    with st.expander(f"{document['name']} · {document['category']}"):
                        st.caption(f"{document['size'] / 1024:.1f} KB · Uploaded {document['uploaded']}")
                        if document.get("description"):
                            st.write(document["description"])
                        st.download_button("Download", document["content"], file_name=document["name"], mime=document["content_type"], key=f"download_{cid}_{index}")
                        if document["name"].lower().endswith(".pdf"):
                            try:
                                st.pdf(document["content"])
                            except AttributeError:
                                st.info("PDF preview is unavailable in this Streamlit version; use Download.")
            else:
                st.info("No documents attached to this case yet.")

        st.divider()
        st.subheader("Submit to Next Workflow")
        current = case["stage"]
        st.write("Current Stage:", f"**{current}**")
        if current != "Completed":
            next_stage = STAGES[STAGES.index(current) + 1]
            decision = "Pass to Next Stage"
            if current in ["Quality Review", "Medical Review"]:
                decision = st.selectbox("Review Decision", ["Select decision", "Pass", "Return for Rework"], key=f"decision_{cid}")
            comment = st.text_area("Submit Comments (Mandatory)", key=f"submit_comment_{cid}")
            if st.button("Confirm Submit", key=f"confirm_submit_{cid}"):
                if not comment.strip():
                    st.error("Please enter submission comments.")
                elif current in ["Quality Review", "Medical Review"] and decision == "Select decision":
                    st.error("Please select a review decision first.")
                else:
                    case.setdefault("comments", []).append(comment)
                    if decision == "Return for Rework":
                        case["stage"] = "Data Entry"
                        case["status"] = "Returned for Rework"
                    else:
                        case["stage"] = next_stage
                        case["status"] = "Completed" if next_stage == "Completed" else "In Progress"
                    case["history"].append(f"Submitted from {current} to {case['stage']}. Comment: {comment}")
                    log_action(cid, f"Workflow submitted from {current} to {case['stage']}")
                    st.rerun()
        else:
            st.success("This case is completed.")

elif page == "Workflow History":
    st.header("Workflow History")
    for cid, case in st.session_state.cases.items():
        with st.expander(cid):
            for item in case["history"]:
                st.write("•", item)

elif page == "Audit Log":
    st.header("Audit Trail")
    if st.session_state.audit:
        st.dataframe(st.session_state.audit, use_container_width=True)
    else:
        st.info("No audit activity yet.")

st.divider()
st.caption("PV Case Lab | Educational simulation only | Use synthetic patient and reporter information.")
