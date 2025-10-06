"""
EvalAgent - Evaluate user responses and update mastery
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from datetime import datetime


class EvalAgent(BaseAgent):
    """
    EvalAgent evaluates user answers:
    - Score responses (exact match + semantic similarity)
    - Classify error types
    - Update difficulty and mastery
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="EvalAgent", config=config)
        
        self.semantic_threshold = config.get("semantic_threshold", 0.7) if config else 0.7
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate user response
        
        Args:
            input_data: {
                "user_id": str,
                "card_id": str,
                "card": {...},  # full card data
                "response": str,
                "latency_ms": int
            }
            
        Returns:
            {
                "user_id": str,
                "card_id": str,
                "score": float (0-1),
                "is_correct": bool,
                "error_type": str (optional),
                "difficulty": str,
                "feedback": str,
                "timestamp": str
            }
        """
        self.validate_input(input_data, ["user_id", "card_id", "card", "response"])
        
        user_id = input_data["user_id"]
        card_id = input_data["card_id"]
        card = input_data["card"]
        response = input_data["response"]
        latency_ms = input_data.get("latency_ms", 0)
        
        card_type = card.get("type")
        correct_answer = card.get("answer")
        
        # Score the response
        score, is_correct = self._score_response(response, correct_answer, card_type)
        
        # Classify error if incorrect
        error_type = None
        if not is_correct:
            error_type = self._classify_error(response, card)
        
        # Generate feedback
        feedback = self._generate_feedback(is_correct, correct_answer, error_type)
        
        result = {
            "user_id": user_id,
            "card_id": card_id,
            "score": score,
            "is_correct": is_correct,
            "error_type": error_type,
            "difficulty": card.get("difficulty", "M"),
            "feedback": feedback,
            "latency_ms": latency_ms,
            "timestamp": datetime.now().isoformat()
        }
        
        self.log_audit(
            action="evaluate_response",
            input_summary=f"user={user_id}, card={card_id}",
            output_summary=f"score={score:.2f}, correct={is_correct}"
        )
        
        return result
    
    def _score_response(self, response: str, correct_answer: str, card_type: str) -> tuple:
        """
        Score user response
        
        Returns:
            (score: float, is_correct: bool)
        """
        response = response.strip().lower()
        correct_answer = correct_answer.strip().lower()
        
        if card_type == "mcq":
            # Exact match for MCQ
            is_correct = response == correct_answer
            score = 1.0 if is_correct else 0.0
            
        elif card_type == "cloze":
            # Exact or close match for cloze
            is_correct = self._fuzzy_match(response, correct_answer)
            score = 1.0 if is_correct else 0.0
            
        elif card_type == "short":
            # Semantic + keyword matching for short answer
            score = self._semantic_score(response, correct_answer)
            is_correct = score >= self.semantic_threshold
            
        else:
            # Default: exact match
            is_correct = response == correct_answer
            score = 1.0 if is_correct else 0.0
        
        return score, is_correct
    
    def _fuzzy_match(self, response: str, answer: str) -> bool:
        """Check if response is close to answer"""
        # Simple fuzzy matching
        # TODO: Use better fuzzy matching (e.g., fuzzywuzzy)
        
        # Remove punctuation and extra spaces
        import re
        response = re.sub(r'[^\w\s]', '', response)
        answer = re.sub(r'[^\w\s]', '', answer)
        
        # Check if words overlap significantly
        response_words = set(response.split())
        answer_words = set(answer.split())
        
        if not answer_words:
            return False
        
        overlap = len(response_words & answer_words) / len(answer_words)
        return overlap >= 0.8
    
    def _semantic_score(self, response: str, answer: str) -> float:
        """Calculate semantic similarity score"""
        # TODO: Use sentence embeddings (sentence-transformers)
        # For now, use simple keyword overlap
        
        import re
        response_words = set(re.findall(r'\w+', response.lower()))
        answer_words = set(re.findall(r'\w+', answer.lower()))
        
        if not answer_words:
            return 0.0
        
        # Jaccard similarity
        intersection = len(response_words & answer_words)
        union = len(response_words | answer_words)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _classify_error(self, response: str, card: Dict[str, Any]) -> str:
        """Classify the type of error"""
        # TODO: Implement sophisticated error classification
        
        if not response or len(response.strip()) < 2:
            return "no_answer"
        
        card_type = card.get("type")
        choices = card.get("choices", [])
        
        if card_type == "mcq" and response in [c.lower() for c in choices]:
            return "concept_confusion"
        
        # Check if response is completely off-topic
        answer_words = set(card.get("answer", "").lower().split())
        response_words = set(response.lower().split())
        
        if not (answer_words & response_words):
            return "completely_wrong"
        
        return "partial_understanding"
    
    def _generate_feedback(self, is_correct: bool, correct_answer: str, 
                          error_type: Optional[str]) -> str:
        """Generate feedback for the user"""
        if is_correct:
            return "正确！"
        
        feedback = f"不正确。正确答案是：{correct_answer}"
        
        if error_type == "concept_confusion":
            feedback += " 提示：注意区分相关概念的细微差别。"
        elif error_type == "partial_understanding":
            feedback += " 提示：你的理解有一定基础，但还需要更准确的表述。"
        elif error_type == "no_answer":
            feedback += " 建议：先复习相关内容再作答。"
        
        return feedback

