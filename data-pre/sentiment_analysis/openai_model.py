"""
OpenAI GPT-based Sentiment Analysis Model
Using OpenAI API for sentiment analysis
"""
import os
import sys
try:
    from .base_model import SentimentModel
except ImportError:
    from base_model import SentimentModel

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

try:
    import openai
    from config import Config
    HAS_OPENAI = bool(Config.OPENAI_API_KEY) if hasattr(Config, 'OPENAI_API_KEY') and Config.OPENAI_API_KEY else False
except ImportError:
    HAS_OPENAI = False
except Exception:
    HAS_OPENAI = False

class OpenAIModel(SentimentModel):
    """OpenAI GPT-based sentiment analysis model"""
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        Initialize OpenAI model
        
        Models:
        - gpt-3.5-turbo (faster, cheaper)
        - gpt-4o (most accurate, optimized)
        - gpt-4o-mini (faster than gpt-4o, more accurate than 3.5)
        """
        super().__init__(f"OpenAI-{model}")
        if not HAS_OPENAI:
            raise ImportError("OpenAI not configured. Set OPENAI_API_KEY in backend/.env")
        self.model_name = model
        self.client = None
        self.initialized = False
    
    def initialize(self):
        """Initialize OpenAI client"""
        if not HAS_OPENAI:
            raise ImportError("OpenAI not configured")
        
        try:
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            self.initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def predict(self, text: str) -> dict:
        """Predict sentiment using OpenAI"""
        if not self.initialized:
            self.initialize()
        
        # Truncate text to avoid token limits
        text = text[:1000]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sentiment analysis assistant. Classify the sentiment of the given text as 'positive' or 'negative' (no neutral). Only respond with one word: positive or negative."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.3,
                max_tokens=10
            )
            
            result_text = response.choices[0].message.content.strip().lower()
            
            # Parse response (only positive and negative, no neutral)
            if 'positive' in result_text:
                label = 'positive'
                score = 0.8  # High confidence for GPT
            elif 'negative' in result_text:
                label = 'negative'
                score = 0.8
            elif 'neutral' in result_text:
                # Map neutral to positive (default)
                label = 'positive'
                score = 0.6
            else:
                # Default to positive if unclear
                label = 'positive'
                score = 0.6
            
            return {
                'label': label,
                'score': score,
                'raw_output': {
                    'response': result_text,
                    'model': self.model_name
                }
            }
        except Exception as e:
            # Return positive as fallback (only positive/negative, no neutral)
            return {
                'label': 'positive',
                'score': 0.5,
                'error': str(e)
            }

