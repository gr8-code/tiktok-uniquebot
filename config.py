import os
from dataclasses import dataclass

@dataclass
class BotConfig:
    # Токен берём из переменных окружения (для безопасности)
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
    
    TEMP_DIR: str = "temp"
    MAX_UNIQUALIZATIONS: int = 50
    MAX_FILE_SIZE: int = 20 * 1024 * 1024

config = BotConfig()

if not os.path.exists(config.TEMP_DIR):
    os.makedirs(config.TEMP_DIR)
