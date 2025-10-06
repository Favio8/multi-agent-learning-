"""
Configuration management module
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration manager"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to YAML config file
        """
        if config_path is None:
            config_path = Path(__file__).parent / "settings.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._apply_env_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def _apply_env_overrides(self):
        """Override config values with environment variables"""
        # API Keys
        if openai_key := os.getenv("OPENAI_API_KEY"):
            self._config.setdefault("models", {}).setdefault("llm", {})["api_key"] = openai_key
        
        if anthropic_key := os.getenv("ANTHROPIC_API_KEY"):
            self._config.setdefault("models", {}).setdefault("llm", {})["anthropic_key"] = anthropic_key
        
        # Database
        if neo4j_uri := os.getenv("NEO4J_URI"):
            self._config.setdefault("database", {}).setdefault("neo4j", {})["uri"] = neo4j_uri
        
        if neo4j_password := os.getenv("NEO4J_PASSWORD"):
            self._config.setdefault("database", {}).setdefault("neo4j", {})["password"] = neo4j_password
        
        # Paths
        if data_path := os.getenv("DATA_PATH"):
            self._config.setdefault("paths", {})["data_dir"] = data_path
        
        if logs_path := os.getenv("LOGS_PATH"):
            self._config.setdefault("paths", {})["logs_dir"] = logs_path
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key
        
        Args:
            key: Configuration key (e.g., "agents.content.min_section_length")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for specific agent"""
        return self.get(f"agents.{agent_name}", {})
    
    def get_all(self) -> Dict[str, Any]:
        """Get complete configuration"""
        return self._config.copy()
    
    def ensure_directories(self):
        """Ensure all required directories exist"""
        paths = self.get("paths", {})
        
        for path_key, path_value in paths.items():
            path = Path(path_value)
            path.mkdir(parents=True, exist_ok=True)


# Global config instance
_config_instance = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get global configuration instance
    
    Args:
        config_path: Path to config file (only used on first call)
        
    Returns:
        Config instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = Config(config_path)
    
    return _config_instance


def reload_config(config_path: Optional[str] = None):
    """Reload configuration"""
    global _config_instance
    _config_instance = Config(config_path)
    return _config_instance

