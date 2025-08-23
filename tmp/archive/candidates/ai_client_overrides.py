# =============================================================================
# ai_client.py (patched for Step 3.9)
# Adds provider pricing overrides from config/provider_pricing_overrides.yaml
# Author: G. Rapson | GR-Analysis
# =============================================================================

import yaml
import os
import logging

class AIClient:
    def __init__(self, config_path: str, project: str):
        self.project = project
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # Load overrides
        self.overrides = self._load_pricing_overrides()
        self.clients = {}
        self.token_usage = {
            provider: {model: 0 for model in details.get("models", {})}
            for provider, details in self.config.get("apis", {}).items()
        }

        self._apply_pricing_overrides()
        self.setup_clients()

    def _load_pricing_overrides(self) -> dict:
        path = os.path.join("config", "provider_pricing_overrides.yaml")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _apply_pricing_overrides(self):
        """Apply overrides to provider configs where not null"""
        for provider, models in self.overrides.items():
            if provider not in self.config.get("apis", {}):
                continue
            for model, values in models.items():
                if model not in self.config["apis"][provider]["models"]:
                    continue
                for key, val in values.items():
                    if val is not None:
                        self.config["apis"][provider]["models"][model][key] = val

    def setup_clients(self):
        # (Placeholder – unchanged client setup logic)
        pass
