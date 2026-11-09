from pathlib import Path

import streamlit as st

import pv_storage as storage

st.set_page_config(page_title="PV Case Lab Documents", page_icon="📎", layout="wide")
storage.init_db()

DOCUMENT_CATEGORIES = [
    "Initial Source Document", "Follow-up Source Document", "Medical Records",
    "Discharge Summary", "Laboratory Reports", "Prescription",
    "Clinical Trial Documents", "Literature Articles", "Patient Consent",
    "Reporter Correspondence", "QC Documents", "Medical Review Documents", "Other",
]
ALLOWED_EXTENSIONS = ["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"]
MAX_FILE_SIZE = 10 * 1024 * 1024


def user_name() -> str:
    return f"Demo {st.session_state.get('demo_role', 'Student')}"


def render_documents() -> None:
    st.header("Document Management")
    cases = storage.get_cases()
    if not cases:
        st.info("Create a training case before attaching documents.")
        return

    case_id = st.selectbox(
        "Attach document to case",
        [case["case_id"] for case in cases],
        key="document_case_id",
    )
    st.caption(
        "PDF attachments are supported, along with Word, Excel, and image files. "
        "Use synthetic training material only. Files are stored on the app server."
    )

    with st.form(f"upload_document_{case_id}"):
        uploads = st.file_uploader(
            "Attach documents (PDF supported)",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="Maximum 10 MB per file. Allowed: PDF, DOC/DOCX, XLS/XLSX, JPG/JPEG, PNG.",
            key=f"document_upload_{case_id}",
        )
        category = st.selectbox("Document category", DOCUMENT_CATEGORIES)
        description = st.text_input("Description")
        submitted = st.form_submit_button("Save attachments", type="primary")

    if submitted:
        if not uploads:
            st.error("Select at least one file to attach.")
        else:
            saved = 0
            for upload in uploads:
                suffix = Path(upload.name).suffix.lower().lstrip(".")
                if suffix not in ALLOWED_EXTENSIONS:
                    st.error(f"{upload.name}: unsupported file type.")
                    continue
                if upload.size > MAX_FILE_SIZE:
                    st.error(f"{upload.name}: exceeds the 10 MB per-file limit.")
                    continue
                try:
                    storage.add_document(
                        case_id=case_id,
                        name=Path(upload.name).name,
                        category=category,
                        content_type=upload.type or "application/octet-stream",
                        content=upload.getvalue(),
                        description=description,
                        date_received="",
                        document_date="",
                        user_name=user_name(),
                    )
                    saved += 1
                except (ValueError, OSError) as exc:
                    st.error(f"Could not save {upload.name}: {exc}")
            if saved:
                st.success(f"Attached {saved} file(s) to {case_id}.")
                st.rerun()

    st.subheader("Attached documents")
    filter_text = st.text_input("Filter documents by name or category", key=f"document_filter_{case_id}")
    docs = storage.list_documents(case_id)
    if filter_text.strip():
        needle = filter_text.casefold()
        docs = [doc for doc in docs if needle in doc["name"].casefold() or needle in doc["category"].casefold()]

    if not docs:
        st.info("No matching attachments for this case.")
        return

    for document in docs:
        with st.expander(
            f"{document['name']} · {document['category']} · v{document['current_version']} · {document['review_status']}"
        ):
            st.write(document.get("description") or "No description")
            stored_path = Path(document["stored_path"])
            if not stored_path.is_file():
                st.error("The stored file is missing. Restore it from backup or attach the document again.")
                continue

            file_bytes = stored_path.read_bytes()
            st.download_button(
                "Download attachment",
                data=file_bytes,
                file_name=document["name"],
                mime=document["content_type"],
                key=f"download_attachment_{document['document_id']}",
            )
            if Path(document["name"]).suffix.lower() == ".pdf":
                with st.expander("Preview PDF"):
                    # st.pdf is available in current Streamlit versions used by this project.
                    if hasattr(st, "pdf"):
                        st.pdf(file_bytes)
                    else:
                        st.info("PDF preview requires a newer Streamlit version. Download the PDF to view it.")

            replacement = st.file_uploader(
                "Attach a replacement version",
                type=ALLOWED_EXTENSIONS,
                key=f"replace_attachment_{document['document_id']}",
            )
            if replacement and st.button(
                "Save as new version",
                key=f"save_replacement_{document['document_id']}",
            ):
                suffix = Path(replacement.name).suffix.lower().lstrip(".")
                if suffix not in ALLOWED_EXTENSIONS:
                    st.error("Unsupported file type.")
                elif replacement.size > MAX_FILE_SIZE:
                    st.error("Replacement exceeds the 10 MB per-file limit.")
                else:
                    storage.replace_document(
                        document["document_id"],
                        Path(replacement.name).name,
                        replacement.getvalue(),
                        replacement.type or "application/octet-stream",
                        user_name(),
                    )
                    st.success("New version saved; previous version retained.")
                    st.rerun()


def main() -> None:
    with st.sidebar:
        st.title("PV Case Lab")
        st.selectbox(
            "Demonstration role (not authentication)",
            ["System Administrator", "PV Manager", "Data Entry User", "QC Reviewer", "Medical Reviewer", "Student", "Faculty/Trainer"],
            key="demo_role",
        )
        st.caption("Synthetic training data only.")
    render_documents()
    st.divider()
    st.caption("PV Case Lab | Educational simulation only | Not a validated production safety system.")


main()
