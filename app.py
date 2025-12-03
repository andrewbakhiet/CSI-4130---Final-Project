import streamlit as st
import os
import json
import shutil
from pathlib import Path
from datetime import datetime, date, timedelta

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from pptx import Presentation


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


# Load environment variables and set up OpenAI
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


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
    courses = [c for c in courses if c["id"] != course_id]
    save_courses(courses)

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


def extract_text_from_file(file_path: Path) -> str:
    """
    Extract plain text from a course file.
    Currently supports: PDF (.pdf), PowerPoint (.pptx/.ppt), and text files (.txt/.md).
    """
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".pdf":
            reader = PdfReader(str(file_path))
            texts = []
            for page in reader.pages:
                content = page.extract_text() or ""
                texts.append(content)
            return "\n\n".join(texts)

        elif suffix in [".pptx", ".ppt"]:
            prs = Presentation(str(file_path))
            texts = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        texts.append(shape.text)
            return "\n\n".join(texts)

        elif suffix in [".txt", ".md"]:
            return file_path.read_text(errors="ignore")

        else:
            # Unsupported type for now
            return ""
    except Exception:
        # If anything goes wrong parsing a file, just skip its content
        return ""


def generate_flashcards_from_text(text: str, num_cards: int = 20) -> list[dict]:
    """
    Call the OpenAI API to generate term/definition flashcards from the given text.
    Returns a list of dicts: [{"front": "...", "back": "..."}, ...]
    """
    if not client:
        raise RuntimeError("OpenAI client is not configured. Missing OPENAI_API_KEY.")

    # Keep the prompt reasonably sized
    MAX_CHARS = 12000
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    prompt = f"""
You are an assistant that creates concise, high-quality term/definition flashcards to help a student study.

Given the course material below, generate up to {num_cards} of the most important flashcards.
Each flashcard must follow this schema:

[
  {{
    "front": "Short term or question",
    "back": "Clear, student-friendly definition or explanation"
  }},
  ...
]

Rules:
- Focus on key concepts, definitions, formulas, and important distinctions.
- Avoid trivial details.
- The 'front' should be short, like a term or a brief question.
- The 'back' should be 1–4 sentences, clear and precise.
- Respond with ONLY valid JSON (a list of objects), no extra text.

COURSE MATERIAL START
{text}
COURSE MATERIAL END
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You generate helpful, accurate term/definition flashcards for students.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content

    # Try to parse the JSON directly
    try:
        cards = json.loads(content)
    except json.JSONDecodeError:
        # Try to recover by extracting the JSON array substring
        start = content.find("[")
        end = content.rfind("]")
        if start != -1 and end != -1 and start < end:
            cards = json.loads(content[start : end + 1])
        else:
            raise

    cleaned_cards = []
    for c in cards:
        if isinstance(c, dict):
            front = (c.get("front") or c.get("term") or "").strip()
            back = (c.get("back") or c.get("definition") or "").strip()
            if front and back:
                cleaned_cards.append({"front": front, "back": back})

    return cleaned_cards


# -----------------------------------------
# Streamlit UI setup
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

# -----------------------------------------
# Sidebar state for course name input
# -----------------------------------------

if "course_name_input_version" not in st.session_state:
    st.session_state["course_name_input_version"] = 0

if "reset_course_name" not in st.session_state:
    st.session_state["reset_course_name"] = False

# If we requested a reset last run, bump the version so the widget key changes
if st.session_state["reset_course_name"]:
    st.session_state["course_name_input_version"] += 1
    st.session_state["reset_course_name"] = False

course_name_input_key = f"new_course_name_{st.session_state['course_name_input_version']}"

# -------------------------
# Sidebar: Course management
# -------------------------
st.sidebar.header("Course Selection & Management")

courses = load_courses()
course_names = [c["name"] for c in courses]

# Section to create a new course
st.sidebar.subheader("Create a new course")

new_course_name = st.sidebar.text_input(
    "New course name",
    key=course_name_input_key,
)

if st.sidebar.button("Add Course"):
    name = new_course_name.strip()
    if name == "":
        st.sidebar.error("Please enter a course name before adding.")
    else:
        existing = get_course_by_name(name)
        if existing:
            st.sidebar.warning("A course with that name already exists.")
        else:
            created = create_course(name)
            st.sidebar.success(f"Course '{created['name']}' created.")
            # Request the input to be cleared on next rerun
            st.session_state["reset_course_name"] = True
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

        # -------------------------
        # Uploader state per course
        # -------------------------
        uploader_version_key = f"uploader_version_{course_id}"
        reset_uploader_flag_key = f"reset_uploader_{course_id}"

        if uploader_version_key not in st.session_state:
            st.session_state[uploader_version_key] = 0
        if reset_uploader_flag_key not in st.session_state:
            st.session_state[reset_uploader_flag_key] = False

        # If requested, bump version so uploader gets a new key and clears its files
        if st.session_state[reset_uploader_flag_key]:
            st.session_state[uploader_version_key] += 1
            st.session_state[reset_uploader_flag_key] = False

        uploader_key = f"uploader_{course_id}_{st.session_state[uploader_version_key]}"

        st.write("Upload lecture slides, notes, PDFs, or other course files here.")

        uploaded_files = st.file_uploader(
            "Choose files to upload",
            accept_multiple_files=True,
            key=uploader_key,
        )

        # Automatically process new uploads once, then clear uploader via version bump
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

            # Clear the uploader selection on next run
            st.session_state[reset_uploader_flag_key] = True
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

                    # Also clear the uploader selection so you don't have to click X
                    st.session_state[reset_uploader_flag_key] = True
                    st.rerun()

        st.info(
            "These uploaded files will be used later by the Study Planner, Flashcard Generator, Quiz Generator, "
            "Cheat Sheet Generator, and Q&A Chat."
        )

# 2) Study Planner tab
with tabs[1]:
    st.header("AI Study Schedule Planner")
    st.write(
        "Generate a high-level study schedule for a specific exam using the files you've uploaded for this course."
    )

    if not selected_course:
        st.warning("Please create and select a course in the sidebar first.")
    else:
        st.subheader(f"Study planner for: {selected_course['name']}")

        # Load files for this course
        course_id = selected_course["id"]
        meta = load_course_meta(course_id)
        files = meta.get("files", [])

        if not files:
            st.info(
                "No files uploaded yet for this course. "
                "Upload lecture slides or notes in the Course Materials tab first."
            )
        else:
            # Inputs for exam and dates
            col1, col2 = st.columns(2)
            with col1:
                exam_name = st.text_input("Exam name", value="Midterm 1")
                start_date = st.date_input(
                    "Start studying on",
                    value=date.today(),
                    help="This is the first day you plan to start studying for this exam.",
                )
            with col2:
                exam_date = st.date_input(
                    "Exam date",
                    value=date.today(),
                    help="You will study up to the day before this date.",
                )
                hours_per_day = st.slider(
                    "Target study hours per day for this course",
                    min_value=1.0,
                    max_value=8.0,
                    value=2.0,
                    step=0.5,
                )

            if exam_date <= start_date:
                st.error("The exam date must be after the study start date.")
            else:
                num_days = (exam_date - start_date).days  # we study up to exam_date - 1

                st.write(
                    f"Study window: **{start_date}** to **{exam_date}** "
                    f"(you have **{num_days}** day(s) to study before the exam)."
                )

                if st.button("Generate study plan"):
                    total_weight = sum(f["size_bytes"] for f in files)
                    if total_weight <= 0:
                        st.error("Unable to compute workload from files. Please re-upload or add files.")
                    else:
                        # Assign continuous date ranges to each file based on size
                        plan_rows = []
                        day_index = 0
                        num_files = len(files)

                        for idx, f_info in enumerate(files):
                            weight = f_info["size_bytes"]
                            share = weight / total_weight

                            # Approximate number of days for this file
                            days_remaining = num_days - day_index
                            if days_remaining <= 0:
                                file_days = 0
                            elif idx == num_files - 1:
                                # Last file gets all remaining days
                                file_days = days_remaining
                            else:
                                file_days = max(1, min(days_remaining, round(share * num_days)))

                            if file_days > 0:
                                start_d = start_date + timedelta(days=day_index)
                                end_d = start_date + timedelta(days=day_index + file_days - 1)

                                est_total_hours = share * num_days * hours_per_day

                                plan_rows.append(
                                    {
                                        "File": f_info["original_name"],
                                        "Suggested start date": str(start_d),
                                        "Suggested end date": str(end_d),
                                        "Estimated total hours": round(est_total_hours, 1),
                                    }
                                )

                                day_index += file_days

                        # If rounding left some unused days, extend the last file to the final day
                        if plan_rows and day_index < num_days:
                            last = plan_rows[-1]
                            last["Suggested end date"] = str(start_date + timedelta(days=num_days - 1))

                        st.subheader(f"File-level plan for: {exam_name}")
                        st.write(
                            "This table shows how the planner allocates your uploaded files across the available study days "
                            "based on their relative size."
                        )
                        if plan_rows:
                            st.table(plan_rows)
                        else:
                            st.info("No days available to schedule. Check your dates.")

                        # Build a simple day-by-day view
                        st.subheader("Day-by-day study schedule")
                        daily_rows = []
                        for offset in range(num_days):
                            day = start_date + timedelta(days=offset)
                            files_for_day = [
                                row["File"]
                                for row in plan_rows
                                if date.fromisoformat(row["Suggested start date"])
                                <= day
                                <= date.fromisoformat(row["Suggested end date"])
                            ]
                            daily_rows.append(
                                {
                                    "Date": str(day),
                                    "Planned study focus": ", ".join(files_for_day) if files_for_day else "—",
                                    "Suggested hours": hours_per_day if files_for_day else 0.0,
                                }
                            )

                        if daily_rows:
                            st.table(daily_rows)
                        else:
                            st.info("No schedule could be generated. Check your dates and files.")


# 3) Flashcards tab
with tabs[2]:
    st.header("AI Flashcard Generator")
    st.write(
        "Generate term/definition flashcards from your uploaded lecture slides and notes."
    )

    if not selected_course:
        st.warning("Please create and select a course in the sidebar first.")
    else:
        if client is None:
            st.error(
                "OpenAI API key not found. Please set OPENAI_API_KEY in a .env file "
                "before using the flashcard generator."
            )
        else:
            course_id = selected_course["id"]
            meta = load_course_meta(course_id)
            files = meta.get("files", [])

            if not files:
                st.info(
                    "No files uploaded yet for this course. "
                    "Upload lecture slides or notes in the Course Materials tab first."
                )
            else:
                st.subheader(f"Generate flashcards for: {selected_course['name']}")

                # Choose which files to include
                uploads_dir = get_course_dir(course_id) / "uploads"
                name_to_file = {f["original_name"]: f for f in files}

                default_selection = list(name_to_file.keys())
                selected_file_names = st.multiselect(
                    "Select files to include in this flashcard set",
                    options=list(name_to_file.keys()),
                    default=default_selection,
                )

                if not selected_file_names:
                    st.warning("Please select at least one file to generate flashcards from.")
                else:
                    num_cards = st.slider(
                        "Maximum number of flashcards",
                        min_value=5,
                        max_value=40,
                        value=20,
                        step=5,
                    )

                    set_name = st.text_input(
                        "Flashcard set name",
                        value="Default set",
                        help="This name is just for display in this session.",
                    )

                    if st.button("Generate flashcards"):
                        # Aggregate text from selected files
                        all_text_parts = []
                        for fname in selected_file_names:
                            f_info = name_to_file[fname]
                            file_path = uploads_dir / f_info["stored_name"]
                            extracted = extract_text_from_file(file_path)
                            if extracted:
                                all_text_parts.append(extracted)

                        combined_text = "\n\n".join(all_text_parts).strip()

                        if not combined_text:
                            st.error(
                                "Could not extract text from the selected files. "
                                "Try different files or formats (PDF, PPTX, TXT)."
                            )
                        else:
                            with st.spinner("Generating flashcards with AI..."):
                                try:
                                    cards = generate_flashcards_from_text(combined_text, num_cards=num_cards)
                                except Exception as e:
                                    st.error(f"Error generating flashcards: {e}")
                                else:
                                    if not cards:
                                        st.warning(
                                            "The AI did not return any valid flashcards. "
                                            "Try reducing the number of files or simplifying the content."
                                        )
                                    else:
                                        # Store in session so they persist while app is running
                                        state_key = f"flashcards_{course_id}"
                                        st.session_state[state_key] = {
                                            "set_name": set_name,
                                            "cards": cards,
                                        }
                                        st.success(
                                            f"Generated {len(cards)} flashcard(s) for set: {set_name}"
                                        )

            # Show flashcards if we have a generated set in this session
            state_key = f"flashcards_{selected_course['id']}" if selected_course else None
            if state_key and state_key in st.session_state:
                flash_state = st.session_state[state_key]
                st.subheader(f"Flashcard set: {flash_state['set_name']}")
                st.write(
                    "Click each card to view the back. You can regenerate a new set at any time."
                )

                for idx, card in enumerate(flash_state["cards"], start=1):
                    with st.expander(f"Card {idx}: {card['front']}"):
                        st.write(card["back"])


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
