# Sentiment Analysis Model Testing Guide

This guide helps you test different sentiment analysis models on a sample of data from your cb table.

## Step 1: Generate Test Set

First, randomly sample 50 contents from the cb table:

```bash
cd data-pre
python3 test_sentiment_models.py
```

This will:
- Randomly select 50 records from the `cb` table that have content
- Save them to `data-pre/sentiment_test_set.json`
- Display a summary of the test set

## Step 2: Install Required Libraries (Optional)

The evaluation script supports multiple sentiment analysis models:

### TextBlob
```bash
pip install textblob
python -m textblob.download_corpora  # Download required data
```

### VADER Sentiment
```bash
pip install vaderSentiment
```

### OpenAI (already configured if you have OPENAI_API_KEY)
No additional installation needed, but make sure `OPENAI_API_KEY` is set in your `backend/.env` file.

## Step 3: Evaluate Models

Run the evaluation script to test different models:

```bash
cd data-pre
python3 evaluate_sentiment_models.py
```

This will:
- Load the test set from `data-pre/sentiment_test_set.json`
- Run each available sentiment analysis model on all samples
- Calculate accuracy, precision, recall, and F1-score for each model
- Compare results across models

## Understanding the Results

The script uses the following as ground truth:
1. **Existing sentiment field** (if available in the database)
2. **Likes-based proxy** (if sentiment is null):
   - `likes > 0` → positive
   - `likes < 0` → negative
   - `likes = 0` → neutral

### Output Format

```
Results for ModelName
============================================================
Accuracy: 75.00% (38/50)

Per-class metrics:
Class      Precision    Recall       F1-Score     Support   
------------------------------------------------------------
positive   0.80         0.75         0.77         20       
negative   0.70         0.65         0.67         15       
neutral    0.75         0.80         0.77         15       
```

## Manual Labeling (Optional)

For more accurate results, you can manually label the test set:

1. Open `data-pre/sentiment_test_set.json`
2. For each sample, add or update the `sentiment` field with one of:
   - `"positive"`
   - `"negative"`
   - `"neutral"`
3. Save the file
4. Run `evaluate_sentiment_models.py` again

Example:
```json
{
  "id": 123,
  "content": "Great product!",
  "sentiment": "positive",  // ← Add this
  ...
}
```

## Models Available

1. **TextBlob**: Simple rule-based sentiment analysis
   - Fast and lightweight
   - Good for general text
   
2. **VADER**: Valence Aware Dictionary and sEntiment Reasoner
   - Specifically designed for social media text
   - Handles negations and intensifiers well
   
3. **OpenAI GPT-3.5-turbo**: Large language model
   - Most accurate but slower and costs money
   - Requires API key configuration

## Tips

- For best results, manually label at least a subset of your test data
- Consider the context: social media text may work better with VADER
- Test on different types of content (short vs long, different languages, etc.)
- Compare models based on your specific use case (accuracy vs speed vs cost)

