📊 REASON Analysis Dashboard
Interactive web application for analyzing REASON data with automated data processing, cleaning, and comprehensive visualization.
Show Image
Show Image
Show Image
🎯 Features
📁 Data Management

Multiple File Upload: Combine multiple Excel files into one unified dataset
Smart Data Merging: Automatically concatenate files with identical structures

🧹 Data Processing Pipeline

Data Consolidation: Merge all uploaded files
Data Cleaning:

Remove duplicate records based on key columns
Filter invalid data (mismatched dates)
Clean REASON column (remove prefixes and suffixes)


Automated Processing:

Split ADMIN column into ADMIN_NAME, ADMIN_ID, and ADMIN_USER
Add Reason Status (WITH REASON / NO REASON)
Add Publish Status based on roster dates
Convert UTC to WIB timezone (UTC+7)
Categorize User Status (Crew Training, Crew Admin, Crew Control, Tracking, OTHER)
Determine Kategori (ACTUAL, PLAN, OTHER)



📊 Analytics & Visualization

Interactive Filters: Filter by COMPANY, Kategori, User Status, Reason Status, Publish Status
Key Metrics Dashboard:

Total Records
With Reason vs No Reason
ACTUAL vs PLAN counts


Visual Charts:

Pie Chart: Reason Status Distribution
Bar Charts: Kategori, Top 5 REASON (%), User Status Distribution


Detailed Statistics: Comprehensive breakdown by REASON with percentages
Data Table: Interactive table with all processed data

📥 Export Options

Download Cleaned Data: Get lightweight file with duplicates removed
Download Full Processed Data: Complete dataset with all new columns
Transparent Chart Backgrounds: Charts ready for presentations

🚀 Quick Start
Prerequisites

Python 3.9 or higher
pip package manager

Installation

Clone the repository

bashgit clone https://github.com/yourusername/reason-analysis-dashboard.git
cd reason-analysis-dashboard

Install dependencies

bashpip install -r requirements.txt

Run the application

bashstreamlit run app.py

Open your browser

http://localhost:8501
📦 Dependencies
streamlit==1.31.0
pandas==2.1.4
numpy==1.26.3
plotly==5.18.0
openpyxl==3.1.2
📖 Usage
Step 1: Upload Files

Specify the number of Excel files to merge
Upload each file (must have identical column structure)
Click "🔄 Proses Data"

Step 2: Review Processing

View processing progress (3 steps)
Check data summary (original vs cleaned counts)

Step 3: Analyze Data

Use sidebar filters to slice data
View metrics and visualizations
Explore detailed statistics tables

Step 4: Export Results

Download cleaned data (smaller file size)
Download fully processed data (all columns included)

📊 Data Structure
Required Columns in Input Files:
NO, ID, NAME, COMPANY, RANK, ROSTER DATE, PAIRING CODE, ACTIVITY, 
STD (UTC Time), ROUTE, ACTION, ACTION TIME (CGK Time), ADMIN, REASON, 
PAIRING MEMO, ROSTER MEMO, Type of Modification, ACTIVITY BEFORE, 
ACTIVITY AFTER, ROUTE BEFORE, ROUTE AFTER
Generated Columns:
ADMIN_NAME, ADMIN_ID, ADMIN_USER, Reason Status, Publish Status, 
STD (Local Time), User Status, Kategori
🎨 Screenshots
Main Dashboard
Show Image
Data Visualization
Show Image
🛠️ Technical Details
Architecture

Frontend: Streamlit
Data Processing: Pandas, NumPy
Visualization: Plotly
File Handling: openpyxl

Processing Workflow
Upload Files → Merge Data → Clean Data → Process Data → Analyze → Export
🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

Fork the repository
Create your feature branch (git checkout -b feature/AmazingFeature)
Commit your changes (git commit -m 'Add some AmazingFeature')
Push to the branch (git push origin feature/AmazingFeature)
Open a Pull Request

📝 License
This project is licensed under the MIT License - see the LICENSE file for details.
👨‍💻 Author
Your Name

GitHub: @yourusername
Email: your.email@example.com

🙏 Acknowledgments

Built with Streamlit
Charts powered by Plotly
Data processing with Pandas

📞 Support
For support, email your.email@example.com or open an issue in the repository.

⭐ Star this repository if you find it helpful!
