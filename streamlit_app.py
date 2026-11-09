"""PV Case Lab: persistent, synthetic-data pharmacovigilance training simulator.

Educational demonstration only. It is not a validated production safety system.
"""
from __future__ import annotations

import json
import mimetypes
import sqlite3
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import pv_storage as storage

st.set_page_config(page_title="PV Case Lab", page_icon="🧬", layout="wide")
storage.init_db()

ROLES = ["System Administrator", "PV Manager", "Intake User", "Triage User", "Data Entry User", "QC Reviewer", "Medical Reviewer", "Submission User", "Student", "Faculty/Trainer"]
NAVIGATION = ["Dashboard", "Case Intake", "Case Processing", "Case Queue", "Product Coding", "MedDRA Event Coding", "Medical Review", "Causality Assessment", "Narrative Management", "Document Management", "Regulatory Reporting", "Literature Management", "Workflow Management", "Reports and Analytics", "Training and Assessment", "User Management", "Audit Trail", "Administration"]
DOC_CATEGORIES = ["Initial Source Document", "Follow-up Source Document", "Medical Records", "Discharge Summary", "Laboratory Reports", "Prescription", "Clinical Trial Documents", "Literature Articles", "Patient Consent", "Reporter Correspondence", "QC Documents", "Medical Review Documents", "Other"]
SERIOUSNESS = ["Serious", "Non-serious", "Unknown"]
CAUSALITY = ["Certain", "Probable/Likely", "Possible", "Unlikely", "Conditional/Unclassified", "Unassessable/Unclassifiable"]

if "demo_role" not in st.session_state:
    st.session_state.demo_role = "System Administrator"


def current_user() -> str:
    return f"Demo {st.session_state.demo_role}"


def cases_frame() -> pd.DataFrame:
    rows = storage.get_cases()
    return pd.DataFrame([{"Case ID": r["case_id"], "WWUID": r["wwuid"] or "", "Stage": r["stage"], "Status": r["status"], "Assigned User": r["assigned_user"], "Created": r["created_at"], **r["data"]} for r in rows])


def case_options() -> list[str]:
    return [r["case_id"] for r in storage.get_cases()]


def choose_case(label: str = "Select case") -> str | None:
    options = case_options()
    if not options:
        st.info("Create a training case first.")
        return None
    return st.selectbox(label, options, key=f"case_select_{label}")


def save_case_section(case_id: str, section: str, values: dict) -> None:
    case = storage.get_case(case_id)
    data = case["data"]
    data.update(values)
    storage.update_case(case_id, data, current_user(), f"{section} saved")
    st.success(f"{section} saved.")


def render_case_fields(case_id: str, section: str, fields: list[str], text_fields: set[str] | None = None) -> None:
    case = storage.get_case(case_id)
    data = case["data"]
    text_fields = text_fields or set()
    with st.form(f"edit_{section}_{case_id}"):
        values = {}
        for field in fields:
            default = str(data.get(field, ""))
            if field in text_fields:
                values[field] = st.text_area(field, value=default, key=f"{section}_{field}_{case_id}")
            elif field == "Case Seriousness":
                values[field] = st.selectbox(field, SERIOUSNESS, index=SERIOUSNESS.index(default) if default in SERIOUSNESS else 2)
            elif field == "WHO-UMC Category":
                values[field] = st.selectbox(field, CAUSALITY, index=CAUSALITY.index(default) if default in CAUSALITY else 0)
            else:
                values[field] = st.text_input(field, value=default, key=f"{section}_{field}_{case_id}")
        if st.form_submit_button(f"Save {section}"):
            save_case_section(case_id, section, values)


def render_narrative(data: dict) -> str:
    def val(key: str) -> str:
        value = str(data.get(key, "")).strip()
        return value if value else "Not Reported"
    parts = [
        ("1. Case Introduction", f"Training case {val('Case ID')} was received from {val('Source type')} in {val('Country')}. Classification: {val('Initial/follow-up classification')} ."),
        ("2. Patient Demographics", f"Patient age: {val('Age')} {val('Age unit')}; sex: {val('Sex')}; patient training ID: {val('Patient ID')}."),
        ("3. Medical History", val("Medical history")),
        ("4. Suspect Product Information", f"Reported product: {val('Reported product name')}; active ingredient: {val('Active ingredient')}."),
        ("5. Product Exposure", f"Dose: {val('Dose')}; route: {val('Route')}; frequency: {val('Frequency')}; start/stop dates: {val('Product start date')} / {val('Product stop date')}."),
        ("6. Adverse Event Description", f"Reported event: {val('Reported verbatim term')}. {val('Event description')}"),
        ("7. Event Onset", f"Onset date: {val('Event onset date')}; end date: {val('Event end date')}."),
        ("8. Clinical Course", val("Clinical course")),
        ("9. Laboratory Findings", val("Laboratory findings")),
        ("10. Treatment and Management", val("Treatment and management")),
        ("11. Dechallenge and Rechallenge", f"Dechallenge: {val('Dechallenge')}; rechallenge: {val('Rechallenge')}."),
        ("12. Event Outcome", f"Outcome: {val('Event outcome')}; seriousness: {val('Case Seriousness')}."),
        ("13. Causality Assessment", f"{val('WHO-UMC Category')}. Rationale: {val('Assessment rationale')}"),
        ("14. Overall Case Summary", f"This is a synthetic educational case. Information not provided in the case record is shown as Not Reported; this narrative requires human review."),
    ]
    return "\n\n".join(f"{heading}\n{text}" for heading, text in parts)


def render_dashboard() -> None:
    st.header("PV Department Dashboard")
    cases = storage.get_cases()
    if not cases:
        st.info("No cases yet. Start in Case Intake to create a synthetic training case.")
        return
    df = cases_frame()
    serious = sum(c["data"].get("Case Seriousness") == "Serious" for c in cases)
    initial = sum(c["data"].get("Initial/follow-up classification", "Initial") == "Initial" for c in cases)
    pending_stages = {stage: sum(c["stage"] == stage for c in cases) for stage in storage.STAGES}
    metrics = [
        ("Total cases", len(cases)), ("New / intake", pending_stages["Case Intake"]),
        ("Serious", serious), ("Non-serious", sum(c["data"].get("Case Seriousness") == "Non-serious" for c in cases)),
        ("Initial", initial), ("Follow-up", len(cases) - initial),
    ]
    cols = st.columns(3)
    for i, (label, value) in enumerate(metrics):
        cols[i % 3].metric(label, value)
    st.subheader("Cases by workflow stage")
    st.bar_chart(pd.DataFrame({"Cases": pending_stages}))
    left, right = st.columns(2)
    with left:
        st.subheader("Cases by source")
        source_counts = df.get("Source type", pd.Series(dtype=str)).replace("", "Not reported").value_counts()
        st.bar_chart(source_counts)
    with right:
        st.subheader("Cases by country")
        country_counts = df.get("Country", pd.Series(dtype=str)).replace("", "Not reported").value_counts().head(10)
        st.bar_chart(country_counts)
    st.caption("Averages, overdue calculations and monthly trends require complete dates and are not yet part of this phase.")
    st.dataframe(df[[col for col in ["Case ID", "Stage", "Status", "Case Seriousness", "Source type", "Country", "Created"] if col in df.columns]], use_container_width=True, hide_index=True)


def render_intake() -> None:
    st.header("Case Intake")
    st.caption("Use fictional training data only. WWUID uniqueness is enforced when provided.")
    with st.form("intake_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        source = c1.selectbox("Source type", ["Spontaneous", "Clinical Trial", "Literature", "Solicited", "Patient Support Program", "Regulatory Authority", "Other"])
        classification = c2.selectbox("Initial/follow-up classification", ["Initial", "Follow-up"])
        country = c1.text_input("Country")
        date_received = c2.date_input("Date received", value=date.today())
        awareness = c1.date_input("Date of awareness", value=date.today())
        organization = c2.text_input("Organization")
        report_type = c1.text_input("Report type")
        seriousness = c2.selectbox("Case seriousness", SERIOUSNESS)
        wwuid = c1.text_input("Worldwide Unique Case Identification Number (optional)")
        duplicate_status = c2.selectbox("Duplicate check status", ["Not checked", "No potential duplicate", "Potential duplicate"])
        assigned = c1.text_input("Assigned user", value=current_user())
        due = c2.date_input("Due date", value=date.today())
        intake_comments = st.text_area("Intake comments")
        valid = st.checkbox("Four minimum criteria appear available (identifiable patient, reporter, product, event)")
        create = st.form_submit_button("Save intake case", type="primary")
    if create:
        if not country.strip():
            st.error("Country is required for this training intake form.")
            return
        payload = {"Source type": source, "Initial/follow-up classification": classification, "Country": country.strip(), "Date received": str(date_received), "Date of awareness": str(awareness), "Organization": organization.strip(), "Report type": report_type.strip(), "Case Seriousness": seriousness, "WWUID": wwuid.strip(), "Duplicate check status": duplicate_status, "Assigned User": assigned.strip(), "Due Date": str(due), "Intake Comments": intake_comments.strip(), "Case validity": "Valid for exercise" if valid else "Not confirmed"}
        try:
            cid = storage.create_case(payload, current_user())
            st.success(f"Created {cid} in Case Intake.")
            matches = [c for c in storage.get_cases() if c["case_id"] != cid and c["data"].get("Country", "").casefold() == country.strip().casefold() and c["data"].get("Source type") == source]
            if matches:
                st.warning("Possible duplicates found for the same source and country: " + ", ".join(c["case_id"] for c in matches))
        except sqlite3.IntegrityError:
            st.error("That WWUID is already in use. Reopen the existing case or verify the identifier.")


def render_processing() -> None:
    st.header("ICSR Case Processing")
    cid = choose_case()
    if not cid:
        return
    case = storage.get_case(cid)
    data = case["data"]
    st.info(f"**{cid}** · Stage: **{case['stage']}** · Status: {case['status']}")
    sections = {
        "General": ["WWUID", "Initial/follow-up classification", "Date received", "Most recent information date", "Country", "Source type", "Case validity", "Case Seriousness", "Reportability", "Case status"],
        "Source": ["Primary source", "Secondary source", "Literature source", "Regulatory authority", "Company reference", "Report source", "Receipt dates"],
        "Reporter": ["Reporter type", "First name", "Last name", "Qualification", "Organization", "Reporter country", "Email", "Telephone", "Primary reporter indicator"],
        "Patient": ["Patient initials", "Patient ID", "Date of birth", "Age", "Age unit", "Sex", "Weight", "Height", "Medical history", "Relevant medical conditions", "Pregnancy information", "Patient medical history comments"],
        "Clinical Trial": ["Study ID", "Protocol number", "Investigator", "Sponsor", "Study type", "Study blind status", "Trial site", "Randomization number", "Treatment arm"],
        "Product": ["Reported product name", "Product role", "Generic name", "Active ingredient", "Manufacturer", "Product country", "Strength", "Dosage form", "Route", "Dose", "Frequency", "Product start date", "Product stop date", "Indication", "Batch number", "Expiry date", "Dechallenge", "Rechallenge", "WHODrug preferred name", "Drug code", "ATC code", "WHODrug version", "Product coding status", "Product coding comments"],
        "Event": ["Reported verbatim term", "Event description", "Event onset date", "Event end date", "Event outcome", "Seriousness criteria", "Hospitalization", "Life-threatening status", "Disability", "Congenital anomaly", "Other medically important condition", "Event comments", "LLT", "LLT code", "PT", "PT code", "HLT", "HLGT", "SOC", "Primary SOC", "MedDRA version", "Event coding status", "Coding comments"],
        "Laboratory": ["Test name", "Test date", "Result", "Unit", "Reference range", "Abnormal indicator", "Laboratory comments"],
        "Causality": ["WHO-UMC Category", "Assessment rationale", "Reviewer", "Assessment date", "Assessment comments"],
        "Literature": ["Article title", "Authors", "Journal", "DOI", "Publication year", "PMID", "Literature reference", "Literature assessment"],
        "Narrative": ["Clinical course", "Laboratory findings", "Treatment and management", "Structured Case Narrative"],
    }
    tabs = st.tabs(list(sections))
    for tab, (section, fields) in zip(tabs, sections.items()):
        with tab:
            st.subheader(f"{section} information")
            render_case_fields(cid, section, fields, {"Medical history", "Relevant medical conditions", "Patient medical history comments", "Event description", "Event comments", "Assessment rationale", "Assessment comments", "Clinical course", "Laboratory findings", "Treatment and management", "Structured Case Narrative", "Coding comments", "Product coding comments"})
    st.subheader("Repeatable training records")
    repeat_tabs = st.tabs(["Products", "Events", "Laboratory tests"])
    for tab, key, label, fields in [
        (repeat_tabs[0], "products", "Product", ["Reported product name", "Product role", "Dose", "Route", "Frequency"]),
        (repeat_tabs[1], "events", "Event", ["Reported verbatim term", "Event onset date", "Event outcome", "Case Seriousness"]),
        (repeat_tabs[2], "labs", "Laboratory test", ["Test name", "Test date", "Result", "Unit", "Reference range"]),
    ]:
        with tab:
            items = data.get(key, [])
            if items:
                st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
            with st.form(f"add_{key}_{cid}"):
                record = {field: st.text_input(field, key=f"repeat_{key}_{field}_{cid}") for field in fields}
                if st.form_submit_button(f"Add {label}"):
                    if not any(value.strip() for value in record.values()):
                        st.error("Enter at least one value before adding a record.")
                    else:
                        data.setdefault(key, []).append(record)
                        storage.update_case(cid, data, current_user(), f"{label} record added")
                        st.success(f"{label} added.")
                        st.rerun()
    st.caption("Repeatable records are training records stored with the case. Dictionary coding is manual; no official code data is bundled.")


def render_queue() -> None:
    st.header("Case Queue")
    query = st.text_input("Search by case ID, WWUID, or case data")
    rows = storage.get_cases(query)
    if rows:
        df = pd.DataFrame([{"Case ID": x["case_id"], "WWUID": x["wwuid"] or "", "Stage": x["stage"], "Status": x["status"], "Assigned User": x["assigned_user"], "Due date": x["due_date"], "Created": x["created_at"]} for x in rows])
        st.dataframe(df, use_container_width=True, hide_index=True)
        selected = st.selectbox("Reopen case", [r["case_id"] for r in rows])
        st.json(storage.get_case(selected)["data"])
    else:
        st.info("No matching cases.")


def render_coding(product: bool = False) -> None:
    title = "Product Coding – WHODrug training" if product else "MedDRA Event Coding"
    st.header(title)
    st.warning("Training/manual entry only. No official dictionary is bundled; never enter invented official codes or claim verification. Import requires authorized/licensed dictionary data and is not enabled in this phase.")
    cid = choose_case()
    if not cid:
        return
    fields = (["Reported product name", "WHODrug preferred name", "Drug code", "Active ingredient", "ATC code", "Drug record number", "Strength", "Pharmaceutical form", "Manufacturer", "Product country", "WHODrug version", "Product coding status", "Product coding comments", "Coder", "Reviewer", "Coding date"] if product else ["Reported verbatim term", "LLT", "LLT code", "PT", "PT code", "HLT", "HLGT", "SOC", "Primary SOC", "MedDRA version", "Event coding status", "Coding comments", "Coder", "Coding date", "Reviewer", "Review status"])
    render_case_fields(cid, "Product coding" if product else "MedDRA coding", fields, {"Product coding comments", "Coding comments"})


def render_review(medical: bool = False) -> None:
    title = "Medical Review" if medical else "Quality Control Review"
    st.header(title)
    cid = choose_case()
    if not cid:
        return
    case = storage.get_case(cid)
    st.write(f"Case **{cid}** · Current stage: **{case['stage']}**")
    checks = ["Mandatory fields present", "Case validity assessed", "Patient and reporter reviewed", "Product and event information reviewed", "Coding reviewed", "Seriousness assessment reviewed", "Narrative reviewed", "Supporting documents checked"]
    if medical:
        st.json({k: case["data"].get(k, "Not Reported") for k in ["Patient ID", "Medical history", "Reported product name", "Reported verbatim term", "Case Seriousness", "WHO-UMC Category", "Structured Case Narrative"]})
    else:
        st.subheader("QC checklist")
        for item in checks:
            st.checkbox(item, key=f"qc_{cid}_{item}")
    decision = st.selectbox("Review decision", ["Select decision", "Pass", "Return for Rework"], key=f"review_decision_{medical}_{cid}")
    comments = st.text_area("Review comments (required for rework)", key=f"review_comments_{medical}_{cid}")
    if st.button("Record review decision", key=f"save_review_{medical}_{cid}"):
        if decision == "Select decision":
            st.error("Select a review decision.")
        elif decision == "Return for Rework" and not comments.strip():
            st.error("Comments are mandatory for rework.")
        else:
            storage.save_review(cid, "Medical" if medical else "QC", decision, comments, current_user())
            if case["stage"] == ("Medical Review" if medical else "Quality Control Review"):
                target = "Data Entry" if decision == "Return for Rework" else ("Submission" if medical else "Medical Review")
                storage.transition_case(cid, target, decision, comments, current_user())
            st.success("Review recorded. Workflow changed only when the case was at this review stage.")
            st.rerun()
    reviews = storage.get_reviews(cid)
    if reviews:
        st.subheader("Review history")
        st.dataframe(pd.DataFrame(reviews), use_container_width=True, hide_index=True)


def render_documents() -> None:
    st.header("Document Management")
    cid = choose_case()
    if not cid:
        return
    st.caption("Files are stored on the server in a dedicated data/documents directory. Local/Community Cloud storage may be ephemeral; use persistent external storage for durable multi-user operation.")
    with st.form(f"upload_document_{cid}"):
        uploads = st.file_uploader("Upload document(s)", type=["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"], accept_multiple_files=True)
        category = st.selectbox("Document category", DOC_CATEGORIES)
        received = st.date_input("Date received", value=date.today())
        doc_date = st.date_input("Document date", value=date.today(), key=f"doc_date_{cid}")
        description = st.text_input("Description")
        submitted = st.form_submit_button("Save documents")
    if submitted:
        if not uploads:
            st.error("Choose at least one file.")
        else:
            for upload in uploads:
                try:
                    storage.add_document(cid, upload.name, category, upload.type or mimetypes.guess_type(upload.name)[0] or "application/octet-stream", upload.getvalue(), description, str(received), str(doc_date), current_user())
                except ValueError as exc:
                    st.error(f"{upload.name}: {exc}")
            st.success("Valid documents saved.")
            st.rerun()
    docs = storage.list_documents(cid)
    if not docs:
        st.info("No documents attached to this case.")
        return
    st.subheader("Case documents")
    for doc in docs:
        with st.expander(f"{doc['name']} · v{doc['current_version']} · {doc['review_status']}"):
            st.write(f"Category: {doc['category']} | {doc['size_bytes'] / 1024:.1f} KB | Uploaded by {doc['uploaded_by']} at {doc['uploaded_at']}")
            st.write(doc["description"])
            path = Path(doc["stored_path"])
            if path.exists():
                st.download_button("Download current version", path.read_bytes(), file_name=doc["name"], mime=doc["content_type"], key=f"download_{doc['document_id']}")
                if doc["content_type"] == "application/pdf":
                    st.caption("PDF preview is not included in this phase.")
            replace = st.file_uploader("Replace with new version", type=["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"], key=f"replace_{doc['document_id']}")
            if replace and st.button("Save new version", key=f"replace_btn_{doc['document_id']}"):
                storage.replace_document(doc["document_id"], replace.name, replace.getvalue(), replace.type or "application/octet-stream", current_user())
                st.success("New version saved; previous version retained.")
                st.rerun()
            review_status = st.selectbox("Review status", ["Pending review", "Approved", "Rejected"], key=f"doc_status_{doc['document_id']}")
            review_comments = st.text_input("Reviewer comments", key=f"doc_comment_{doc['document_id']}")
            if st.button("Save document review", key=f"doc_review_{doc['document_id']}"):
                storage.set_document_review(doc["document_id"], review_status, review_comments, current_user())
                st.success("Document review saved.")
            versions = storage.document_versions(doc["document_id"])
            st.caption("Version history")
            st.dataframe(pd.DataFrame(versions)[["version", "size_bytes", "uploaded_by", "uploaded_at"]], use_container_width=True, hide_index=True)


def render_narrative_page() -> None:
    st.header("Narrative Management")
    cid = choose_case()
    if not cid:
        return
    case = storage.get_case(cid)
    data = case["data"]
    generated = render_narrative({**data, "Case ID": cid})
    if st.button("Generate / Regenerate Narrative", key=f"generate_narrative_{cid}"):
        data["Generated Narrative"] = generated
        data.setdefault("Narrative Versions", []).append({"version": len(data.get("Narrative Versions", [])) + 1, "text": generated, "created": storage.utc_now(), "author": current_user()})
        storage.update_case(cid, data, current_user(), "Narrative generated")
        st.success("Draft generated from available case data; human review is required.")
    text = st.text_area("Edit narrative draft", value=data.get("Generated Narrative", generated), height=400, key=f"narrative_text_{cid}")
    if st.button("Save Narrative", key=f"save_narrative_{cid}"):
        old = data.get("Generated Narrative", "")
        data["Generated Narrative"] = text
        data.setdefault("Narrative Versions", []).append({"version": len(data.get("Narrative Versions", [])) + 1, "text": text, "created": storage.utc_now(), "author": current_user()})
        storage.update_case(cid, data, current_user(), "Narrative edited and saved")
        st.success("Narrative version saved. Human review is required before approval.")
    if data.get("Narrative Versions"):
        st.subheader("Saved versions")
        versions = data["Narrative Versions"]
        for item in versions:
            st.write(f"Version {item['version']} · {item['created']} · {item['author']}")
        if len(versions) > 1:
            a, b = st.columns(2)
            a.text_area("Previous", value=versions[-2]["text"], height=150, disabled=True)
            b.text_area("Current", value=versions[-1]["text"], height=150, disabled=True)
    st.download_button("Download narrative text", text, file_name=f"{cid}_narrative.txt", mime="text/plain")


def render_workflow() -> None:
    st.header("Workflow Management")
    cid = choose_case()
    if not cid:
        return
    case = storage.get_case(cid)
    st.progress((storage.STAGES.index(case["stage"]) + 1) / len(storage.STAGES))
    st.write(" → ".join(storage.STAGES))
    st.info(f"Current stage: **{case['stage']}** · Assigned to: {case['assigned_user'] or 'Unassigned'}")
    data = case["data"]
    with st.form(f"assignment_{cid}"):
        assigned = st.text_input("Assigned user", value=case["assigned_user"])
        due = st.text_input("Due date (YYYY-MM-DD)", value=case["due_date"])
        save = st.form_submit_button("Save assignment")
    if save:
        data["Assigned User"] = assigned
        data["Due Date"] = due
        storage.update_case(cid, data, current_user(), "Case assignment updated")
        st.success("Assignment saved.")
    if case["stage"] != "Completed":
        current_index = storage.STAGES.index(case["stage"])
        next_stage = storage.STAGES[current_index + 1]
        if case["stage"] in ("Quality Control Review", "Medical Review"):
            st.caption("Review stage decisions are captured in the corresponding review module.")
        else:
            comments = st.text_area("Handover comments (required)", key=f"handover_comments_{cid}")
            if st.button(f"Confirm handover to {next_stage}", key=f"handover_{cid}"):
                if not comments.strip():
                    st.error("Enter handover comments before progressing.")
                else:
                    storage.transition_case(cid, next_stage, "Pass", comments, current_user())
                    st.success(f"Case moved to {next_stage}.")
                    st.rerun()
    history = storage.get_workflow(cid)
    if history:
        st.subheader("Workflow history")
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)


def render_regulatory() -> None:
    st.header("Regulatory Reporting – training simulation")
    st.warning("This produces an educational XML sketch only. It is not a valid ICH E2B(R3) message and does not submit to any authority.")
    cid = choose_case()
    if not cid:
        return
    case = storage.get_case(cid)
    with st.form(f"submission_{cid}"):
        destination = st.text_input("Training destination")
        sub_type = st.selectbox("Submission type", ["Initial", "Follow-up"])
        due = st.date_input("Submission due date", value=date.today())
        st.form_submit_button("Save simulation metadata")
    if st.button("Generate training XML", key=f"xml_{cid}"):
        root = ET.Element("TrainingICSR", attrib={"caseId": cid, "trainingOnly": "true"})
        ET.SubElement(root, "Destination").text = destination or "Not provided"
        ET.SubElement(root, "SubmissionType").text = sub_type
        ET.SubElement(root, "DueDate").text = str(due)
        record = ET.SubElement(root, "CaseData")
        for key, value in case["data"].items():
            node = ET.SubElement(record, "Field", name=str(key))
            node.text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
        xml = ET.tostring(root, encoding="unicode")
        st.code(xml, language="xml")
        st.download_button("Download training XML", xml, file_name=f"{cid}_training.xml", mime="application/xml")
        storage.audit(cid, "Training XML generated", current_user())


def render_literature() -> None:
    st.header("Literature Management")
    cid = choose_case("Link to case (optional)")
    if cid is None and not case_options():
        cid = ""
    with st.form("literature_record"):
        title = st.text_input("Article title")
        authors = st.text_input("Authors")
        journal = st.text_input("Journal")
        doi = st.text_input("DOI")
        pmid = st.text_input("PMID")
        pub_year = st.text_input("Publication year")
        screening = st.selectbox("Screening status", ["Unscreened", "Relevant", "Not relevant", "Potential ICSR"])
        duplicate = st.selectbox("Duplicate assessment", ["Not assessed", "Not duplicate", "Potential duplicate"])
        comments = st.text_area("Reviewer comments")
        save = st.form_submit_button("Save literature record")
    if save:
        data = storage.get_case(cid)["data"] if cid else {}
        data.setdefault("literature_records", []).append({"title": title, "authors": authors, "journal": journal, "doi": doi, "pmid": pmid, "publication_year": pub_year, "screening": screening, "duplicate": duplicate, "comments": comments})
        if cid:
            storage.update_case(cid, data, current_user(), "Literature record saved")
        else:
            st.session_state["unlinked_literature"] = st.session_state.get("unlinked_literature", []) + [data["literature_records"][-1]]
        st.success("Literature record saved.")
    if cid and storage.get_case(cid)["data"].get("literature_records"):
        st.dataframe(pd.DataFrame(storage.get_case(cid)["data"]["literature_records"]), use_container_width=True, hide_index=True)


def render_training() -> None:
    st.header("Training and Assessment")
    st.info("Practice mode uses a synthetic exercise and provides immediate feedback. Subjective work requires faculty evaluation; this is not a credentialing system.")
    level = st.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"])
    question = st.radio("Which four minimum elements are generally needed to constitute a valid ICSR?", ["Identifiable patient, identifiable reporter, suspect product, adverse event", "Patient age, product batch, country, narrative", "Reporter email, product code, event code, seriousness"], key=f"training_q_{level}")
    if st.button("Submit answer"):
        correct = question.startswith("Identifiable patient")
        st.session_state["training_score"] = st.session_state.get("training_score", 0) + int(correct)
        if correct:
            st.success("Correct. A valid report requires an identifiable patient, identifiable reporter, suspect medicinal product, and suspected adverse reaction/event.")
        else:
            st.error("Not quite. Review the four minimum ICSR criteria and try again.")
    st.metric("Correct answers this session", st.session_state.get("training_score", 0))
    st.subheader("Training completion")
    st.caption("Faculty-managed submissions, persistent student results and certificates are planned for a later phase.")


def main() -> None:
    with st.sidebar:
        st.title("🧬 PV Case Lab")
        st.caption("Training simulator �� synthetic data only")
        page = st.radio("Navigation", NAVIGATION)
        st.divider()
        st.selectbox("Demonstration role (not authentication)", ROLES, key="demo_role")
        st.caption("Demo role selection does not enforce production-grade access control.")
    st.title("🧬 PV CASE LAB")
    st.caption("Original pharmacovigilance training simulation · Not a validated production safety system")
    renderers = {
        "Dashboard": render_dashboard,
        "Case Intake": render_intake,
        "Case Processing": render_processing,
        "Case Queue": render_queue,
        "Product Coding": lambda: render_coding(product=True),
        "MedDRA Event Coding": lambda: render_coding(product=False),
        "Medical Review": lambda: render_review(medical=True),
        "Causality Assessment": lambda: render_case_causality(),
        "Narrative Management": render_narrative_page,
        "Document Management": render_documents,
        "Regulatory Reporting": render_regulatory,
        "Literature Management": render_literature,
        "Workflow Management": render_workflow,
        "Reports and Analytics": render_reports,
        "Training and Assessment": render_training,
        "User Management": render_users,
        "Audit Trail": render_audit,
        "Administration": render_admin,
    }
    renderers[page]()
    st.divider()
    st.caption("PV Case Lab | Educational simulation only | Use synthetic patient and reporter information. Local SQLite/file storage may be ephemeral on hosted platforms.")


def render_case_causality() -> None:
    st.header("Causality Assessment")
    cid = choose_case()
    if cid:
        render_case_fields(cid, "Causality assessment", ["Product-event combination", "WHO-UMC Category", "Assessment rationale", "Reviewer", "Assessment date", "Assessment comments"], {"Assessment rationale", "Assessment comments"})
        st.caption("Assessments are educational and require qualified human interpretation.")


def render_reports() -> None:
    st.header("Reports and Analytics")
    df = cases_frame()
    if df.empty:
        st.info("No case data available.")
        return
    stage = st.multiselect("Workflow stage", storage.STAGES, default=storage.STAGES)
    filtered = df[df["Stage"].isin(stage)]
    st.metric("Matching cases", len(filtered))
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.download_button("Export filtered cases as CSV", filtered.to_csv(index=False).encode("utf-8"), file_name="pv_caselab_cases.csv", mime="text/csv")
    st.caption("Analytics are descriptive only. Rejection rates and turnaround metrics are deferred until sufficient review/timing data are captured.")


def render_users() -> None:
    st.header("User Management")
    st.warning("Demonstration role selector only; it is not authentication or a security boundary. Do not use for production access control.")
    st.write("Selected demo role:", st.session_state.demo_role)
    st.dataframe(pd.DataFrame([{"Role": role, "Mode": "Demonstration"} for role in ROLES]), use_container_width=True, hide_index=True)
    st.caption("Production deployment needs a trusted identity provider and server-enforced authorization.")


def render_audit() -> None:
    st.header("Audit Trail")
    cid = st.selectbox("Filter by case", ["All cases"] + case_options())
    rows = storage.get_audit("" if cid == "All cases" else cid)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("Training audit records are editable by database administrators and are not immutable or regulatory validated.")
    else:
        st.info("No audit records found.")


def render_admin() -> None:
    st.header("Administration")
    st.write(f"SQLite database: `{storage.DB_PATH}`")
    st.write(f"Document storage: `{storage.DOCUMENT_DIR}`")
    if st.button("Prepare SQLite backup"):
        backup = storage.DATA_DIR / f"pv_caselab_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"
        storage.backup_database(backup)
        st.success(f"Backup created at {backup}.")
        st.download_button("Download backup", backup.read_bytes(), file_name=backup.name, mime="application/octet-stream")
    st.caption("Database schema initializes safely with CREATE TABLE IF NOT EXISTS. Hosted ephemeral filesystems require external persistent storage for durable use.")


if __name__ == "__main__":
    main()
