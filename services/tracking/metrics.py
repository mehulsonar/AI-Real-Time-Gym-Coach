import streamlit as st
import time
from services.config.workout_config import METRICS_FIELDS
from services.persistence.exercise_repository import add_exercise


def sync_metrics_update(context):
    # Validate context
    if not context:
        return
    if not hasattr(context, "state"):
        return
    if not context.state.playing:
        return
    
    processor = getattr(context, "video_processor", None)
    if not processor:
        return 
    
    # Get exercise type
    exercise = st.session_state.get("exercise_type") or st.session_state.get("plan_exercise")
    if not exercise:
        return
    
    # Set exercise and get latest metrics
    processor.set_exercise(exercise)
    latest_metrics = processor.get_latest_metrics()

    if not latest_metrics:
        return
    
    # CRITICAL: Update reps from detector - this is the primary counter
    # This should update EVERY frame when a rep is completed
    if "reps" in latest_metrics and latest_metrics["reps"] is not None:
        new_reps = int(latest_metrics["reps"])
        current_reps = int(st.session_state.get("reps") or 0)
        
        # Only update if there's a change (new rep detected)
        if new_reps != current_reps:
            st.session_state.reps = new_reps
    else:
        # Fallback: ensure reps exists in session state
        if "reps" not in st.session_state:
            st.session_state.reps = 0

    # Update exercise-specific metric fields
    fields = METRICS_FIELDS.get(exercise)
    if fields:
        for key, default in fields.items():
            if key in latest_metrics:
                st.session_state[key] = latest_metrics[key]
            elif key not in st.session_state:
                st.session_state[key] = default

    # Get workout parameters
    reps = int(st.session_state.get("reps") or 0)
    reps_per_set = int(st.session_state.get("reps_per_set") or 0)
    target_sets = int(st.session_state.get("target_sets") or 0)

    # Calculate sets and current set reps - MUST ALWAYS UPDATE
    if reps_per_set > 0 and target_sets > 0:
        sets_completed = reps // reps_per_set
        current_set_reps = reps % reps_per_set
        
        # Cap sets_completed at target_sets
        if sets_completed > target_sets:
            sets_completed = target_sets
            current_set_reps = reps_per_set
        
        workout_complete = sets_completed >= target_sets
    elif reps_per_set > 0:
        sets_completed = reps // reps_per_set
        current_set_reps = reps % reps_per_set
        workout_complete = False
    else:
        sets_completed = 0
        current_set_reps = 0 if reps == 0 else reps
        workout_complete = False

    # Update session state with calculated values - ALWAYS
    st.session_state.sets_completed = sets_completed
    st.session_state.current_set_reps = current_set_reps
    st.session_state.workout_complete = workout_complete

    last_saved_sets = st.session_state.get("last_saved_sets_completed", 0)

    if target_sets > 0 and reps_per_set > 0 and sets_completed > last_saved_sets:
        newly_completed = sets_completed - last_saved_sets
        now_ts = time.time()
        started_at = st.session_state.get("set_cycle_started_at", now_ts)
        time_taken = now_ts - started_at
        user_id = st.session_state.get("user_id", 0)

        add_exercise(user_id, exercise, newly_completed * reps_per_set, newly_completed, time_taken)

        if st.session_state.get("voice_pipeline"):
            result = st.session_state.voice_pipeline.process_event(
                event="set_completed",
                exercise=exercise,
                metrics=latest_metrics,
            )

            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result

        st.session_state.set_cycle_started_at = now_ts
        st.session_state.last_saved_sets_completed = sets_completed

    if workout_complete and not st.session_state.get("last_notified_workout_complete", False):
        st.session_state.last_notified_workout_complete = True

        if st.session_state.get("voice_pipeline"):
            result = st.session_state.voice_pipeline.process_event(
                event="workout_completed",
                exercise=exercise,
                metrics=latest_metrics,
            )

            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result
                
    pose_detected = latest_metrics.get("pose_detected", True)
    
    if not pose_detected and st.session_state.get("voice_pipeline"):
        result = st.session_state.voice_pipeline.process_event(
            event="no_pose_detected",
            exercise=exercise,
            metrics={"issue": "No pose detected! Please step into the camera frame."},
        )
    
        if result:
            st.session_state.audio_to_play, st.session_state.coach_feedback = result

    if st.session_state.get("voice_pipeline"):
        result = st.session_state.voice_pipeline.process_event(
            event="ongoing_form_check",
            exercise=exercise,
            metrics=latest_metrics,
        )
        
        if result:
            st.session_state.audio_to_play, st.session_state.coach_feedback = result
