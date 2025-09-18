import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from training_agent import TrainingAI


def extract_workouts_from_plan(plan_text):
    """Extracts individual workouts from the plan text"""
    # Basic implementation - may need adjustment based on your plan format
    workouts = []
    current_workout = {}

    for line in plan_text.split('\n'):
        if "Day" in line and ":" in line:
            if current_workout:
                workouts.append(current_workout)
            current_workout = {"original_text": line}
        elif current_workout:
            current_workout["details"] = current_workout.get("details", "") + line + "\n"

    if current_workout:
        workouts.append(current_workout)

    return workouts


def adjust_workout(original_workout, feedback):
    """Adjusts a specific workout based on feedback"""
    adjusted_workout = original_workout.copy()

    # Adjust intensity
    if feedback["tipo"] == "Too intense":
        # Reduce intensity
        adjusted_workout["details"] = adjusted_workout["details"].replace(
            "fast pace", "moderate pace"
        ).replace(
            "high intensity", "moderate intensity"
        )
    elif feedback["tipo"] == "Too light":
        # Increase intensity
        adjusted_workout["details"] = adjusted_workout["details"].replace(
            "easy pace", "moderate pace"
        ).replace(
            "low intensity", "moderate intensity"
        )

    # Apply preferences
    for pref in feedback["preferencias"]:
        if pref == "Shorter workouts":
            # Reduce volume by 20%
            adjusted_workout["details"] = adjusted_workout["details"].replace(
                "km", lambda x: f"{float(x.group(0).replace('km', '')) * 0.8:.1f}km"
            )
        # Add more adjustments based on preferences

    return adjusted_workout

def main():
    if 'plano_original' not in st.session_state:
        st.session_state.plano_original = None
    if 'plano_atual' not in st.session_state:
        st.session_state.plano_atual = None
    if 'versao_plano' not in st.session_state:
        st.session_state.versao_plano = 1


    st.set_page_config(
        page_title="Training Assistant",
        page_icon="🏃‍♂️",
        layout="wide"
    )

    st.title("🏃‍♂️ Personalized Training Assistant")


    # Main interface - simplified
    with st.form("training_plan"):
        st.header("🎯 Define Your Goal")

        goal = st.text_input(
            "What is your goal?",
            value="Prepare for a half marathon"
        )

        col1, col2 = st.columns(2)
        with col1:
            level = st.selectbox(
                "Your current level:",
                ["Beginner", "Intermediate", "Advanced"],
                index=1
            )
        with col2:
            training_days = st.slider(
                "Available days per week:",
                min_value=2,
                max_value=7,
                value=4
            )

        generate_plan = st.form_submit_button("Generate Plan")


    if generate_plan:
        with st.spinner("🤖 Generating your initial plan..."):
            try:
                # Create the training agent
                coach = TrainingAI()

                # Generate the plan (TrainingAI already fetches Garmin data)
                plan = coach.gerar_plano(
                    None,  # No need to pass data, TrainingAI fetches it
                    goal,
                    level,
                    training_days
                )

                if plan:
                    st.session_state.original_plan = plan
                    st.session_state.current_plan = plan
                    st.session_state.plan_version = 1
                    st.markdown(plan)
                    st.success("✅ Plan generated successfully!")
                else:
                    st.error("❌ Error generating plan")

            except Exception as e:
                st.error(f"❌ Error generating plan: {str(e)}")

    # Feedback section (only appears if a plan exists)
    if st.session_state.get("current_plan"):
        st.header(f"📝 Plan Feedback (Version {st.session_state.get('plan_version', 1)})")

        # Button to restore original version
        if st.session_state.get("plan_version", 1) > 1:
            if st.button("↩️ Restore Original Plan"):
                st.session_state.current_plan = st.session_state.original_plan
                st.session_state.plan_version = 1
                st.rerun()

        col1, col2 = st.columns(2)

        with col1:
            feedback_type = st.selectbox(
                "Type of adjustment needed:",
                ["Too intense", "Too light", "Adjust distances", "Adjust paces", "Other"]
            )

            feedback_level = st.slider(
                "Impact level of adjustment:",
                min_value=1, max_value=5, value=3,
                help="1 = subtle adjustment, 5 = significant change"
            )

        with col2:
            feedback_preferences = st.multiselect(
                "Training preferences:",
                ["Shorter workouts", "Longer workouts", "More intervals",
                 "More base runs", "Include hills", "Avoid hills"]
            )

        feedback_details = st.text_area(
            "Feedback details:",
            placeholder="Describe what needs to be adjusted..."
        )

        if st.button("Adjust Current Plan"):
            with st.spinner("🤖 Adjusting your plan..."):
                try:
                    # Extract workouts from the current plan
                    workouts = extract_workouts_from_plan(st.session_state.current_plan)

                    # Prepare feedback
                    feedback = {
                        "tipo": feedback_type,
                        "nivel": feedback_level,
                        "detalhes": feedback_details,
                        "preferencias": feedback_preferences
                    }

                    # Adjust each workout
                    adjusted_workouts = [
                        adjust_workout(workout, feedback)
                        for workout in workouts
                    ]

                    # Build the new plan
                    adjusted_plan = st.session_state.current_plan
                    for original, adjusted in zip(workouts, adjusted_workouts):
                        adjusted_plan = adjusted_plan.replace(
                            original["original_text"] + original.get("details", ""),
                            adjusted["original_text"] + adjusted.get("details", "")
                        )

                    # Update the plan
                    st.session_state.current_plan = adjusted_plan
                    st.session_state.plan_version += 1

                    st.markdown(adjusted_plan)
                    st.success(f"✅ Plan successfully adjusted! (Version {st.session_state.plan_version})")

                except Exception as e:
                    st.error(f"❌ Error adjusting plan: {str(e)}")

if __name__ == "__main__":
    main()