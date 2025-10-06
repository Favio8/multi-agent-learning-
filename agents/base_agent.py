"""
Base Agent Class
All agents inherit from this base class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime


class BaseAgent(ABC):
    """
    Base class for all agents in the system
    
    Attributes:
        agent_id: Unique identifier for the agent
        logger: Logger instance for this agent
    """
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base agent
        
        Args:
            agent_id: Unique identifier for the agent
            config: Configuration dictionary for the agent
        """
        self.agent_id = agent_id
        self.config = config or {}
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for this agent"""
        logger = logging.getLogger(f"agents.{self.agent_id}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.agent_id} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method that each agent must implement
        
        Args:
            input_data: Input data for the agent to process
            
        Returns:
            Processed output data
        """
        pass
    
    def validate_input(self, input_data: Dict[str, Any], required_fields: list) -> bool:
        """
        Validate that input data contains all required fields
        
        Args:
            input_data: Input data to validate
            required_fields: List of required field names
            
        Returns:
            True if valid, raises ValueError otherwise
        """
        missing_fields = [field for field in required_fields if field not in input_data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        return True
    
    def log_audit(self, action: str, input_summary: str, output_summary: str):
        """
        Log audit trail for this agent's action
        
        Args:
            action: Action performed
            input_summary: Summary of input data
            output_summary: Summary of output data
        """
        self.logger.info(
            f"Action: {action} | Input: {input_summary} | Output: {output_summary}"
        )

