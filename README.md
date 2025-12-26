# SaaS Product Review Scraper

A Python script that scrapes SaaS product reviews from multiple review platforms (G2, Capterra, and TrustRadius) based on company name and date range filters.

## Project Overview

This tool enables automated collection of product reviews from popular SaaS review platforms. It extracts structured review data including titles, descriptions, dates, reviewer names, and ratings, filtering results by a specified date range.

## Features

- **Multi-Source Support**: Scrapes reviews from G2, Capterra, and TrustRadius
- **Date Range Filtering**: Filters reviews strictly between start_date and end_date
- **Automatic Pagination**: Handles pagination automatically to collect all matching reviews
- **Structured Output**: Exports reviews as a clean JSON array
- **Error Handling**: Comprehensive error handling with informative logging
- **Modular Design**: Clean, maintainable code with a base scraper class and platform-specific implementations

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Step-by-Step Installation

#### Option 1: Using Virtual Environment (Recommended)

1. **Navigate to the project directory:**
   ```bash
   cd "Pulse Coding Assignment"
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   # On Windows
   python -m venv venv
   
   # On macOS/Linux
   python3 -m venv venv
   ```

3. **Activate the virtual environment:**
   ```bash
   # On Windows (PowerShell)
   .\venv\Scripts\Activate.ps1
   
   # On Windows (Command Prompt)
   venv\Scripts\activate.bat
   
   # On macOS/Linux
   source venv/bin/activate
   ```

4. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

#### Option 2: Direct Installation (Without Virtual Environment)

1. **Navigate to the project directory:**
   ```bash
   cd "Pulse Coding Assignment"
   ```

2. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Required Packages

The following packages will be installed automatically:
- `requests` (>=2.31.0) - For HTTP requests to review platforms
- `beautifulsoup4` (>=4.12.0) - For HTML parsing and data extraction
- `lxml` (>=4.9.0) - HTML parser backend (recommended for better performance)

### Verify Installation

To verify that all packages are installed correctly, run:
```bash
python -c "import requests, bs4, lxml; print('All packages installed successfully!')"
```

## Usage

### Basic Command Syntax

```bash
python saas_reviews_scraper.py --company_name "CompanyName" --start_date YYYY-MM-DD --end_date YYYY-MM-DD --source SOURCE [--output OUTPUT_FILE]
```

### Command-Line Arguments

| Argument | Required | Description | Example |
|----------|----------|-------------|---------|
| `--company_name` | Yes | The name of the company/product to search for | `"Salesforce"` |
| `--start_date` | Yes | Start date in YYYY-MM-DD format | `2023-01-01` |
| `--end_date` | Yes | End date in YYYY-MM-DD format | `2023-12-31` |
| `--source` | Yes | Review source platform. Options: `G2`, `Capterra`, or `TrustRadius` | `G2` |
| `--output` | No | Output JSON file path (default: `reviews.json`) | `my_reviews.json` |

### Usage Examples

#### Example 1: Scrape G2 Reviews for Salesforce
```bash
python saas_reviews_scraper.py --company_name "Salesforce" --start_date 2023-01-01 --end_date 2023-12-31 --source G2
```
**Output:** Creates `reviews.json` with all Salesforce reviews from G2 in 2023.

#### Example 2: Scrape Capterra Reviews for HubSpot
```bash
python saas_reviews_scraper.py --company_name "HubSpot" --start_date 2023-06-01 --end_date 2023-06-30 --source Capterra
```
**Output:** Creates `reviews.json` with all HubSpot reviews from Capterra in June 2023.

#### Example 3: Scrape TrustRadius Reviews with Custom Output File
```bash
python saas_reviews_scraper.py --company_name "Slack" --start_date 2023-01-01 --end_date 2023-12-31 --source TrustRadius --output slack_reviews.json
```
**Output:** Creates `slack_reviews.json` with all Slack reviews from TrustRadius in 2023.

#### Example 4: Scrape Reviews for a Specific Month
```bash
python saas_reviews_scraper.py --company_name "Zoom" --start_date 2023-03-01 --end_date 2023-03-31 --source G2 --output zoom_march_2023.json
```
**Output:** Creates `zoom_march_2023.json` with all Zoom reviews from G2 in March 2023.

### Running the Script

1. **Ensure you're in the project directory** (or provide the full path to the script)

2. **Make sure Python is accessible:**
   ```bash
   python --version
   ```
   Should show Python 3.7 or higher.

3. **Run the script with your desired parameters:**
   ```bash
   python saas_reviews_scraper.py --company_name "YourCompany" --start_date 2023-01-01 --end_date 2023-12-31 --source G2
   ```

4. **Check the output:**
   - The script will display progress messages in the console
   - Upon completion, reviews will be saved to the specified JSON file (or `reviews.json` by default)
   - Review the output file to see the scraped reviews

### Expected Output

When you run the script, you'll see output like:
```
2024-01-15 10:30:00 - INFO - Validating input parameters...
2024-01-15 10:30:00 - INFO - Scraping reviews for 'Salesforce' from G2
2024-01-15 10:30:00 - INFO - Date range: 2023-01-01 to 2023-12-31
2024-01-15 10:30:01 - INFO - Scraping G2 page 1...
2024-01-15 10:30:02 - INFO - Scraping G2 page 2...
...
2024-01-15 10:30:15 - INFO - Successfully saved 45 reviews to reviews.json
```

## Output Format

The script outputs a JSON file containing an array of review objects. Each review object contains:

- `source`: The review platform (G2, Capterra, or TrustRadius)
- `title`: Review title/headline
- `description`: Full review text
- `review_date`: Date of the review (format may vary)
- `reviewer_name`: Name of the reviewer (if available)
- `rating`: Numeric rating (if available)

### Sample Output Structure

```json
[
  {
    "source": "G2",
    "title": "Excellent CRM solution",
    "description": "Great product with excellent features...",
    "review_date": "2023-03-15",
    "reviewer_name": "John Smith",
    "rating": "4.5"
  },
  {
    "source": "Capterra",
    "title": "Best CRM we've used",
    "description": "Highly recommend this product...",
    "review_date": "2023-05-10",
    "reviewer_name": "Michael Chen",
    "rating": "5.0"
  }
]
```

See `sample_output.json` for a complete example.

## How It Works

1. **Company Search**: The script searches for the specified company on the selected platform
2. **Review Collection**: Navigates to the reviews section and begins scraping
3. **Pagination**: Automatically handles pagination to collect all reviews
4. **Date Filtering**: Filters reviews to include only those within the specified date range
5. **Data Extraction**: Extracts structured data from each review element
6. **JSON Export**: Saves all matching reviews to a JSON file

## Technical Details

### Architecture

The code follows an object-oriented design with:
- `BaseScraper`: Abstract base class defining the scraper interface
- `G2Scraper`: Implementation for G2 platform
- `CapterraScraper`: Implementation for Capterra platform
- `TrustRadiusScraper`: Implementation for TrustRadius platform (bonus feature)

### Error Handling

The script includes comprehensive error handling for:
- Invalid date formats
- Network errors
- Company not found scenarios
- Parsing errors
- Rate limiting (basic handling)

### Logging

The script uses Python's logging module to provide informative messages about:
- Scraping progress
- Page numbers being processed
- Errors and warnings
- Final results summary

## Limitations & Notes

1. **Website Structure Changes**: Review platforms may change their HTML structure, which could require updates to the CSS selectors
2. **Rate Limiting**: Some platforms may implement rate limiting. The script includes basic handling, but you may need to add delays for large-scale scraping
3. **Dynamic Content**: Some platforms use JavaScript to load content dynamically. This script uses BeautifulSoup which works with static HTML
4. **Date Parsing**: The script attempts to parse various date formats, but some formats may not be recognized
5. **Authentication**: Some platforms may require authentication for accessing reviews

## Troubleshooting

**Issue: Company not found**
- Verify the company name matches exactly as it appears on the platform
- Try searching manually on the platform first

**Issue: No reviews found**
- Check that the date range includes reviews that exist
- Verify the company has reviews on the selected platform

**Issue: Network errors**
- Check your internet connection
- Some platforms may block automated requests - consider adding delays or using proxies

**Issue: Parsing errors**
- The platform's HTML structure may have changed
- Check the logs for specific error messages

## License

This project is created for educational purposes as part of a coding assignment.

## Author

Senior Python Engineer - Pulse Coding Assignment

