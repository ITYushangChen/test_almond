# Theme Insights Data

This directory contains pre-generated AI insights for all base_themes and sub_themes.

## File

- `theme_insights.json`: Pre-generated insights for all themes

## Generating Insights

To generate or regenerate the insights file, run:

```bash
cd backend
python generate_theme_insights.py
```

This script will:
1. Fetch all base_themes and sub_themes from the database
2. Extract positive and negative content for each theme
3. Generate AI insights using OpenAI API
4. Save all insights to `data/theme_insights.json`

**Note**: This process may take a while and will consume OpenAI API credits. Make sure you have:
- `OPENAI_API_KEY` configured in your environment
- Sufficient API credits
- Database connection configured

## File Format

The JSON file has the following structure:

```json
{
  "base_theme_theme_name": {
    "positive_summary": "Summary text...",
    "negative_summary": "Summary text...",
    "positive_recommendations": ["rec 1", "rec 2", "rec 3"],
    "negative_recommendations": ["rec 1", "rec 2", "rec 3"]
  },
  "sub_theme_theme_name": {
    ...
  }
}
```

## Usage

The backend API (`/api/analysis/theme-insights`) automatically loads insights from this file. No manual intervention needed after generation.

