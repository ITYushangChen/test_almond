# Sentiment Analysis Models

This directory contains implementations of various mature sentiment analysis models for comparison on your test set.

## Available Models

### 1. **TextBlob**
- **Type**: Rule-based
- **Speed**: Fast
- **Installation**: `pip install textblob && python -m textblob.download_corpora`
- **Best for**: General text, simple use cases

### 2. **VADER (Valence Aware Dictionary and sEntiment Reasoner)**
- **Type**: Rule-based, lexicon-based
- **Speed**: Fast
- **Installation**: `pip install vaderSentiment`
- **Best for**: Social media text, short texts with slang/emojis

### 3. **Transformers (Twitter RoBERTa)**
- **Type**: Deep learning (BERT-based)
- **Speed**: Medium (GPU recommended)
- **Installation**: `pip install transformers torch`
- **Model**: `cardiffnlp/twitter-roberta-base-sentiment-latest`
- **Best for**: Twitter/social media text, high accuracy

### 4. **OpenAI GPT-3.5-turbo / GPT-4**
- **Type**: Large language model
- **Speed**: Slow (API calls)
- **Installation**: Configure `OPENAI_API_KEY` in `backend/.env`
- **Best for**: High accuracy, complex text, multilingual

### 5. **Flair**
- **Type**: Deep learning (contextualized embeddings)
- **Speed**: Medium
- **Installation**: `pip install flair`
- **Best for**: General text, good balance of accuracy and speed

## Installation

### Minimal Setup (TextBlob + VADER)
```bash
pip install textblob vaderSentiment
python -m textblob.download_corpora
```

### Full Setup (All Models)
```bash
# Basic models
pip install textblob vaderSentiment
python -m textblob.download_corpora

# Transformers (requires more memory)
pip install transformers torch

# Flair
pip install flair

# OpenAI (configure API key in backend/.env)
# No additional installation needed
```

## Usage

### Run Comparison

```bash
cd data-pre
python3 -m sentiment_analysis.run_comparison
```

Or from the sentiment_analysis directory:

```bash
cd data-pre/sentiment_analysis
python3 run_comparison.py
```

### Programmatic Usage

```python
from sentiment_analysis.evaluator import SentimentEvaluator
from sentiment_analysis.textblob_model import TextBlobModel
from sentiment_analysis.vader_model import VaderModel

# Load test set
evaluator = SentimentEvaluator('sentiment_test_set.json')

# Initialize models
models = [
    TextBlobModel(),
    VaderModel()
]

# Compare models
results = evaluator.compare_models(models)
evaluator.print_results(results)
```

## Output

The script will:
1. Load all available models
2. Evaluate each model on the test set
3. Calculate metrics:
   - Overall accuracy
   - Per-class precision, recall, F1-score
   - Support (number of samples per class)
4. Print a comparison table
5. Save results to `sentiment_comparison_results.json`

## Model Recommendations

**For Social Media Text (like Reddit comments):**
- Best: VADER or Twitter RoBERTa
- Fast: VADER
- Accurate: Twitter RoBERTa

**For General Text:**
- Best: Transformers or OpenAI
- Fast: TextBlob or VADER
- Accurate: OpenAI GPT-4

**For Production:**
- Speed-critical: VADER
- Accuracy-critical: OpenAI GPT-4 or Transformers
- Balanced: Flair or Twitter RoBERTa

## Notes

- Models are initialized lazily (only when first used)
- Transformers models require significant memory (2-4GB RAM)
- OpenAI models require API key and cost money per request
- First run of transformers/flair models will download weights (~500MB-2GB)

