

# Stop Using Generic Training Plans. Your Garmin Data Holds the Key to Your Next Personal Best.

![Streamlit App Running](images/example.png)

Are you a runner tired of one-size-fits-all training schedules? Do you have years of valuable performance data locked away in your Garmin Connect account?

This project transforms that data into your ultimate competitive advantage. We've built a **Personalized Training Assistant** that acts as your personal AI running coach, crafting the perfect half-marathon plan tailored specifically to *you*.

## Features

- **Data Import:**
  - Supports CSV and TCX files exported from Garmin Connect.
  - Reads and processes sports activity data.

- **Exploratory Analysis:**
  - Generates detailed analyses of completed runs.
  - Provides performance statistics, progress, and training patterns.

- **Training Planning:**
  - Automatically generates complete training plans for half marathons.
  - Customizes plans based on the athlete's history.

- **Export and Integration:**
  - Exports plans and analyses in easy-to-read formats.
  - Integrates with platforms such as SisRun.

## Project Structure

```
├── detailed_run_analysis.txt           # Detailed running analysis report
├── garmin_activities.csv               # Raw data exported from Garmin Connect
├── connection_and_exploration.ipynb    # Data exploration and connection notebook
├── garmin_training_20250222.tcx        # Example TCX training file
├── requirements.txt                    # Project dependencies
└── src/
  ├── garmin_activities.csv           # Internal copy of activity data
  ├── garmin_connect.py               # Garmin data connection and reading module
  ├── generate_full_plan.py           # Complete training plan generation
  ├── main.py                         # Main execution script
  ├── half_marathon_full_plan.txt     # Example generated plan
  ├── sisrun_export.py                # SisRun export module
  └── training_agent.py               # Training analysis and planning logic
```

### Who is This For?

*   **For the Ambitious Runner:** Whether you're tackling your first half marathon or aiming to shatter your personal record, our AI agent analyzes your unique running style, fitness level, and weekly availability to build a plan that is 100% yours. No more generic advice—just a data-driven strategy for success.

*   **For the Data-Driven Athlete & Developer:** This is more than just a training app; it's a powerful sports analytics tool. Dive into a project that showcases the real-world application of AI in sports. Explore your performance trends, visualize your progress, and see what a data-first approach can do. Built with Python, Pandas, and Streamlit, it's a perfect portfolio piece.

## Quick Start Guide 🚀

1. **Set Up Your Environment:**
    ```bash
    # Clone this repository
    git clone https://github.com/diegosimao/Personalized-Training-Assistant-Agent.git
    
    # Install dependencies
    pip install -r requirements.txt
    ```

2. **Launch Your AI Coach:**
    ```bash
    # Start the Streamlit app
    python -m streamlit run src/main.py
    ```

3. **Start Your Journey:**
    - Upload your Garmin data
    - Define your goals
    - Get your personalized plan instantly

## Built With Powerful Tech 💪

- **Python 3** - The core of our AI engine
- **Pandas & NumPy** - For lightning-fast data analysis
- **Streamlit** - Creating a beautiful, responsive UI
- **Jupyter Notebook** - For deep dive analytics
- **Custom AI Models** - Making sense of your running patterns

## Roadmap 🗺️

- Integration with more sports platforms
- Real-time training adjustments
- Support for multiple race distances
- Advanced performance analytics dashboard
- Mobile app development

## Contributing 🤝

Your contributions are welcome! Whether you're fixing bugs, adding new features, or improving documentation, check out our contributing guidelines to get started.

## Support ⭐

If you find this project useful, give it a star! It helps others discover this tool and motivates further development.

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Created By

**Diego Simão** - Transforming running data into winning strategies.

---

*Stop following generic plans. Start training smarter with data-driven insights.*
