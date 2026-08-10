from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    data_dir: str = os.environ.get("CB_DATA_DIR", "/data")
    exec_timeout_s: float = float(os.environ.get("CB_EXEC_TIMEOUT_S", "8"))
    mem_mb: int = int(os.environ.get("CB_MEM_MB", "256"))
    allow_origins: str = os.environ.get(
        "CB_ALLOW_ORIGINS",
        "http://127.0.0.1:8188,http://localhost:8188,*",
    )


settings = Settings()
