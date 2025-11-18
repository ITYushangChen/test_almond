"""
Transformers-based Sentiment Analysis Models
Using Hugging Face transformers library with pre-trained models
"""
try:
    from .base_model import SentimentModel
except ImportError:
    from base_model import SentimentModel

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

class TransformersModel(SentimentModel):
    """Transformers-based sentiment analysis model"""
    
    def __init__(self, model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"):
        """
        Initialize transformers model
        
        Popular models:
        - cardiffnlp/twitter-roberta-base-sentiment-latest (Twitter-specific, 3 classes)
        - distilbert-base-uncased-finetuned-sst-2-english (2 classes: pos/neg)
        - nlptown/bert-base-multilingual-uncased-sentiment (5 star rating)
        """
        super().__init__(f"Transformers-{model_name.split('/')[-1]}")
        if not HAS_TRANSFORMERS:
            raise ImportError("Transformers not installed. Install with: pip install transformers torch")
        self.model_name = model_name
        self.pipeline = None
        self.initialized = False
    
    def initialize(self):
        """Initialize transformers pipeline"""
        if not HAS_TRANSFORMERS:
            raise ImportError("Transformers not installed")
        
        try:
            # Use GPU if available, otherwise CPU
            device = 0 if torch.cuda.is_available() else -1
            
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model_name,
                device=device,
                truncation=True,
                max_length=512
            )
            self.initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize model {self.model_name}: {str(e)}")
    
    def predict(self, text: str) -> dict:
        """Predict sentiment using transformers model"""
        if not self.initialized:
            self.initialize()
        
        # Truncate text if too long
        text = text[:512]
        
        result = self.pipeline(text)[0]
        
        # Extract label and score
        label_raw = result['label'].lower()
        score = result['score']
        
        # Map to standard labels (model-specific, only positive and negative)
        if 'pos' in label_raw or 'positive' in label_raw:
            label = 'positive'
        elif 'neg' in label_raw or 'negative' in label_raw:
            label = 'negative'
        elif 'neutral' in label_raw or 'neu' in label_raw:
            # Map neutral to positive (or based on score)
            label = 'positive' if score > 0.5 else 'negative'
        else:
            # Default mapping based on score (only positive/negative)
            if score > 0.5:
                label = 'positive'
            else:
                label = 'negative'
        
        return {
            'label': label,
            'score': score,
            'raw_output': result
        }

