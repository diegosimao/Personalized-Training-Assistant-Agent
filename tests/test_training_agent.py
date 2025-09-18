"""
Unit tests for the TrainingAgent class.
"""

import pytest
from datetime import datetime, timedelta
from training_agent import TrainingAgent


class TestTrainingAgent:
    """Test cases for the TrainingAgent class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.agent = TrainingAgent()
        self.sample_garmin_data = {
            'runs': [
                {'distance': 5.0, 'duration': 1800, 'date': '2024-01-01'},
                {'distance': 3.0, 'duration': 1200, 'date': '2024-01-03'},
                {'distance': 8.0, 'duration': 3000, 'date': '2024-01-06'}
            ]
        }

    def test_training_agent_initialization(self):
        """Test that TrainingAgent initializes correctly."""
        agent = TrainingAgent()
        assert isinstance(agent.training_plans, dict)
        assert isinstance(agent.user_data, dict)
        assert len(agent.training_plans) == 0
        assert len(agent.user_data) == 0

    def test_analyze_garmin_data_valid_input(self):
        """Test analyzing valid Garmin data."""
        metrics = self.agent.analyze_garmin_data(self.sample_garmin_data)

        assert isinstance(metrics, dict)
        assert 'avg_pace' in metrics
        assert 'weekly_mileage' in metrics
        assert 'fitness_level' in metrics
        assert 'injury_risk' in metrics

        # Check that values are reasonable
        assert metrics['avg_pace'] > 0
        assert metrics['weekly_mileage'] > 0
        assert metrics['fitness_level'] in ['beginner', 'intermediate', 'advanced']
        assert metrics['injury_risk'] in ['low', 'medium', 'high']

    def test_analyze_garmin_data_invalid_input(self):
        """Test analyzing invalid Garmin data."""
        with pytest.raises(ValueError, match="Garmin data must be a dictionary"):
            self.agent.analyze_garmin_data("invalid_data")

        with pytest.raises(ValueError, match="Garmin data must be a dictionary"):
            self.agent.analyze_garmin_data(None)

    def test_analyze_garmin_data_empty_runs(self):
        """Test analyzing Garmin data with empty runs."""
        empty_data = {'runs': []}
        metrics = self.agent.analyze_garmin_data(empty_data)

        assert metrics['avg_pace'] == 0.0
        assert metrics['weekly_mileage'] == 0.0
        assert metrics['fitness_level'] == 'beginner'
        assert metrics['injury_risk'] == 'low'

    def test_generate_training_plan_valid_input(self):
        """Test generating a valid training plan."""
        metrics = self.agent.analyze_garmin_data(self.sample_garmin_data)
        future_date = (datetime.now() + timedelta(days=100)).strftime('%Y-%m-%d')

        plan = self.agent.generate_training_plan(
            user_id="test_user",
            target_date=future_date,
            current_fitness=metrics
        )

        assert isinstance(plan, dict)
        assert plan['user_id'] == "test_user"
        assert plan['target_date'] == future_date
        assert 'weeks_to_marathon' in plan
        assert 'weekly_schedule' in plan
        assert 'progression' in plan

        # Check that plan is stored
        assert "test_user" in self.agent.training_plans

    def test_generate_training_plan_invalid_user_id(self):
        """Test generating training plan with invalid user ID."""
        metrics = self.agent.analyze_garmin_data(self.sample_garmin_data)
        future_date = (datetime.now() + timedelta(days=100)).strftime('%Y-%m-%d')

        with pytest.raises(ValueError, match="User ID cannot be empty"):
            self.agent.generate_training_plan(
                user_id="",
                target_date=future_date,
                current_fitness=metrics
            )

        with pytest.raises(ValueError, match="User ID cannot be empty"):
            self.agent.generate_training_plan(
                user_id=None,
                target_date=future_date,
                current_fitness=metrics
            )

    def test_generate_training_plan_invalid_date_format(self):
        """Test generating training plan with invalid date format."""
        metrics = self.agent.analyze_garmin_data(self.sample_garmin_data)

        with pytest.raises(ValueError, match="Target date must be in YYYY-MM-DD format"):
            self.agent.generate_training_plan(
                user_id="test_user",
                target_date="invalid-date",
                current_fitness=metrics
            )

    def test_generate_training_plan_insufficient_time(self):
        """Test generating training plan with insufficient preparation time."""
        metrics = self.agent.analyze_garmin_data(self.sample_garmin_data)
        near_future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        with pytest.raises(ValueError, match="Need at least 12 weeks to prepare for marathon"):
            self.agent.generate_training_plan(
                user_id="test_user",
                target_date=near_future_date,
                current_fitness=metrics
            )

    def test_get_training_plan_existing_user(self):
        """Test retrieving an existing training plan."""
        metrics = self.agent.analyze_garmin_data(self.sample_garmin_data)
        future_date = (datetime.now() + timedelta(days=100)).strftime('%Y-%m-%d')

        # Generate plan first
        original_plan = self.agent.generate_training_plan(
            user_id="test_user",
            target_date=future_date,
            current_fitness=metrics
        )

        # Retrieve plan
        retrieved_plan = self.agent.get_training_plan("test_user")

        assert retrieved_plan is not None
        assert retrieved_plan == original_plan

    def test_get_training_plan_nonexistent_user(self):
        """Test retrieving a non-existent training plan."""
        plan = self.agent.get_training_plan("nonexistent_user")
        assert plan is None

    def test_update_progress_valid_input(self):
        """Test updating progress with valid input."""
        # First generate a plan
        metrics = self.agent.analyze_garmin_data(self.sample_garmin_data)
        future_date = (datetime.now() + timedelta(days=100)).strftime('%Y-%m-%d')
        self.agent.generate_training_plan(
            user_id="test_user",
            target_date=future_date,
            current_fitness=metrics
        )

        # Update progress
        workout_data = {
            'date': '2024-01-10',
            'distance': 5.0,
            'duration': 1800,
            'pace': 6.0
        }

        result = self.agent.update_progress("test_user", workout_data)
        assert result is True
        assert "test_user" in self.agent.user_data
        assert len(self.agent.user_data["test_user"]) == 1
        assert self.agent.user_data["test_user"][0] == workout_data

    def test_update_progress_nonexistent_user(self):
        """Test updating progress for non-existent user."""
        workout_data = {'date': '2024-01-10', 'distance': 5.0}
        result = self.agent.update_progress("nonexistent_user", workout_data)
        assert result is False

    def test_update_progress_invalid_workout_data(self):
        """Test updating progress with invalid workout data."""
        # First generate a plan
        metrics = self.agent.analyze_garmin_data(self.sample_garmin_data)
        future_date = (datetime.now() + timedelta(days=100)).strftime('%Y-%m-%d')
        self.agent.generate_training_plan(
            user_id="test_user",
            target_date=future_date,
            current_fitness=metrics
        )

        # Try to update with invalid data
        result = self.agent.update_progress("test_user", "invalid_data")
        assert result is False

        result = self.agent.update_progress("test_user", None)
        assert result is False

    def test_calculate_average_pace(self):
        """Test calculating average pace."""
        runs = [
            {'distance': 5.0, 'duration': 1800},  # 360 sec/mile
            {'distance': 3.0, 'duration': 1200},  # 400 sec/mile
        ]

        avg_pace = self.agent._calculate_average_pace(runs)
        expected_pace = (1800 + 1200) / (5.0 + 3.0)  # 375 sec/mile
        assert abs(avg_pace - expected_pace) < 0.01

    def test_calculate_average_pace_empty_runs(self):
        """Test calculating average pace with empty runs."""
        avg_pace = self.agent._calculate_average_pace([])
        assert avg_pace == 0.0

    def test_calculate_weekly_mileage(self):
        """Test calculating weekly mileage."""
        runs = [
            {'distance': 5.0},
            {'distance': 3.0},
            {'distance': 8.0},
        ]

        weekly_mileage = self.agent._calculate_weekly_mileage(runs)
        assert weekly_mileage == 16.0  # 3 runs total 16 miles, treated as 1 week

    def test_assess_fitness_level(self):
        """Test assessing fitness level."""
        # Test beginner level (less than 10 miles per week)
        beginner_runs = [{'distance': 1.0}] * 7  # 7 miles per week (when >= 7 runs, weeks = 1)
        fitness_level = self.agent._assess_fitness_level(beginner_runs)
        assert fitness_level == 'beginner'

        # Test intermediate level (10-24 miles per week)
        intermediate_runs = [{'distance': 3.0}] * 7  # 21 miles per week
        fitness_level = self.agent._assess_fitness_level(intermediate_runs)
        assert fitness_level == 'intermediate'

        # Test advanced level (25+ miles per week)
        advanced_runs = [{'distance': 4.0}] * 7  # 28 miles per week
        fitness_level = self.agent._assess_fitness_level(advanced_runs)
        assert fitness_level == 'advanced'

    def test_assess_injury_risk(self):
        """Test assessing injury risk."""
        # High risk - too many runs
        high_risk_runs = [{'distance': 3.0}] * 10
        risk = self.agent._assess_injury_risk(high_risk_runs)
        assert risk == 'high'

        # Low risk - too few runs
        low_risk_runs = [{'distance': 3.0}]
        risk = self.agent._assess_injury_risk(low_risk_runs)
        assert risk == 'low'

        # Medium risk - appropriate amount
        medium_risk_runs = [{'distance': 3.0}] * 3
        risk = self.agent._assess_injury_risk(medium_risk_runs)
        assert risk == 'medium'

    def test_create_weekly_schedule(self):
        """Test creating weekly schedule."""
        beginner_fitness = {'fitness_level': 'beginner'}
        schedule = self.agent._create_weekly_schedule(beginner_fitness, 16)

        assert 'runs_per_week' in schedule
        assert 'easy_runs' in schedule
        assert 'hard_runs' in schedule
        assert 'rest_days' in schedule
        assert schedule['runs_per_week'] == 3

    def test_create_progression_plan(self):
        """Test creating progression plan."""
        fitness = {'weekly_mileage': 20}
        progression = self.agent._create_progression_plan(fitness, 16)

        assert isinstance(progression, list)
        assert len(progression) == 16

        for week_plan in progression:
            assert 'week' in week_plan
            assert 'target_mileage' in week_plan
            assert 'focus' in week_plan
            assert week_plan['focus'] in ['base_building', 'strength_building', 'peak_training', 'taper']

    def test_get_weekly_focus(self):
        """Test getting weekly focus."""
        total_weeks = 20

        # Base building phase
        focus = self.agent._get_weekly_focus(2, total_weeks)
        assert focus == 'base_building'

        # Strength building phase
        focus = self.agent._get_weekly_focus(10, total_weeks)
        assert focus == 'strength_building'

        # Peak training phase
        focus = self.agent._get_weekly_focus(15, total_weeks)
        assert focus == 'peak_training'

        # Taper phase
        focus = self.agent._get_weekly_focus(19, total_weeks)
        assert focus == 'taper'


# Integration tests
class TestTrainingAgentIntegration:
    """Integration tests for the complete workflow."""

    def test_complete_workflow(self):
        """Test the complete workflow from data analysis to plan generation."""
        agent = TrainingAgent()

        # Sample data
        garmin_data = {
            'runs': [
                {'distance': 5.0, 'duration': 1800, 'date': '2024-01-01'},
                {'distance': 3.0, 'duration': 1200, 'date': '2024-01-03'},
                {'distance': 8.0, 'duration': 3000, 'date': '2024-01-06'},
                {'distance': 10.0, 'duration': 3600, 'date': '2024-01-08'}
            ]
        }

        # Analyze data
        metrics = agent.analyze_garmin_data(garmin_data)
        assert isinstance(metrics, dict)

        # Generate plan
        future_date = (datetime.now() + timedelta(days=100)).strftime('%Y-%m-%d')
        plan = agent.generate_training_plan(
            user_id="integration_test_user",
            target_date=future_date,
            current_fitness=metrics
        )
        assert isinstance(plan, dict)

        # Retrieve plan
        retrieved_plan = agent.get_training_plan("integration_test_user")
        assert retrieved_plan == plan

        # Update progress
        workout_data = {
            'date': '2024-01-10',
            'distance': 6.0,
            'duration': 2100,
            'notes': 'Good pace today'
        }
        success = agent.update_progress("integration_test_user", workout_data)
        assert success is True

        # Verify data was stored
        assert "integration_test_user" in agent.user_data
        assert len(agent.user_data["integration_test_user"]) == 1
