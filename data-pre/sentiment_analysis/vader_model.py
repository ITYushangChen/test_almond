"""
VADER Sentiment Analysis Model
Valence Aware Dictionary and sEntiment Reasoner - optimized for social media
"""
try:
    from .base_model import SentimentModel
except ImportError:
    from base_model import SentimentModel

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    HAS_VADER = True
except ImportError:
    HAS_VADER = False

class VaderModel(SentimentModel):
    """VADER sentiment analysis model"""
    
    def __init__(self):
        super().__init__("VADER")
        if not HAS_VADER:
            raise ImportError("VADER not installed. Install with: pip install vaderSentiment")
        self.analyzer = None
        self.initialized = False
    
    def initialize(self):
        """Initialize VADER analyzer"""
        if not HAS_VADER:
            raise ImportError("VADER not installed")
        self.analyzer = SentimentIntensityAnalyzer()
        self.initialized = True
    
    def predict(self, text: str) -> dict:
        """Predict sentiment using VADER"""
        if not self.initialized:
            self.initialize()
        
        scores = self.analyzer.polarity_scores(text)
        compound = scores['compound']  # Range: -1 to 1
        
        # Convert compound score to label (only positive and negative, no neutral)
        if compound >= 0:
            label = 'positive'
            score = 0.5 + (abs(compound) * 0.5)  # Normalize to 0.5-1.0
        else:
            label = 'negative'
            score = 0.5 + (abs(compound) * 0.5)  # Normalize to 0.5-1.0
        
        return {
            'label': label,
            'score': score,
            'raw_output': scores
        }

