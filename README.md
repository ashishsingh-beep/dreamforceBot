# Dreamforce Scout App

## Overview
The Dreamforce Scout App is a Streamlit application designed to assist users in scouting leads, scraping LinkedIn profile details, and finding relevant leads. The application features a multi-tab interface for easy navigation and functionality.

## Project Structure
```
dreamforce-scout-app
├── app.py                # Main Streamlit application code
├── stages                # Contains the implementation of various stages
│   ├── stage_1.py       # Implementation of the scout_leads function
│   ├── stage_2.py       # Implementation of the get_linkedin_profile_details function
│   └── stage_3.py       # Implementation of the get_gemini_response function
├── data                  # Directory for input and output data
│   ├── input            # Input CSV files
│   └── output           # Output CSV files
├── requirements.txt      # List of project dependencies
├── .env.example          # Template for environment variables
└── README.md             # Documentation for the project
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd dreamforce-scout-app
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy `.env.example` to `.env` and fill in the necessary API keys and configurations.

## Usage
1. Run the Streamlit application:
   ```
   streamlit run app.py
   ```

2. Navigate through the tabs:
   - **Scout Leads**: Input keywords and posts to scout leads and download results as a CSV.
   - **Scrape Details**: Input LinkedIn URLs to scrape profile details and download results as a CSV.
   - **Find Relevant Leads**: This tab is currently left blank for future development.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.