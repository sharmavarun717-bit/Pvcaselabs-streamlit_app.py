"""MedDRA event and WHODrug product training workspaces."""
from __future__ import annotations

import json
import uuid

import pandas as pd
import streamlit as st

import pv_coding as coding
import pv_storage as storage

storage.init_db()
coding.initialize()

ROLES = ["System Administrator", "PV Manager", "Intake User", "Triage User", "Data Entry User", "QC Reviewer", "Medical Reviewer", "Submission User", "Student", "Faculty/Trainer"]


def user_name() -> str:
    return f"Demo {st.session_state.get('demo_role', 'Student')}"


def _target_value(target: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        if target.get(key):
            return str(target[key])
    return ""


def get_targets(case_id: str, kind: str) -> list[dict]:
    case = storage.get_case(case_id)
    data = case["data"]
    key = "events" if kind == coding.MEDDRA else "products"
    targets = data.get(key, [])
    if not targets:
        # Seed one editable training target from older single-record case fields,
        # or create an empty target so coding practice can start immediately.
        if kind == coding.MEDDRA:
            initial = {"Reported verbatim term": data.get("Reported verbatim term", data.get("Verbatim Event", ""))}
        else:
            initial = {"Reported product name": data.get("Reported product name", data.get("Product Name", ""))}
        targets = [initial]
        data[key] = targets
    changed = False
    for target in targets:
        if not target.get("_record_id"):
            target["_record_id"] = str(uuid.uuid4())
            changed = True
    if changed or key not in data:
        data[key] = targets
        storage.update_case(case_id, data, user_name(), f"{kind} coding target initialized")
    return targets


def target_label(target: dict, index: int, kind: str) -> str:
    term = _target_value(target, ("Reported verbatim term", "Verbatim Event", "Reported product name", "Product Name"))
    return f"{index + 1}. {term or 'Untitled training record'}"


def render_dictionary_upload(dictionary_type: str) -> None:
    label = "MedDRA" if dictionary_type == coding.MEDDRA else "WHODrug"
    with st.expander(f"Import authorized {label} CSV", expanded=False):
        st.warning("Only upload dictionary data you are authorized to use. No official dictionary is bundled. Imported records are user-provided training references; the app does not verify licensing, authenticity, or official status.")
        uploaded = st.file_uploader("UTF-8 CSV dictionary file", type=["csv"], key=f"dict_upload_{dictionary_type}")
        confirmed = st.checkbox("I am authorized to use and import these dictionary data", key=f"dict_auth_{dictionary_type}")
        if st.button(f"Import {label} records", key=f"dict_import_{dictionary_type}"):
            if not uploaded:
                st.error("Choose a CSV file first.")
            else:
                try:
                    count = coding.import_dictionary_csv(dictionary_type, uploaded.getvalue(), user_name(), confirmed)
                    st.success(f"Imported {count} {label} records.")
                except ValueError as exc:
                    st.error(str(exc))


def meddra_fields(record: dict) -> dict:
    return {
        "LLT": record.get("term", ""),
        "LLT code": record.get("code", ""),
        "PT": record.get("pt", ""),
        "PT code": record.get("pt_code", ""),
        "HLT": record.get("hlt", ""),
        "HLGT": record.get("hlgt", ""),
        "SOC": record.get("soc", ""),
        "Primary SOC": record.get("primary_soc", ""),
        "MedDRA version": record.get("version", ""),
    }


def whodrug_fields(record: dict) -> dict:
    return {
        "WHODrug preferred name": record.get("term", ""),
        "Drug code": record.get("code", ""),
        "Active ingredient": record.get("active_ingredient", ""),
        "ATC code": record.get("atc_code", ""),
        "Drug record number": record.get("drug_record_number", ""),
        "Strength": record.get("strength", ""),
        "Pharmaceutical form": record.get("pharmaceutical_form", ""),
        "Manufacturer": record.get("manufacturer", ""),
        "Product country": record.get("country", ""),
        "WHODrug version": record.get("version", ""),
    }


def render_workspace(dictionary_type: str) -> None:
    is_meddra = dictionary_type == coding.MEDDRA
    title = "MedDRA Event Coding" if is_meddra else "WHODrug Product Coding"
    st.header(title)
    st.caption("Dictionary-assisted training when your organization provides authorized records, or clearly labelled manual practice. No terms/codes are fabricated by this app.")
    render_dictionary_upload(dictionary_type)
    cases = storage.get_cases()
    if not cases:
        st.info("Create a synthetic case in the main PV Case Lab app first.")
        return
    case_id = st.selectbox("Case", [case["case_id"] for case in cases], key=f"coding_case_{dictionary_type}")
    targets = get_targets(case_id, dictionary_type)
    target_idx = st.selectbox(
        "Event record" if is_meddra else "Product record",
        range(len(targets)),
        format_func=lambda i: target_label(targets[i], i, dictionary_type),
        key=f"coding_target_{dictionary_type}_{case_id}",
    )
    target = targets[target_idx]
    target_id = target["_record_id"]
    term_key = "Reported verbatim term" if is_meddra else "Reported product name"
    reported_term = st.text_input("Reported verbatim term" if is_meddra else "Reported product name", value=_target_value(target, (term_key, "Verbatim Event", "Product Name")), key=f"reported_{dictionary_type}_{case_id}_{target_id}")

    st.subheader("Search imported dictionary records")
    query = st.text_input("Search by reported term, preferred term, or code", value=reported_term, key=f"dict_search_{dictionary_type}_{case_id}_{target_id}")
    results = coding.search_dictionary(dictionary_type, query)
    selected_record = None
    if results:
        labels = [f"{r['search_term']} | {r['code']} | v{r['version'] or 'unspecified'}" for r in results]
        selected_idx = st.selectbox("Matching imported records", range(len(results)), format_func=lambda i: labels[i], key=f"dict_choice_{dictionary_type}_{case_id}_{target_id}")
        selected_record = results[selected_idx]["record"]
        st.caption(f"Record source: {results[selected_idx]['source']}. Selection is not independent verification of dictionary authenticity or licensing.")
    elif len(query.strip()) >= 2:
        st.info("No matching imported record found. You can still enter a clearly labelled manual training code below.")
    else:
        st.caption("Enter at least two characters to search imported records.")

    initial = (meddra_fields(selected_record) if is_meddra and selected_record else whodrug_fields(selected_record) if selected_record else {})
    prior = coding.get_coding(case_id, dictionary_type, target_id)
    if prior:
        initial = {**prior["coded_record"], **initial}
        # A saved choice/manual edit should remain visible until the user applies a new dictionary selection.
        if not selected_record:
            initial = prior["coded_record"]
    fields = list(meddra_fields({}).keys()) if is_meddra else list(whodrug_fields({}).keys())
    with st.form(f"save_coding_{dictionary_type}_{case_id}_{target_id}"):
        values = {field: st.text_input(field, value=str(initial.get(field, "")), key=f"coding_field_{dictionary_type}_{field}_{target_id}") for field in fields}
        status_options = ["Pending", "Training entry - not dictionary verified", "Dictionary selection - training only", "Reviewed"]
        default_status = prior["coding_status"] if prior and prior["coding_status"] in status_options else ("Dictionary selection - training only" if selected_record else "Training entry - not dictionary verified")
        status = st.selectbox("Coding status", status_options, index=status_options.index(default_status))
        reviewer = st.text_input("Reviewer", value=prior["reviewer"] if prior else "")
        comments = st.text_area("Coding comments", value=prior["comments"] if prior else "")
        submitted = st.form_submit_button("Save coding", type="primary")
    if submitted:
        if not reported_term.strip():
            st.error("Enter the reported term before saving coding.")
        elif status == "Reviewed" and not reviewer.strip():
            st.error("Enter a reviewer before marking the coding as Reviewed.")
        else:
            # Keep source record and imported dictionary identity alongside the captured hierarchy.
            coded_values = {**values, "dictionary_source": "Imported user-provided CSV" if selected_record else "Manual training entry; not verified", "dictionary_type": dictionary_type}
            if selected_record:
                coded_values["dictionary_record"] = selected_record
            coding.save_coding(case_id, dictionary_type, target_id, reported_term, coded_values, status, user_name(), reviewer, comments)
            target[term_key] = reported_term.strip()
            storage.update_case(case_id, storage.get_case(case_id)["data"], user_name(), f"{dictionary_type} coding target updated")
            st.success("Coding saved with a training-only status. Imported data are not represented as independently verified official coding.")
            st.rerun()
    history = coding.get_history(case_id, dictionary_type, target_id)
    if history:
        st.subheader("Coding history")
        rows = [{"Action": h["action"], "User": h["user_name"], "Timestamp": h["timestamp"], "Status": h["snapshot"].get("coding_status", ""), "Term": h["snapshot"].get("reported_term", "")} for h in history]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Use only authorized data. Manual training records are not official dictionary matches. Review coding using your organization’s licensed dictionary and procedures.")


def main() -> None:
    with st.sidebar:
        st.title("PV Case Lab · Coding")
        st.selectbox("Demonstration role (not authentication)", ROLES, key="demo_role")
    st.title("Coding Workspaces")
    meddra_tab, whodrug_tab = st.tabs(["MedDRA Event Coding", "WHODrug Product Coding"])
    with meddra_tab:
        render_workspace(coding.MEDDRA)
    with whodrug_tab:
        render_workspace(coding.WHODRUG)


main()
