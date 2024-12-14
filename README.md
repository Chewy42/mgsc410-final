# Real Estate Investment Optimizer

This Shiny web application helps real estate investors optimize their property search based on their specific priorities and budget constraints.

# Deployed EC2 Instance Link:
http://3.101.14.134

## Features

- **Investment Parameters**
  - Budget range specification ($min - $max)
  - Property type preferences (warehouse, office, retail, etc.)
  - Priority optimization metrics:
    - Square footage maximization
    - Number of rooms optimization
    - Location value scoring
    - Return on Investment (ROI) potential

- **Interactive Visualization**
  - Heat map of property locations
  - Property comparison charts
  - Optimization results display

## Setup

To run this application, you need:

1. Python 3.7+ installed on your system
2. The following Python packages:
   ```bash
   pip install shiny pandas numpy folium plotly
   ```

## Running the Application

To run the application:

1. Open a terminal
2. Navigate to this directory
3. Run: `shiny run app.py`

## Structure

- `app.py`: Main application file containing both UI and server logic
- `utils/`: Helper functions for optimization and data processing
- `data/`: Property dataset and related files

## How It Works

1. Users input their investment parameters:
   - Budget range
   - Property type preferences
   - Optimization priorities

2. The application uses optimization algorithms to:
   - Filter properties within budget
   - Apply weighted scoring based on priorities
   - Rank properties by optimization criteria

3. Results are displayed through:
   - Interactive heat map
   - Detailed property comparisons
   - Optimization metrics visualization