import streamlit as st
from main import load_config, run_pipeline, run_query

st.set_page_config(page_title="RAG Document Chat", page_icon="💬", layout="wide")

st.title("RAG Document Chat")
st.write(
    "Ask questions directly against your indexed documents. "
    "The RAG engine is loaded directly from main.py without FastAPI."
)

# Initialize session state for pipeline and index
if "index" not in st.session_state:
    with st.spinner("Loading RAG pipeline... (this may take a moment)"):
        try:
            st.session_state.config = load_config()
            st.session_state.index = run_pipeline(st.session_state.config)
            st.session_state.pipeline_ready = True
            st.success("Pipeline loaded successfully!")
        except Exception as exc:
            st.error(f"Failed to load pipeline: {exc}")
            st.session_state.pipeline_ready = False

if st.session_state.get("pipeline_ready", False):
    st.sidebar.markdown("**Pipeline Configuration**")
    st.sidebar.write(f"Source: `{st.session_state.config['source']['type']}`")
    st.sidebar.write(f"Chunking: `{st.session_state.config['chunking'].get('strategy', 'sentence')}`")
    st.sidebar.write(f"Embedding: `{st.session_state.config['embedding']['provider']}`")
    st.sidebar.write(f"Query Mode: `{st.session_state.config.get('query_mode', {}).get('strategy', 'hybrid')}`")

    question = st.text_area(
        "Your Question",
        height=150,
        placeholder="Ask a question about the documents...",
        key="user_question"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        submit_btn = st.button("🔍 Send Query", use_container_width=True)

    if submit_btn:
        if not question.strip():
            st.warning("Please enter a question before sending.")
        else:
            try:
                with st.spinner("Processing query..."):
                    result = run_query(
                        question.strip(),
                        st.session_state.index,
                        st.session_state.config
                    )
                    st.session_state.query_result = result
            except Exception as exc:
                st.error(f"Query failed: {exc}")
                st.session_state.query_result = None

    # Display result from session state (persists across reruns)
    if st.session_state.get("query_result"):
        result = st.session_state.query_result
        st.markdown("---")
        st.markdown("### 📄 Answer")
        st.write(result.answer)

        with st.expander("📊 Metadata & Details"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Strategy", result.strategy)
            with col2:
                st.metric("Format", result.output_format)
            with col3:
                st.metric("Confidence", "High" if result.answer else "N/A")

            if result.rendered and result.output_format != "text":
                st.subheader(f"Rendered ({result.output_format.upper()})")
                st.write(result.rendered)
else:
    st.error("Pipeline not ready. Please check the error above.")
