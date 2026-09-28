from os import getenv
from dotenv import load_dotenv
from typing import Dict, Any

# Load variables from .env file
load_dotenv()

class DatabaseConfig:
    @staticmethod
    def get_source_db_config() -> Dict[str, Any]:
        """
        Get source database (Postgres) configuration from environment/secrets.
        """
        # You should implement proper secret management here
        return {
            'host': getenv('SOURCE_DB_HOST'),
            'port': getenv('SOURCE_DB_PORT'),
            'database': getenv('SOURCE_DB_NAME'),
            'user': getenv('SOURCE_DB_USERNAME'),
            'password': getenv('SOURCE_DB_PASSWORD')
        }

    @staticmethod
    def get_target_db_config() -> Dict[str, Any]:
        """
        Get target database (AlloyDB) configuration from environment/secrets.
        """
        return {
            'host': getenv('TARGET_DB_HOST'),
            'port': getenv('TARGET_DB_PORT'),
            'database': getenv('TARGET_DB_NAME'),
            'user': getenv('TARGET_DB_USERNAME'),
            'password': getenv('TARGET_DB_PASSWORD')
        }

    @staticmethod
    def get_source_db_url() -> str:
        """
        Construct source database URL.
        """
        config = DatabaseConfig.get_source_db_config()
        return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

    @staticmethod
    def get_target_db_url() -> str:
        """
        Construct target database URL.
        """
        config = DatabaseConfig.get_target_db_config()
        return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"