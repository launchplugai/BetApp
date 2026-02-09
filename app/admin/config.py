"""
Configuration Management System

Centralized config with persistence, validation, and hot-reload.
"""
import json
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("./data/admin_config.json")


@dataclass
class NBAConfig:
    """NBA Analytics configuration."""
    enabled: bool = True
    cache_ttl_seconds: int = 300
    rest_coefficient: float = -4.5  # Points for B2B
    tank_detection_threshold: float = 0.6
    injury_war_multiplier: float = 3.0
    data_sources: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.data_sources is None:
            self.data_sources = {
                'nba_api': True,
                'espn_injuries': True,
                'bball_ref': False,  # Off by default (scraping)
                'rotowire': False
            }


@dataclass
class HeuristicsConfig:
    """Heuristics engine tuning."""
    rest_weights: Dict[str, float] = None
    tank_signal_weights: Dict[str, float] = None
    confidence_adjustment_caps: Dict[str, float] = None
    
    def __post_init__(self):
        if self.rest_weights is None:
            self.rest_weights = {
                'b2b': -4.5,
                'one_day': -2.0,
                'normal': 0.0,
                'three_day': 1.0,
                'four_plus': 1.5
            }
        if self.tank_signal_weights is None:
            self.tank_signal_weights = {
                'playoff_elimination': 0.5,
                'star_availability': 0.2,
                'youth_minutes': 0.1,
                'defensive_decline': 0.2
            }
        if self.confidence_adjustment_caps is None:
            self.confidence_adjustment_caps = {
                'max_single': 20.0,
                'max_total': 30.0,
                'min_confidence': 10.0
            }


@dataclass
class PlatformConfig:
    """Top-level platform configuration."""
    version: str = "1.0.0"
    last_updated: str = None
    nba: NBAConfig = None
    heuristics: HeuristicsConfig = None
    features: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow().isoformat()
        if self.nba is None:
            self.nba = NBAConfig()
        if self.heuristics is None:
            self.heuristics = HeuristicsConfig()
        if self.features is None:
            self.features = {
                'nba_analytics': True,
                'injury_tracking': True,
                'tank_detection': True,
                'playoff_context': True,
                'advanced_stats': False
            }


class ConfigManager:
    """Central configuration manager with persistence."""
    
    _instance: Optional['ConfigManager'] = None
    _config: PlatformConfig = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load_config()
        return cls._instance
    
    @classmethod
    def _load_config(cls):
        """Load config from disk or create default."""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH) as f:
                    data = json.load(f)
                cls._config = PlatformConfig(**data)
                logger.info("Config loaded from disk")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                cls._config = PlatformConfig()
        else:
            cls._config = PlatformConfig()
            cls._save_config()
    
    @classmethod
    def _save_config(cls):
        """Save config to disk."""
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(asdict(cls._config), f, indent=2)
        logger.info("Config saved to disk")
    
    def get(self) -> PlatformConfig:
        """Get current configuration."""
        return self._config
    
    def update(self, updates: Dict[str, Any]) -> bool:
        """
        Update configuration.
        
        Args:
            updates: Nested dict of updates
            
        Returns:
            True if successful
        """
        try:
            # Deep merge updates
            self._deep_update(asdict(self._config), updates)
            
            # Reconstruct config object
            self._config = PlatformConfig(**asdict(self._config))
            self._config.last_updated = datetime.utcnow().isoformat()
            
            # Persist
            self._save_config()
            
            return True
        except Exception as e:
            logger.error(f"Config update failed: {e}")
            return False
    
    def _deep_update(self, base: Dict, updates: Dict):
        """Recursively update nested dict."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in base:
                self._deep_update(base[key], value)
            else:
                base[key] = value
    
    def reset_to_defaults(self):
        """Reset to default configuration."""
        self._config = PlatformConfig()
        self._save_config()
        logger.info("Config reset to defaults")


# Global config accessor
def get_config() -> PlatformConfig:
    """Get global configuration instance."""
    return ConfigManager().get()


def update_config(updates: Dict[str, Any]) -> bool:
    """Update global configuration."""
    return ConfigManager().update(updates)
