"""
Base class for sentiment analysis models
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class SentimentModel(ABC):
    """Base class for all sentiment analysis models"""
    
    def __init__(self, name: str):
        self.name = name
        self.initialized = False
    
    @abstractmethod
    def initialize(self):
        """Initialize the model (load weights, etc.)"""
        pass
    
    @abstractmethod
    def predict(self, text: str) -> Dict[str, any]:
        """
        Predict sentiment for a single text
        
        Returns:
            dict with keys:
                - 'label': 'positive' or 'negative' (no neutral)
                - 'score': confidence score (0-1)
                - 'raw_output': raw model output (optional)
        """
        pass
    
    def predict_batch(self, texts: List[str]) -> List[Dict[str, any]]:
        """Predict sentiment for multiple texts"""
        if not self.initialized:
            self.initialize()
        
        results = []
        for text in texts:
            try:
                result = self.predict(text)
                results.append(result)
            except Exception as e:
                # Return positive as fallback (only positive/negative, no neutral)
                results.append({
                    'label': 'positive',
                    'score': 0.5,
                    'error': str(e)
                })
        return results
    
    def __str__(self):
        return self.name

