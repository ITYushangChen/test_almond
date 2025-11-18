"""
Flair Sentiment Analysis Model
Using Flair NLP library with pre-trained sentiment models
"""
try:
    from .base_model import SentimentModel
except ImportError:
    from base_model import SentimentModel

try:
    from flair.models import TextClassifier
    from flair.data import Sentence
    HAS_FLAIR = True
except ImportError:
    HAS_FLAIR = False

class FlairModel(SentimentModel):
    """Flair sentiment analysis model"""
    
    def __init__(self, model_name: str = "en-sentiment"):
        """
        Initialize Flair model
        
        Models:
        - en-sentiment (English sentiment, 2 classes: POSITIVE/NEGATIVE)
        """
        super().__init__(f"Flair-{model_name}")
        if not HAS_FLAIR:
            raise ImportError("Flair not installed. Install with: pip install flair")
        self.model_name = model_name
        self.classifier = None
        self.initialized = False
    
    def initialize(self):
        """Initialize Flair classifier"""
        if not HAS_FLAIR:
            raise ImportError("Flair not installed")
        
        try:
            self.classifier = TextClassifier.load(self.model_name)
            self.initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to load Flair model {self.model_name}: {str(e)}")
    
    def predict(self, text: str) -> dict:
        """Predict sentiment using Flair"""
        if not self.initialized:
            self.initialize()
        
        sentence = Sentence(text)
        self.classifier.predict(sentence)
        
        # Get prediction
        label_raw = sentence.labels[0].value  # POSITIVE or NEGATIVE
        score = sentence.labels[0].score
        
        # Map to standard labels (only positive and negative)
        if label_raw == 'POSITIVE':
            label = 'positive'
        elif label_raw == 'NEGATIVE':
            label = 'negative'
        else:
            # Default to positive if unknown
            label = 'positive'
            score = 0.6
        
        return {
            'label': label,
            'score': float(score),
            'raw_output': {
                'label_raw': label_raw,
                'score': float(score)
            }
        }

