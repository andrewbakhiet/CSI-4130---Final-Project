import streamlit as st

# -----------------------------------------
# StudyPilot - Minimal Skeleton App
# -----------------------------------------

st.set_page_config(
    page_title="StudyPilot",
    page_icon="🎓",
    layout="wide",
)

st.title("StudyPilot 🎓")
st.write(
    "An AI-powered study companion that turns your course materials into a study plan, flashcards, quizzes, cheat sheets, and a Q&A chat."
)

# Sidebar for course selection (we'll make this functional later)
st.sidebar.header("Course Selection")
selected_course = st.sidebar.selectbox(
    "Choose a course (placeholder for now):",
    ["No course selected (demo)"],
    index=0,
)

st.sidebar.info(
    "In future steps, you'll be able to create courses, upload files, and switch between them here."
)

# Main tabs for the five core features
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
    st.write(
        "Here you'll upload and manage lecture slides, notes, and other course files. "
        "For now, this is just a placeholder area."
    )
    st.info("Next steps: add file upload, list of files, and basic storage.")

# 2) Study Planner tab
with tabs[1]:
    st.header("AI Study Schedule Planner")
    st.write(
        "This tab will generate a personalized exam study plan based on your course materials and exam date."
    )
    st.info("Next steps: add inputs for exam name, exam date, and planner logic.")

# 3) Flashcards tab
with tabs[2]:
    st.header("AI Flashcard Generator")
    st.write(
        "This tab will create term/definition flashcards from your uploaded lecture slides, notes, and visuals."
    )
    st.info("Next steps: add flashcard generation, viewing, starring, and renaming sets.")

# 4) Quizzes tab
with tabs[3]:
    st.header("AI Quiz Generator")
    st.write(
        "This tab will generate multiple-choice and true/false quizzes from your course content."
    )
    st.info("Next steps: add difficulty options, question types, and quiz-taking UI.")

# 5) Cheat Sheets tab
with tabs[4]:
    st.header("AI Cheat Sheet Generator")
    st.write(
        "This tab will build compact cheat sheets (3×5 card, 1 page, or 2-sided) from your key formulas and definitions."
    )
    st.info("Next steps: add size options and focused cheat sheet generation.")

# 6) Q&A Chat tab
with tabs[5]:
    st.header("Course Q&A Chat")
    st.write(
        "This tab will let you ask questions about your course and get answers grounded in your uploaded materials."
    )
    st.info("Next steps: add retrieval over course files and chat interface.")
