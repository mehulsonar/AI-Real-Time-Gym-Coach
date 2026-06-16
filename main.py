import streamlit as st 
import os
import time
from services.auth.login_wall import login_form
from services.state.session_defaults import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS
from services.ui.style_loader import load_css, inject_local_font, inject_webrtc_styles
from services.persistence.exercise_repository import init_db
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update


def main():
    st.set_page_config(
            page_icon="🏋️‍♀️",
            page_title="AI Real-time GYM Coach",
            initial_sidebar_state="expanded",
            layout="centered"
        )
    
    load_css(os.path.join(os.getcwd(), "static", "style.css"))
    inject_local_font(os.path.join(os.getcwd(), "static", "AdobeClean.otf"), "AdobeClean")
    
    init_db()

    if not login_form():
        return
    
    initial_session_defaults()

    workout_started = st.session_state.get("workout_started", False)
    
    with st.sidebar:
        st.title("🏋️‍♂️ Apna AI Coach")

        if st.session_state.username:
            st.caption(f"👤 Login as {st.session_state.username}")

        st.divider()

        st.subheader("Workout Plan")

        # Workout plan inputs (always visible so changes take effect immediately)
        st.selectbox("Exercise", options=EXERCISE_OPTIONS, key="plan_exercise")

        st.number_input("Sets", min_value=0, max_value=50, key="plan_sets", step=1)

        st.number_input("Reps per Set", min_value=0, max_value=50, key="plan_reps", step=1)

        st.markdown("")

        if not workout_started:
            start_session_button = st.button("Start Session", width="stretch", key="start_session_button")

            if start_session_button:
                # Set exercise configuration from plan
                st.session_state.exercise_type = st.session_state.plan_exercise
                st.session_state.target_sets = int(st.session_state.plan_sets)
                st.session_state.reps_per_set = int(st.session_state.plan_reps)
                
                # Reset workout metrics
                st.session_state.reps = 0
                st.session_state.current_set_reps = 0
                st.session_state.sets_completed = 0
                st.session_state.workout_complete = False
                st.session_state.last_saved_sets_completed = 0
                st.session_state.last_notified_workout_complete = False
                st.session_state.set_cycle_started_at = time.time()
                
                # Increment session ID to force new video processor
                st.session_state.workout_session_id += 1
                st.session_state["workout_started"] = True
                st.rerun()
        else:
            exercise = st.session_state.get("exercise_type")
            sets = st.session_state.get("target_sets")
            reps = st.session_state.get("reps_per_set")

            st.info(f"**{exercise}** -- {sets} Sets / {reps} Reps")

            end_session_button = st.button("End Session", key="end_session_button", width="stretch")

            if end_session_button:
                st.session_state["workout_started"] = False
                st.rerun()

        if workout_started:
            st.divider()

            exercise = st.session_state.get("exercise_type")
            total_reps = st.session_state.get("reps")
            current_set_reps = st.session_state.get("current_set_reps")
            reps_per_set = st.session_state.get("reps_per_set")
            sets_completed = st.session_state.get("sets_completed")
            target_sets = st.session_state.get("target_sets")

            st.subheader("Progress")

            st.metric("Total Reps", f"{total_reps}")
            st.metric("Current Set Reps", f"{current_set_reps} / {reps_per_set}")
            st.metric("Sets Completed", f"{sets_completed} / {target_sets}")

            st.divider()

            if exercise == "Squats":
                st.subheader("Squat Metrics")
                st.metric("Knee Angle", f"{st.session_state.knee_angle}°")
                st.metric("Back Angle", f"{st.session_state.back_angle}°")
                st.metric("Depth Status", st.session_state.depth_status)

            elif exercise == "Push-ups":
                st.subheader("Push-up Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Body Alignment", st.session_state.body_alignment)
                st.metric("Hip Position", st.session_state.hip_status)

            elif exercise == "Biceps Curls (Dumbbell)":
                st.subheader("Curl Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Shoulder Stability", st.session_state.shoulder_status)
                st.metric("Swing Detection", st.session_state.swing_status)

            elif exercise == "Shoulder Press":
                st.subheader("Shoulder Press Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Arm Extension", st.session_state.extension_status)
                st.metric("Back Arch", st.session_state.back_arch_status)

            elif exercise == "Lunges":
                st.subheader("Lunge Metrics")
                st.metric("Front Knee Angle", f"{st.session_state.front_knee_angle}°")
                st.metric("Torso Angle", f"{st.session_state.torso_angle}°")
                st.metric("Balance Status", st.session_state.balance_status)
    if not workout_started:
        st.header("AI Real-Time GymCoach")
        st.markdown("""
                    <p style="color: grey">Real-time pose detection with productive AI voice coaching</p>
                    <div style="border: 10px groove; text-align: center; margin-top: 2rem; margin-bottom: 4rem">
                        <h2 style="margin-top: 2rem;">👈 Set your workou plan here</h2>
                        <p style="color: grey; margin-bottom: 3rem;">Choose your exercise, sets & reps insithe the sidebar, </br>
                            then click Start Workout to activate the camera and AI coach
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
        
    else:
        context = webrtc_streamer(
            key=f"exercise-analysis-{st.session_state.workout_session_id}",
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=VideoProcessorClass,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={
                "video": True,
                "audio": False
            },
            async_processing=True
        )

        if context.video_processor:
            exercise = st.session_state.get("exercise_type", "Squats")
            context.video_processor.set_exercise(exercise)

        sync_metrics_update(context)

        # Update more frequently for real-time feedback
        if context.state.playing:
            time.sleep(0.1)
            st.rerun()

        inject_webrtc_styles()
        
    st.markdown("### Workout History")

if __name__ == "__main__":
    main()
