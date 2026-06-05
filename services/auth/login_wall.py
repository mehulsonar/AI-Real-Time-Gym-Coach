import streamlit as st 
from services.persistence.exercise_repository import get_or_create_user

def login_form():
    if st.session_state.get("user_id") is not None:
        return True
    
    st.title("🏋️‍♂️ AI Real-time GYM Trainer")
    st.markdown("### Welcome! Please enter a username to start.")

    with st.form("Login Form", clear_on_submit=True, border=True, width="stretch", height="content" ):
        username = st.text_input("Username (Unique)", placeholder="Username e.g. sonarmehul")
        st.divider()
        submit_button = st.form_submit_button("Start Session", width="stretch", type="primary")

    if submit_button:
        if not username:
            st.error("Name is required!")
            return False
        
        user = get_or_create_user(username)
        
        st.session_state["user_id"] = user["id"]
        st.session_state["username"] = user["username"]

        st.rerun()

    return False

