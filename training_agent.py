"""
Personalized Training Assistant Agent

AI-powered running coach that generates personalized marathon training plans.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class TrainingAgent:
    """
    Main training agent class for generating personalized marathon training plans.
    """

    def __init__(self):
        """Initialize the training agent."""
        self.training_plans = {}
        self.user_data = {}

    def analyze_garmin_data(self, garmin_data: Dict) -> Dict:
        """
        Analyze Garmin data to extract key metrics.

        Args:
            garmin_data: Dictionary containing Garmin fitness data

        Returns:
            Dictionary with analyzed metrics
        """
        if not isinstance(garmin_data, dict):
            raise ValueError("Garmin data must be a dictionary")

        metrics = {
            'avg_pace': self._calculate_average_pace(garmin_data.get('runs', [])),
            'weekly_mileage': self._calculate_weekly_mileage(garmin_data.get('runs', [])),
            'fitness_level': self._assess_fitness_level(garmin_data.get('runs', [])),
            'injury_risk': self._assess_injury_risk(garmin_data.get('runs', []))
        }

        return metrics

    def generate_training_plan(self, user_id: str, target_date: str,
                               current_fitness: Dict) -> Dict:
        """
        Generate a personalized marathon training plan.

        Args:
            user_id: Unique identifier for the user
            target_date: Target marathon date (YYYY-MM-DD format)
            current_fitness: Current fitness metrics

        Returns:
            Dictionary containing the training plan
        """
        if not user_id:
            raise ValueError("User ID cannot be empty")

        try:
            target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Target date must be in YYYY-MM-DD format")

        weeks_to_marathon = (target_datetime - datetime.now()).days // 7

        if weeks_to_marathon < 12:
            raise ValueError("Need at least 12 weeks to prepare for marathon")

        plan = {
            'user_id': user_id,
            'target_date': target_date,
            'weeks_to_marathon': weeks_to_marathon,
            'weekly_schedule': self._create_weekly_schedule(current_fitness, weeks_to_marathon),
            'progression': self._create_progression_plan(current_fitness, weeks_to_marathon)
        }

        self.training_plans[user_id] = plan
        return plan

    def get_training_plan(self, user_id: str) -> Optional[Dict]:
        """
        Retrieve a training plan for a user.

        Args:
            user_id: Unique identifier for the user

        Returns:
            Training plan dictionary or None if not found
        """
        return self.training_plans.get(user_id)

    def update_progress(self, user_id: str, workout_data: Dict) -> bool:
        """
        Update user's training progress.

        Args:
            user_id: Unique identifier for the user
            workout_data: Dictionary containing workout information

        Returns:
            True if update was successful, False otherwise
        """
        if user_id not in self.training_plans:
            return False

        if not isinstance(workout_data, dict):
            return False

        if user_id not in self.user_data:
            self.user_data[user_id] = []

        self.user_data[user_id].append(workout_data)
        return True

    def _calculate_average_pace(self, runs: List[Dict]) -> float:
        """Calculate average pace from run data."""
        if not runs:
            return 0.0

        total_time = sum(run.get('duration', 0) for run in runs)
        total_distance = sum(run.get('distance', 0) for run in runs)

        if total_distance == 0:
            return 0.0

        return total_time / total_distance  # seconds per mile/km

    def _calculate_weekly_mileage(self, runs: List[Dict]) -> float:
        """Calculate average weekly mileage."""
        if not runs:
            return 0.0

        total_distance = sum(run.get('distance', 0) for run in runs)
        weeks = len(runs) / 7 if len(runs) >= 7 else 1

        return total_distance / weeks

    def _assess_fitness_level(self, runs: List[Dict]) -> str:
        """Assess user's fitness level based on run data."""
        weekly_mileage = self._calculate_weekly_mileage(runs)

        if weekly_mileage < 10:
            return 'beginner'
        elif weekly_mileage < 25:
            return 'intermediate'
        else:
            return 'advanced'

    def _assess_injury_risk(self, runs: List[Dict]) -> str:
        """Assess injury risk based on training patterns."""
        if not runs:
            return 'low'

        # Simple assessment based on consistency
        recent_runs = runs[-7:] if len(runs) >= 7 else runs

        if len(recent_runs) > 5:
            return 'high'  # Too many runs per week
        elif len(recent_runs) < 2:
            return 'low'   # Not enough activity
        else:
            return 'medium'

    def _create_weekly_schedule(self, fitness: Dict, weeks: int) -> Dict:
        """Create a weekly training schedule."""
        fitness_level = fitness.get('fitness_level', 'beginner')

        base_schedule = {
            'beginner': {
                'runs_per_week': 3,
                'easy_runs': 2,
                'hard_runs': 1,
                'rest_days': 4
            },
            'intermediate': {
                'runs_per_week': 4,
                'easy_runs': 2,
                'hard_runs': 2,
                'rest_days': 3
            },
            'advanced': {
                'runs_per_week': 5,
                'easy_runs': 3,
                'hard_runs': 2,
                'rest_days': 2
            }
        }

        return base_schedule.get(fitness_level, base_schedule['beginner'])

    def _create_progression_plan(self, fitness: Dict, weeks: int) -> List[Dict]:
        """Create a week-by-week progression plan."""
        weekly_mileage = fitness.get('weekly_mileage', 10)

        progression = []
        current_mileage = weekly_mileage

        for week in range(weeks):
            # Gradual increase with recovery weeks
            if week % 4 == 3:  # Recovery week
                mileage = current_mileage * 0.8
            else:
                mileage = current_mileage * 1.1
                current_mileage = mileage

            progression.append({
                'week': week + 1,
                'target_mileage': round(mileage, 1),
                'focus': self._get_weekly_focus(week, weeks)
            })

        return progression

    def _get_weekly_focus(self, week: int, total_weeks: int) -> str:
        """Determine the training focus for a given week."""
        if week < total_weeks * 0.3:
            return 'base_building'
        elif week < total_weeks * 0.7:
            return 'strength_building'
        elif week < total_weeks * 0.9:
            return 'peak_training'
        else:
            return 'taper'


def main():
    """Main function for testing the training agent."""
    agent = TrainingAgent()

    # Sample Garmin data
    sample_data = {
        'runs': [
            {'distance': 5.0, 'duration': 1800, 'date': '2024-01-01'},
            {'distance': 3.0, 'duration': 1200, 'date': '2024-01-03'},
            {'distance': 8.0, 'duration': 3000, 'date': '2024-01-06'}
        ]
    }

    # Analyze data
    metrics = agent.analyze_garmin_data(sample_data)
    print("Fitness Metrics:", json.dumps(metrics, indent=2))

    # Generate training plan (set date to be far enough in the future)
    future_date = (datetime.now() + timedelta(days=100)).strftime('%Y-%m-%d')
    plan = agent.generate_training_plan(
        user_id="test_user",
        target_date=future_date,
        current_fitness=metrics
    )
    print("\nTraining Plan:", json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
