"""
ScheduleAgent - Implement spaced repetition scheduling
"""

from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
from datetime import datetime, timedelta
import math


class ScheduleAgent(BaseAgent):
    """
    ScheduleAgent implements spaced repetition algorithm:
    - SM-2 algorithm variant
    - Adaptive scheduling based on performance
    - Priority-based review planning
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="ScheduleAgent", config=config)
        
        self.default_ef = config.get("default_ef", 2.5) if config else 2.5
        self.min_ef = config.get("min_ef", 1.3) if config else 1.3
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate next review schedule
        
        Args:
            input_data: {
                "card_id": str,
                "user_id": str,
                "score": float,
                "difficulty": str,
                "history": {
                    "ef": float (optional),
                    "interval_days": int (optional),
                    "repetitions": int (optional)
                }
            }
            
        Returns:
            {
                "card_id": str,
                "user_id": str,
                "next_due": str (ISO datetime),
                "interval_days": int,
                "ef": float,
                "repetitions": int
            }
        """
        self.validate_input(input_data, ["card_id", "user_id", "score"])
        
        card_id = input_data["card_id"]
        user_id = input_data["user_id"]
        score = input_data["score"]
        difficulty = input_data.get("difficulty", "M")
        history = input_data.get("history", {})
        
        # Get previous values
        ef = history.get("ef", self.default_ef)
        interval_days = history.get("interval_days", 0)
        repetitions = history.get("repetitions", 0)
        
        # Calculate new values using SM-2 algorithm
        new_ef, new_interval, new_reps = self._sm2_calculate(
            score, ef, interval_days, repetitions, difficulty
        )
        
        # Calculate next due date
        next_due = datetime.now() + timedelta(days=new_interval)
        
        result = {
            "card_id": card_id,
            "user_id": user_id,
            "next_due": next_due.isoformat(),
            "interval_days": new_interval,
            "ef": new_ef,
            "repetitions": new_reps
        }
        
        self.log_audit(
            action="schedule_review",
            input_summary=f"card={card_id}, score={score:.2f}",
            output_summary=f"next_interval={new_interval}days, ef={new_ef:.2f}"
        )
        
        return result
    
    def _sm2_calculate(self, score: float, ef: float, interval: int, 
                       repetitions: int, difficulty: str) -> tuple:
        """
        SM-2 algorithm calculation
        
        Returns:
            (new_ef, new_interval, new_repetitions)
        """
        # Convert score (0-1) to quality (0-5)
        quality = int(score * 5)
        
        # Adjust quality based on difficulty
        if difficulty == "H":
            quality = max(0, quality - 1)
        elif difficulty == "L":
            quality = min(5, quality + 1)
        
        # Update EF (Easiness Factor)
        new_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(self.min_ef, new_ef)
        
        # Calculate new interval and repetitions
        if quality < 3:
            # Failed: restart
            new_reps = 0
            new_interval = 1
        else:
            # Passed
            new_reps = repetitions + 1
            
            if new_reps == 1:
                new_interval = 1
            elif new_reps == 2:
                new_interval = 6
            else:
                new_interval = math.ceil(interval * new_ef)
        
        return new_ef, new_interval, new_reps
    
    def get_due_cards(self, user_id: str, review_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get cards that are due for review
        
        Args:
            user_id: User ID
            review_data: List of review records
            
        Returns:
            {
                "user_id": str,
                "due_today": int,
                "overdue": int,
                "cards": [card_id, ...]
            }
        """
        now = datetime.now()
        
        due_cards = []
        overdue_cards = []
        
        for record in review_data:
            if record.get("user_id") != user_id:
                continue
            
            next_due_str = record.get("next_due")
            if not next_due_str:
                due_cards.append(record["card_id"])
                continue
            
            next_due = datetime.fromisoformat(next_due_str)
            
            if next_due <= now:
                due_cards.append(record["card_id"])
                
                # Check if overdue (more than 1 day late)
                if next_due < now - timedelta(days=1):
                    overdue_cards.append(record["card_id"])
        
        return {
            "user_id": user_id,
            "due_today": len(due_cards),
            "overdue": len(overdue_cards),
            "cards": due_cards
        }

