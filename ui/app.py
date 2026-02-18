from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from core.semantic_evaluation import evaluate_answer
from srs_engine import SRSEngine


DB_PATH = "srs.db"
DIFFICULTY_OPTIONS = ["all", "beginner", "intermediate", "advanced"]
QUESTION_TYPE_OPTIONS = ["concept", "syntax_writing", "output_prediction"]
STATE_VERSION = 3


def init_state() -> None:
    if st.session_state.get("state_version") != STATE_VERSION:
        for key in [
            "engine",
            "review_item_id",
            "show_answer",
            "answer_input",
            "review_filter",
            "lesson_topic_filter",
            "lesson_difficulty_filter",
            "lesson_show_answer",
            "lesson_item_id",
            "modify_topic_filter",
            "modify_difficulty_filter",
            "modify_qtype_filter",
            "modify_selected_id",
            "clear_answer_input_on_next_run",
        ]:
            st.session_state.pop(key, None)
        st.session_state.state_version = STATE_VERSION
    if "engine" not in st.session_state:
        st.session_state.engine = SRSEngine(DB_PATH)
    if "review_item_id" not in st.session_state:
        st.session_state.review_item_id = None
    if "show_answer" not in st.session_state:
        st.session_state.show_answer = False
    if "answer_input" not in st.session_state:
        st.session_state.answer_input = ""
    if "clear_answer_input_on_next_run" not in st.session_state:
        st.session_state.clear_answer_input_on_next_run = False
    if st.session_state.clear_answer_input_on_next_run:
        # Clear input before the text_area widget is created in this run.
        st.session_state.answer_input = ""
        st.session_state.clear_answer_input_on_next_run = False
    if "review_filter" not in st.session_state:
        st.session_state.review_filter = "all"
    if "lesson_topic_filter" not in st.session_state:
        st.session_state.lesson_topic_filter = "all"
    if "lesson_difficulty_filter" not in st.session_state:
        st.session_state.lesson_difficulty_filter = "all"
    if "lesson_show_answer" not in st.session_state:
        st.session_state.lesson_show_answer = False
    if "lesson_item_id" not in st.session_state:
        st.session_state.lesson_item_id = None
    if "modify_topic_filter" not in st.session_state:
        st.session_state.modify_topic_filter = "all"
    if "modify_difficulty_filter" not in st.session_state:
        st.session_state.modify_difficulty_filter = "all"
    if "modify_qtype_filter" not in st.session_state:
        st.session_state.modify_qtype_filter = "all"
    if "modify_selected_id" not in st.session_state:
        st.session_state.modify_selected_id = None


def reset_review_state() -> None:
    st.session_state.review_item_id = None
    st.session_state.show_answer = False
    st.session_state.clear_answer_input_on_next_run = True


def reset_lesson_state() -> None:
    st.session_state.lesson_show_answer = False
    st.session_state.lesson_item_id = None


def get_or_pick_review_item():
    engine: SRSEngine = st.session_state.engine

    if st.session_state.review_item_id is not None:
        try:
            return engine.get_item(st.session_state.review_item_id)
        except ValueError:
            reset_review_state()

    level_filter = None if st.session_state.review_filter == "all" else st.session_state.review_filter
    due_items = engine.get_due_items(now=datetime.now(timezone.utc), difficulty_level=level_filter)
    if not due_items:
        return None

    item = due_items[0]
    st.session_state.review_item_id = item.id
    return item


def render_home_page() -> None:
    engine: SRSEngine = st.session_state.engine
    counts = engine.get_home_counts(now=datetime.now(timezone.utc))

    st.title("SQL SRS")
    st.caption("SQL learning from beginner to advanced with spaced repetition.")
    st.metric("Reviews Due", counts["total_due"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Beginner Due", counts["beginner_due"])
    c2.metric("Intermediate Due", counts["intermediate_due"])
    c3.metric("Advanced Due", counts["advanced_due"])

    if counts["total_due"] == 0:
        st.info("No reviews due right now. Add lessons or come back later.")
    else:
        st.success("You have due reviews. Open the Review page.")


def render_review_page() -> None:
    st.title("Review")
    st.selectbox("Difficulty filter", DIFFICULTY_OPTIONS, key="review_filter")

    engine: SRSEngine = st.session_state.engine
    item = get_or_pick_review_item()
    if item is None:
        st.info("No due items for the selected filter.")
        return

    st.subheader(f"Item #{item.id}")
    st.caption(
        "Difficulty: "
        f"{item.difficulty_level} | Type: {display_question_type(item.question_type)} | "
        f"SRS Level: {item.level}"
    )
    st.write(item.question)

    st.text_area(
        "Your SQL answer",
        key="answer_input",
        height=160,
        placeholder="Write your answer here...",
        disabled=st.session_state.show_answer,
    )

    if not st.session_state.show_answer:
        if st.button("Reveal Correct Answer", type="primary"):
            st.session_state.show_answer = True
            st.rerun()
        return

    st.markdown("**Correct answer**")
    st.code(item.answer, language="sql")
    if item.explanation:
        st.markdown("**Explanation**")
        st.write(item.explanation)

    evaluation = evaluate_answer(st.session_state.answer_input, item.answer)
    st.markdown("**Semantic evaluation**")
    st.caption(f"Similarity score: {evaluation['similarity']:.2f}")
    if evaluation["classification"] == "correct":
        st.success(f"Pass: {evaluation['feedback']}")
    elif evaluation["classification"] == "partially_correct":
        st.warning(f"Fail (partial): {evaluation['feedback']}")
    else:
        st.error(f"Fail: {evaluation['feedback']}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Correct", use_container_width=True):
            engine.submit_answer(item.id, item.answer, now=datetime.now(timezone.utc))
            reset_review_state()
            st.rerun()
    with col2:
        if st.button("Incorrect", use_container_width=True):
            engine.submit_answer(item.id, "__INCORRECT__", now=datetime.now(timezone.utc))
            reset_review_state()
            st.rerun()


def render_lessons_page() -> None:
    st.title("Lessons")
    st.caption("Learn SQL topics and move lessons into the review queue.")
    engine: SRSEngine = st.session_state.engine
    progress = engine.get_topic_progress()
    st.markdown("**Topic progress**")
    for row in progress:
        total = int(row["total_items"])
        learned = int(row["learned_items"])
        burned = int(row["burned_items"])
        pct = 0.0 if total == 0 else learned / total
        st.write(f"{row['topic']}: {learned}/{total} learned, {burned} burned")
        st.progress(pct)

    topics = ["all"] + engine.list_topics()
    st.selectbox("Topic filter", topics, key="lesson_topic_filter")
    st.selectbox("Difficulty filter", DIFFICULTY_OPTIONS, key="lesson_difficulty_filter")

    topic_filter = None if st.session_state.lesson_topic_filter == "all" else st.session_state.lesson_topic_filter
    difficulty_filter = (
        None if st.session_state.lesson_difficulty_filter == "all" else st.session_state.lesson_difficulty_filter
    )

    lesson_item = None
    if st.session_state.lesson_item_id is not None:
        try:
            lesson_item = engine.get_item(st.session_state.lesson_item_id)
            if lesson_item.unlocked_at is not None:
                lesson_item = None
                reset_lesson_state()
        except ValueError:
            reset_lesson_state()

    if lesson_item is None:
        lesson_item = engine.get_next_lesson(topic=topic_filter, difficulty_level=difficulty_filter)
        if lesson_item:
            st.session_state.lesson_item_id = lesson_item.id

    if lesson_item is None:
        st.info("No pending lessons for this filter. Go to Review or change filters.")
        return

    st.markdown("**Current lesson**")
    st.caption(
        f"Topic: {lesson_item.topic} | Difficulty: {lesson_item.difficulty_level} | "
        f"Type: {display_question_type(lesson_item.question_type)}"
    )
    st.write(lesson_item.question)

    if not st.session_state.lesson_show_answer:
        if st.button("Reveal Lesson Answer", type="primary"):
            st.session_state.lesson_show_answer = True
            st.rerun()
        return

    st.markdown("**Answer**")
    st.code(lesson_item.answer, language="sql")
    if lesson_item.explanation:
        st.markdown("**Explanation**")
        st.write(lesson_item.explanation)

    if st.button("Mark as Learned and Move to Review", use_container_width=True):
        engine.unlock_lesson(lesson_item.id, now=datetime.now(timezone.utc))
        reset_review_state()
        reset_lesson_state()
        st.success("Lesson moved to review queue.")
        st.rerun()


def run_streamlit_app() -> None:
    st.set_page_config(page_title="SQL SRS", layout="centered")
    init_state()

    page = st.sidebar.radio("Navigate", ["Home", "Review", "Lessons", "Modify Lessons"])
    if page == "Home":
        render_home_page()
    elif page == "Review":
        render_review_page()
    elif page == "Lessons":
        render_lessons_page()
    else:
        render_modify_lessons_page()


def display_question_type(raw: str) -> str:
    mapping = {
        "concept": "concept",
        "syntax": "syntax_writing",
        "syntax_writing": "syntax_writing",
        "output": "output_prediction",
        "output_prediction": "output_prediction",
    }
    return mapping.get(raw, raw)


def render_modify_lessons_page() -> None:
    st.title("Modify Lessons")
    st.caption("Edit existing SQL questions and answers.")
    engine: SRSEngine = st.session_state.engine

    topics = ["all"] + engine.list_topics()
    st.selectbox("Topic filter", topics, key="modify_topic_filter")
    st.selectbox("Difficulty filter", DIFFICULTY_OPTIONS, key="modify_difficulty_filter")
    st.selectbox(
        "Question type filter",
        ["all", "concept", "syntax_writing", "output_prediction"],
        key="modify_qtype_filter",
    )

    topic_filter = None if st.session_state.modify_topic_filter == "all" else st.session_state.modify_topic_filter
    difficulty_filter = (
        None if st.session_state.modify_difficulty_filter == "all" else st.session_state.modify_difficulty_filter
    )
    qtype_filter = None if st.session_state.modify_qtype_filter == "all" else st.session_state.modify_qtype_filter

    items = engine.list_items(
        topic=topic_filter,
        difficulty_level=difficulty_filter,
        question_type=qtype_filter,
        limit=500,
    )
    if not items:
        st.info("No lessons found for selected filters.")
        return

    item_options = {
        f"#{item.id} [{item.difficulty_level}] [{display_question_type(item.question_type)}] {item.question[:80]}": item.id
        for item in items
    }
    labels = list(item_options.keys())
    current_label_index = 0
    if st.session_state.modify_selected_id is not None:
        for idx, lbl in enumerate(labels):
            if item_options[lbl] == st.session_state.modify_selected_id:
                current_label_index = idx
                break

    selected_label = st.selectbox("Select lesson to edit", labels, index=current_label_index)
    selected_id = item_options[selected_label]
    st.session_state.modify_selected_id = selected_id
    item = engine.get_item(selected_id)

    with st.form("modify_lesson_form"):
        new_topic = st.text_input("Topic", value=item.topic)
        new_difficulty = st.selectbox(
            "Difficulty",
            ["beginner", "intermediate", "advanced"],
            index=["beginner", "intermediate", "advanced"].index(item.difficulty_level),
        )
        qtype_values = ["concept", "syntax_writing", "output_prediction"]
        normalized_qtype = display_question_type(item.question_type)
        if normalized_qtype not in qtype_values:
            normalized_qtype = "concept"
        new_qtype = st.selectbox(
            "Question type",
            qtype_values,
            index=qtype_values.index(normalized_qtype),
        )
        new_question = st.text_area("Question", value=item.question, height=150)
        new_answer = st.text_area("Correct answer", value=item.answer, height=150)
        new_explanation = st.text_area("Explanation", value=item.explanation, height=120)
        submitted = st.form_submit_button("Save changes")

        if submitted:
            try:
                engine.update_item_content(
                    item_id=item.id,
                    question=new_question,
                    answer=new_answer,
                    explanation=new_explanation,
                    topic=new_topic,
                    difficulty_level=new_difficulty,
                    question_type=new_qtype,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(f"Saved changes for item #{item.id}.")
                reset_lesson_state()
                reset_review_state()
                st.rerun()
