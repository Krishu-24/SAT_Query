"""
ModelRegistry — Load/unload/get models with automatic VRAM management.

Handles the RTX 4060 (8GB) constraint by loading ONE major model at a time.
Strategy: Load → Infer → (auto-unload if needed) → Load next.
"""

import gc
from loguru import logger


class ModelRegistry:
    """
    Central registry for all model wrappers.

    Models are registered with a lazy loader function and VRAM estimate.
    When a model is requested, the registry:
      1. Checks if it's already loaded
      2. If not, ensures enough VRAM by unloading other models
      3. Loads the model via its loader function
      4. Returns the loaded model instance
    """

    def __init__(self):
        self._models: dict = {}      # name → loaded model instance
        self._configs: dict = {}     # name → {"loader": fn, "vram_gb": float}

    def register(self, name: str, loader_fn, vram_gb: float = 0.0):
        """
        Register a model with a lazy loader.

        Args:
            name: Unique model identifier (e.g. "rs_vlm", "grounding_dino").
            loader_fn: Callable that returns a model instance when called.
            vram_gb: Estimated VRAM usage in GB.
        """
        self._configs[name] = {"loader": loader_fn, "vram_gb": vram_gb}
        logger.debug(f"Registered model: {name} (~{vram_gb} GB)")

    def get(self, name: str):
        """
        Get a loaded model instance. Loads it if not already loaded.

        Auto-unloads other models if VRAM is insufficient.

        Args:
            name: Model identifier.

        Returns:
            Loaded model wrapper instance.

        Raises:
            ValueError: If model name is not registered.
        """
        if name not in self._configs:
            raise ValueError(
                f"Unknown model: '{name}'. "
                f"Registered models: {list(self._configs.keys())}"
            )

        if name not in self._models:
            self._load(name)

        return self._models[name]

    def _load(self, name: str):
        """Load a model, ensuring VRAM is available first."""
        config = self._configs[name]
        needed_gb = config["vram_gb"]

        # Free up VRAM if needed
        self._ensure_vram(needed_gb, exclude=name)

        logger.info(f"Loading model: {name} (~{needed_gb} GB)")
        try:
            self._models[name] = config["loader"]()
            logger.info(f"Model loaded: {name}")
        except Exception as e:
            logger.error(f"Failed to load model {name}: {e}")
            raise

    def _ensure_vram(self, needed_gb: float, exclude: str = ""):
        """Unload models until enough VRAM is free."""
        try:
            import torch
            if not torch.cuda.is_available():
                return

            free = (
                torch.cuda.get_device_properties(0).total_mem
                - torch.cuda.memory_allocated()
            ) / 1e9

            while free < needed_gb and self._models:
                # Unload the oldest loaded model (FIFO)
                candidates = [k for k in self._models if k != exclude]
                if not candidates:
                    break
                oldest = candidates[0]
                self.unload(oldest)
                free = (
                    torch.cuda.get_device_properties(0).total_mem
                    - torch.cuda.memory_allocated()
                ) / 1e9

        except ImportError:
            # No torch — skip VRAM management (CPU mode)
            pass

    def unload(self, name: str):
        """Unload a model and free its resources."""
        if name in self._models:
            del self._models[name]
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            logger.info(f"Unloaded model: {name}")

    def unload_all(self):
        """Unload all loaded models."""
        for name in list(self._models.keys()):
            self.unload(name)

    def list_loaded(self) -> list[str]:
        """Return names of currently loaded models."""
        return list(self._models.keys())

    def list_all(self) -> list[dict]:
        """Return info about all registered models."""
        return [
            {
                "name": name,
                "loaded": name in self._models,
                "vram_gb": config["vram_gb"],
            }
            for name, config in self._configs.items()
        ]
