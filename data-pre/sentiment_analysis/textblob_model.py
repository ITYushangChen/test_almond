"""
TextBlob Sentiment Analysis Model
Simple rule-based sentiment analysis using TextBlob
"""
try:
    from .base_model import SentimentModel
except ImportError:
    from base_model import SentimentModel

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False

class TextBlobModel(SentimentModel):
    """TextBlob sentiment analysis model"""
    
    def __init__(self):
        super().__init__("TextBlob")
        if not HAS_TEXTBLOB:
            raise ImportError("TextBlob not installed. Install with: pip install textblob")
        self.initialized = True
    
    def initialize(self):
        """TextBlob doesn't require initialization"""
        self.initialized = True
    
    def predict(self, text: str) -> dict:
        """Predict sentiment using TextBlob"""
        if not self.initialized:
            self.initialize()
        
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # Range: -1 to 1
        
        # Convert polarity to label (only positive and negative, no neutral)
        if polarity > 0:
            label = 'positive'
            score = min(0.5 + (abs(polarity) * 0.5), 1.0)  # Normalize to 0.5-1.0
        else:
            label = 'negative'
            score = min(0.5 + (abs(polarity) * 0.5), 1.0)  # Normalize to 0.5-1.0
        
        return {
            'label': label,
            'score': score,
            'raw_output': {
                'polarity': polarity,
                'subjectivity': blob.sentiment.subjectivity
            }
        }

