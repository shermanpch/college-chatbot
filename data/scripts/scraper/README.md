# Data Scrapers

This directory contains comprehensive scripts for downloading and scraping various education-related data sources with automated discovery, retry logic, and organized storage.

## 🔧 Scrapers Overview

### 🏫 [peterson_search_data/](peterson_search_data/)
**University Data Scraping & Processing**
Complete pipeline for scraping and processing comprehensive university data from Peterson's college search website.

**Main Scripts:**
- `001_get_peterson_urls.py` - Searches Peterson's website for universities and extracts profile URLs
- `002_get_correct_peterson_url.py` - Validates and matches Peterson URLs against university datasets
- `003_get_peterson_data.py` - Batch scrapes university data using Firecrawl API
- `004_rescrape_failed_urls.py` - Re-scrapes URLs that failed initial processing
- `005_scrape_courses_bs.py` - Scrapes course information for universities using BeautifulSoup
- `006_combine_peterson_courses.py` - Combines course data from multiple sources
- `007_clean_peterson_data.py` - Extracts and combines JSON data from scraped files
- `models.py` - Pydantic models defining the data structure for university information

**Key Features:**
- 🔍 **URL Discovery**: Automated search and extraction of university profile URLs
- ✅ **URL Validation**: Smart matching and validation against existing university datasets
- 🌐 **Batch Scraping**: Efficient batch processing using Firecrawl API with retry logic
- 📊 **Structured Data**: Comprehensive university information extraction including:
  - 📍 Location and contact information
  - 🎓 Academic programs and majors
  - 📈 Admission statistics and requirements
  - 💰 Tuition, fees, and financial aid information
  - 🏃 Athletics and campus life details
  - 👨‍🏫 Faculty information and statistics
- 🔄 **Error Recovery**: Automatic identification and re-scraping of failed URLs
- 🧹 **Data Cleaning**: Automated extraction and combination of university data
- 🌐 **Multiple Scraping Methods**: BeautifulSoup-based scraping for reliable course data extraction
- 📝 **Comprehensive Logging**: Detailed progress tracking and error reporting

## 🚀 Installation & Setup

Install the required dependencies:

**1. Install the main project as an editable package** (required for `projectutils` imports):
```bash
pip install -e .
```

**2. Install the scraper-specific dependencies**:
```bash
pip install -r data/scripts/scraper/requirements.txt
```

**Key Dependencies:**
- `requests` - HTTP requests and web scraping
- `beautifulsoup4` - HTML parsing
- `lxml` - HTML/XML parser backend for BeautifulSoup
- `firecrawl-py` - Batch scraping via the Firecrawl API
- `selenium` - JavaScript-heavy page handling
- `fuzzywuzzy` - Fuzzy string matching for URL validation
- `levenshtein` - String distance backend for fuzzywuzzy
- `pandas` - Reads university CSV/JSON datasets for URL validation
- `pydantic` - Schema models for scraped data (`models.py`)

## 📖 Quick Start Guide

### Peterson University Data

**Complete Pipeline Process:**

**1. Extract University URLs:**
```bash
python data/scripts/scraper/peterson_search_data/001_get_peterson_urls.py
```

**2. Validate URLs Against Dataset:**
```bash
python data/scripts/scraper/peterson_search_data/002_get_correct_peterson_url.py
```

**3. Batch Scrape University Data:**
```bash
python data/scripts/scraper/peterson_search_data/003_get_peterson_data.py --num-batches 10
```

**4. Re-scrape Failed URLs (if needed):**
```bash
python data/scripts/scraper/peterson_search_data/004_rescrape_failed_urls.py
```

**5. Scrape Course Information:**
```bash
python data/scripts/scraper/peterson_search_data/005_scrape_courses_bs.py
```

**6. Combine Course Data:**
```bash
python data/scripts/scraper/peterson_search_data/006_combine_peterson_courses.py
```

**7. Clean and Combine Data:**
```bash
python data/scripts/scraper/peterson_search_data/007_clean_peterson_data.py
```

**Pipeline Overview:**
1. **URL Discovery**: Searches Peterson's website for university URLs
2. **URL Correction**: Validates and gets correct URLs against existing university datasets
3. **Batch Scraping**: Uses Firecrawl API to scrape university data in batches
4. **Error Recovery**: Identifies and re-scrapes any failed URLs
5. **Course Scraping**: Scrapes detailed course information for universities
6. **Course Combination**: Combines course data from multiple sources
7. **Data Cleaning**: Extracts JSON data and combines into single dataset

## 📁 Data Organization & Output

### Peterson University Data Structure
```
data/
├── chatbot/
│   └── peterson_data.json                      # Final cleaned university dataset
├── cleaned/
│   ├── peterson_university_urls.json           # University search results and URLs
│   ├── peterson_university_urls_backup.json    # Backup of university URLs
│   ├── peterson_url_validation_results.json    # URL validation and matching results
│   └── peterson_url_validation_results_backup.json # Backup of validation results

└── external/
    ├── peterson_data/
    │   └── *.json                              # Raw scraped university data files
    └── peterson_courses_data/
        └── *.json                              # Course data scraped using BeautifulSoup
```

## 🔧 Advanced Usage & Configuration

### Peterson University Scraper

**Pipeline Requirements:**
- University dataset (CSV/JSON) for URL validation
- `FIRECRAWL_API_KEY` environment variable; scripts `003` and `004` exit if it is unset
- Internet connection for web scraping

**Performance Features:**
- **Async Batch Submission**: Scripts `003` and `004` submit batch jobs to the Firecrawl API, then you download the results from the Firecrawl dashboard
- **Smart Validation**: Matches URLs against existing datasets before scraping
- **Error Recovery**: Automatic identification and re-submission of failed URLs
- **Efficient Storage**: Organized file structure with progress tracking

## 📝 Logging & Monitoring

### Peterson University Data

Each script derives its log filename from its path relative to the project root, replacing separators with underscores.

- **Log Files**:
  - `logs/data_scripts_scraper_peterson_search_data_003_get_peterson_data.log` - Batch scraping progress and job submissions
  - `logs/data_scripts_scraper_peterson_search_data_004_rescrape_failed_urls.log` - Failed URL re-scraping activities
  - `logs/data_scripts_scraper_peterson_search_data_007_clean_peterson_data.log` - Data cleaning and extraction progress
- **Content**: Pipeline progress, URL validation, batch job tracking, data extraction, error recovery
- **Monitoring**: Real-time progress tracking for each pipeline stage

## 🛠️ Troubleshooting Guide

### Common Issues & Solutions

**Network-Related Issues:**
1. **Connection timeouts**: Scripts include retry logic with exponential backoff
2. **Rate limiting**: Appropriate delays built into scrapers
3. **DNS issues**: Check internet connection and DNS settings

**File & Storage Issues:**
1. **Disk space**: Large datasets require significant storage space
2. **File permissions**: Ensure write permissions to output directories
3. **Existing files**: Scripts automatically skip existing files

**Data-Specific Issues:**
1. **Large files**: Some datasets are very large; be patient or use selective downloads

### Performance Optimization

**For Large Downloads:**
1. **Batch processing**: Download categories in smaller batches
2. **Selective downloads**: Focus on specific years or categories
3. **Resume capability**: Re-run scripts to continue interrupted downloads
4. **Storage planning**: Ensure adequate disk space before starting

**For Web Scraping:**
1. **Stable internet**: Ensure reliable internet connection
2. **Browser compatibility**: Keep browser drivers updated for Selenium
3. **Memory management**: Monitor memory usage for large scraping jobs

## 🔍 Data Quality & Validation

### Peterson University Data
- **Pipeline validation**: Multi-stage validation throughout the process
- **URL matching**: Smart matching against existing university datasets
- **Data consistency**: Pydantic models ensure structured data extraction
- **Error tracking**: Comprehensive tracking of failed URLs and re-scraping
- **Data completeness**: Final dataset combines all successfully scraped universities

## 📚 Additional Resources

### Getting Help
```bash
# Check Peterson pipeline logs
tail -f logs/data_scripts_scraper_peterson_search_data_003_get_peterson_data.log
tail -f logs/data_scripts_scraper_peterson_search_data_004_rescrape_failed_urls.log
tail -f logs/data_scripts_scraper_peterson_search_data_007_clean_peterson_data.log
```

### Best Practices
1. **Start small**: Begin with specific categories or years
2. **Monitor progress**: Check logs regularly for large downloads
3. **Plan storage**: Estimate storage requirements before downloading
4. **Backup data**: Consider backing up downloaded data
5. **Respect terms**: Both scrapers respect website terms of service

## ⚠️ Important Notes

- **Terms of Service**: Both scrapers include appropriate delays and respect website terms
- **Data Size**: Some datasets are very large (>1GB); plan accordingly
- **Processing Time**: Large downloads may take hours; use screen/tmux for long sessions
- **Directory Structure**: Scripts automatically create necessary directory structures
- **Error Recovery**: Failed operations are logged and can be retried
- **Browser Requirements**: Peterson scraper requires Chrome/Chromium for Selenium

## 🔄 Updates & Maintenance

- **Regular Updates**: Peterson's website structure may change; scripts may need updates
- **Dependency Management**: Keep dependencies updated for security and compatibility
- **Log Rotation**: Consider rotating log files for long-term usage
- **Data Archival**: Plan for long-term storage and archival of downloaded data
