import streamlit as st
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

# -----------------------------------------
# Paths and basic storage helpers
# -----------------------------------------

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
COURSES_FILE = DATA_DIR / "courses.json"
COURSES_DIR = DATA_DIR / "courses"


def ensure_data_dirs():
    """Ensure the data directories and files exist."""
    DATA_DIR.mkdir(exist_ok=True)
    COURSES_DIR.mkdir(exist_ok=True)
    if not COURSES_FILE.exists():
        COURSES_FILE.write_text(json.dumps({"courses": []}, indent=2))


def load_courses():
    """Load list of courses from courses.json."""
    if not COURSES_FILE.exists():
        return []
    try:
        data = json.loads(COURSES_FILE.read_text())
        return data.get("courses", [])
    except json.JSONDecodeError:
        return []


def save_courses(courses):
    """Save list of courses to courses.json."""
    COURSES_FILE.write_text(json.dumps({"courses": courses}, indent=2))


def create_course(course_name: str):
    """Create a new course with a unique id."""
    courses = load_courses()
    # Simple id scheme: course_1, course_2, ...
    existing_ids = [c["id"] for c in courses]
    new_index = len(existing_ids) + 1
    new_id = f"course_{new_index}"

    new_course = {"id": new_id, "name": course_name}
    courses.append(new_course)
    save_courses(courses)

    # Create course directory + meta
    course_dir = COURSES_DIR / new_id
    course_dir.mkdir(parents=True, exist_ok=True)
    meta_path = course_dir / "meta.json"
    if not meta_path.exists():
        meta = {"id": new_id, "name": course_name, "files": []}
        meta_path.write_text(json.dumps(meta, indent=2))

    return new_course


def get_course_by_name(course_name: str):
    """Find a course dict by name."""
    for c in load_courses():
        if c["name"] == course_name:
            return c
    return None


def get_course_by_id(course_id: str):
    """Find a course dict by id."""
    for c in load_courses():
        if c["id"] == course_id:
            return c
    return None


def delete_course(course_id: str):
    """Delete a course from courses.json and remove its directory from disk."""
    courses = load_courses()
    # Remove this course from the list
    courses = [c for c in courses if c["id"] != course_id]
    save_courses(courses)

    # Remove course directory (uploads + meta)
    course_dir = get_course_dir(course_id)
    if course_dir.exists():
        shutil.rmtree(course_dir)


def get_course_dir(course_id: str) -> Path:
    return COURSES_DIR / course_id


def get_course_meta_path(course_id: str) -> Path:
    return get_course_dir(course_id) / "meta.json"


def load_course_meta(course_id: str):
    """Load meta.json for a course (name + files)."""
    meta_path = get_course_meta_path(course_id)
    if not meta_path.exists():
        # Try to reconstruct a basic meta
        course = get_course_by_id(course_id) or {"id": course_id, "name": "Unknown Course"}
        meta = {"id": course_id, "name": course.get("name", "Unknown Course"), "files": []}
        meta_path.write_text(json.dumps(meta, indent=2))
        return meta

    try:
        return json.loads(meta_path.read_text())
    except json.JSONDecodeError:
        return {"id": course_id, "name": "Unknown Course", "files": []}


def save_course_meta(course_id: str, meta: dict):
    """Save meta.json for a course."""
    meta_path = get_course_meta_path(course_id)
    meta_path.write_text(json.dumps(meta, indent=2))


def make_unique_filename(folder: Path, original_name: str) -> str:
    """
    If a file with original_name exists in folder, append a counter.
    e.g., Lecture1.pdf -> Lecture1_1.pdf, Lecture1_2.pdf, etc.
    """
    base = Path(original_name).stem
    ext = Path(original_name).suffix
    candidate = original_name
    counter = 1
    while (folder / candidate).exists():
        candidate = f"{base}_{counter}{ext}"
        counter += 1
    return candidate


# -----------------------------------------
# Streamlit UI
# -----------------------------------------

ensure_data_dirs()

st.set_page_config(
    page_title="StudyPilot",
    page_icon="🎓",
    layout="wide",
)

st.title("StudyPilot 🎓")
st.write(
    "An AI-powered study companion that turns your course materials into a study plan, flashcards, quizzes, cheat sheets, and a Q&A chat."
)

# -------------------------
# Sidebar: Course management
# -------------------------
st.sidebar.header("Course Selection & Management")

courses = load_courses()
course_names = [c["name"] for c in courses]

# Section to create a new course
st.sidebar.subheader("Create a new course")
new_course_name = st.sidebar.text_input("New course name", value="")

if st.sidebar.button("Add Course"):
    if new_course_name.strip() == "":
        st.sidebar.error("Please enter a course name before adding.")
    else:
        existing = get_course_by_name(new_course_name.strip())
        if existing:
            st.sidebar.warning("A course with that name already exists.")
        else:
            created = create_course(new_course_name.strip())
            st.sidebar.success(f"Course '{created['name']}' created.")
            # Rerun to refresh the sidebar list
            st.rerun()

# Course selection
st.sidebar.subheader("Select a course")
if courses:
    selected_course_name = st.sidebar.selectbox(
        "Current course:",
        ["-- Select a course --"] + course_names,
        index=0,
    )
else:
    selected_course_name = st.sidebar.selectbox(
        "Current course:",
        ["No courses available"],
        index=0,
    )

selected_course = None
if courses and selected_course_name != "-- Select a course --":
    selected_course = get_course_by_name(selected_course_name)

if selected_course:
    st.sidebar.info(f"Selected course: **{selected_course['name']}**")

    # Delete course button
    if st.sidebar.button("Delete selected course"):
        delete_course(selected_course["id"])
        st.sidebar.success(f"Deleted course: {selected_course['name']}")
        st.rerun()
else:
    st.sidebar.info("No course selected yet. Create and select a course to enable uploads and features.")

# -------------------------
# Main tabs
# -------------------------
tabs = st.tabs(
    [
        "📂 Course Materials",
        "🗓️ Study Planner",
        "🃏 Flashcards",
        "📝 Quizzes",
        "📄 Cheat Sheets",
        "💬 Q&A Chat",
    ]
)

# 1) Course Materials tab
with tabs[0]:
    st.header("Course Materials")

    if not selected_course:
        st.warning("Please create and select a course in the sidebar to manage materials.")
    else:
        st.subheader(f"Files for: {selected_course['name']}")

        course_id = selected_course["id"]
        course_dir = get_course_dir(course_id)
        uploads_dir = course_dir / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)

        # File uploader
        st.write("Upload lecture slides, notes, PDFs, or other course files here.")
        uploaded_files = st.file_uploader(
            "Upload one or more files",
            accept_multiple_files=True,
        )

        if uploaded_files:
            meta = load_course_meta(course_id)
            existing_files = meta.get("files", [])

            for uploaded in uploaded_files:
                stored_name = make_unique_filename(uploads_dir, uploaded.name)
                file_path = uploads_dir / stored_name

                # Save file to disk
                with open(file_path, "wb") as f:
                    f.write(uploaded.getbuffer())

                file_record = {
                    "original_name": uploaded.name,
                    "stored_name": stored_name,
                    "uploaded_at": datetime.now().isoformat(timespec="seconds"),
                    "size_bytes": len(uploaded.getbuffer()),
                }
                existing_files.append(file_record)

            meta["files"] = existing_files
            save_course_meta(course_id, meta)
            st.success(f"Uploaded {len(uploaded_files)} file(s) successfully.")
            st.rerun()

        # List existing files
        meta = load_course_meta(course_id)
        files = meta.get("files", [])

        if not files:
            st.info("No files uploaded yet for this course.")
        else:
            st.write("### Uploaded Files")

            for i, f_info in enumerate(files):
                cols = st.columns([4, 2, 2, 1])
                cols[0].write(f"**{f_info['original_name']}**")
                cols[1].write(f_info["uploaded_at"])
                size_kb = f_info["size_bytes"] / 1024
                cols[2].write(f"{size_kb:.1f} KB")

                delete_button = cols[3].button(
                    "🗑️",
                    key=f"delete_{course_id}_{i}",
                    help="Delete this file",
                )

                if delete_button:
                    # Delete file from disk
                    file_path = uploads_dir / f_info["stored_name"]
                    if file_path.exists():
                        os.remove(file_path)

                    # Remove from meta
                    new_files = [ff for j, ff in enumerate(files) if j != i]
                    meta["files"] = new_files
                    save_course_meta(course_id, meta)
                    st.success(f"Deleted file: {f_info['original_name']}")
                    st.rerun()

        st.info(
            "These uploaded files will be used later by the Study Planner, Flashcard Generator, Quiz Generator, "
            "Cheat Sheet Generator, and Q&A Chat."
        )

# 2) Study Planner tab
with tabs[1]:
    st.header("AI Study Schedule Planner")
    st.write(
        "This tab will generate a personalized exam study plan based on your course materials and exam date."
    )
    if not selected_course:
        st.warning("Please create and select a course in the sidebar first.")
    else:
        st.info(
            f"Study planner for course: **{selected_course['name']}** (logic to be implemented in the next steps)."
        )

# 3) Flashcards tab
with tabs[2]:
    st.header("AI Flashcard Generator")
    st.write(
        "This tab will create term/definition flashcards from your uploaded lecture slides, notes, and visuals."
    )
    if not selected_course:
        st.warning("Please create and select a course in the sidebar first.")
    else:
        st.info(
            f"Flashcard generation for course: **{selected_course['name']}** will be implemented in a later step."
        )

# 4) Quizzes tab
with tabs[3]:
    st.header("AI Quiz Generator")
    st.write(
        "This tab will generate multiple-choice and true/false quizzes from your course content."
    )
    if not selected_course:
        st.warning("Please create and select a course in the sidebar first.")
    else:
        st.info(
            f"Quiz generation for course: **{selected_course['name']}** will be implemented in a later step."
        )

# 5) Cheat Sheets tab
with tabs[4]:
    st.header("AI Cheat Sheet Generator")
    st.write(
        "This tab will build compact cheat sheets (3×5 card, 1 page, or 2-sided) from your key formulas and definitions."
    )
    if not selected_course:
        st.warning("Please create and select a course in the sidebar first.")
    else:
        st.info(
            f"Cheat sheet generation for course: **{selected_course['name']}** will be implemented in a later step."
        )

# 6) Q&A Chat tab
with tabs[5]:
    st.header("Course Q&A Chat")
    st.write(
        "This tab will let you ask questions about your course and get answers grounded in your uploaded materials."
    )
    if not selected_course:
        st.warning("Please create and select a course in the sidebar first.")
    else:
        st.info(
            f"Q&A chat for course: **{selected_course['name']}** will be implemented in a later step."
        )
