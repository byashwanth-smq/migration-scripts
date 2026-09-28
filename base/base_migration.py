import os
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker
from migrations.base.db_config import DatabaseConfig
from migrations.helpers import get_asset_template_arr

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logger = logging.getLogger('migration_logger')
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()

class BaseMigration(ABC):
    def __init__(self):
        """Initialize the base migration class"""
        self.log_file = f'logs/migration_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log'
        self._setup_logger()
        
        source_db_url = DatabaseConfig.get_source_db_url()
        target_db_url = DatabaseConfig.get_target_db_url()

        logger.info(f"Initializing migration with source DB: {self._mask_connection_url(source_db_url)}")
        logger.info(f"Target DB: {self._mask_connection_url(target_db_url)}")

        self.source_engine = self._create_engine(source_db_url)
        self.target_engine = self._create_engine(target_db_url)
        
        self.source_session = self._create_session(self.source_engine)
        self.target_session = self._create_session(self.target_engine)
        
        self.migration_start_time = None
        self.migration_end_time = None
        
    def _setup_logger(self):
        if not logger.handlers:  # Prevent duplicate handlers
            os.makedirs('logs', exist_ok=True)
            file_handler = logging.FileHandler(self.log_file)
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

    @staticmethod
    def _mask_connection_url(url: str) -> str:
        """Mask sensitive information in connection URL for logging"""
        if '@' in url:
            # Only show the host and database name, mask credentials
            return url.split('@')[1]
        return url

    @staticmethod
    def _create_engine(db_url: str) -> Engine:
        """Create SQLAlchemy engine with proper configuration."""
        return create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800
        )

    @staticmethod
    def big_int_to_uuid(big_int):
        # Convert integer to 32-char hex string, padding with zeros
        hex_str = f"{big_int:032x}"
        hex_str = hex_str.zfill(32)
        
        # Set version and variant bits
        hex_str = hex_str[:12] + '4' + hex_str[13:]
        hex_str = hex_str[:16] + '8' + hex_str[17:]
        return str(uuid.UUID(hex_str))

    @staticmethod
    def uuid_to_big_int(uuid_str):
        # Convert UUID string to hex, removing hyphens and version/variant bits
        hex_str = uuid_str.replace('-', '')
        
        # Remove version nibble (position 12) and variant nibble (position 16)
        hex_str = hex_str[:12] + '0' + hex_str[13:16] + '0' + hex_str[17:]
        
        # Convert back to integer
        return int(hex_str, 16)

    @staticmethod
    def _create_session(engine: Engine) -> sessionmaker:
        """Create SQLAlchemy session maker."""
        return sessionmaker(bind=engine)
    
    def process_mapping_data(self, data: List[Dict], key_field: str, value_field: str) -> Dict:
        """Process mapping data into a dictionary.
        
        Args:
            data: List of dictionaries containing mapping data
            key_field: Field name to use as dictionary key
            value_field: Field name to use as dictionary value
        """
        mapping = {}
        for item in data:
            mapping[item[key_field]] = item[value_field]
        return mapping
    
    def process_multi_mapping_data(self, data: List[Dict], key_field: str, value_field: str) -> Dict:
        mapping = {}
        for item in data:
            key = item[key_field]
            value = item[value_field]
            if not value:
                continue
            if key in mapping:
                mapping[key].append(value)
            else:
                mapping[key] = [value]
        return mapping

    def get_asset_list(self, assets, id, type):
        if assets.get(id) and len(assets.get(id)):
            return get_asset_template_arr(
                asset_id_arr=assets.get(id), type=type
            )
        else:
            return None

    def _log_migration_start(self, migration_name: str) -> None:
        """Log migration start time and details."""
        self.migration_start_time = datetime.now(timezone.utc)
        logger.info(f"Starting migration: {migration_name} at {self.migration_start_time}")

    def _log(self, message):
        logger.error(message)

    def _log_migration_end(self, migration_name: str) -> None:
        """Log migration end time and duration."""
        self.migration_end_time = datetime.now(timezone.utc)
        duration = self.migration_end_time - self.migration_start_time
        logger.info(f"Completed migration: {migration_name} at {self.migration_end_time}")
        logger.info(f"Migration duration: {duration}")
        logger.info(f"Log file location: {os.path.abspath(self.log_file)}")

    def _get_source_data(self, query: Any) -> List[Dict[str, Any]]:
        """Execute query on source database and return results."""
        with self.source_session() as session:
            result = session.execute(query)
            data = [dict(zip(result.keys(), row)) for row in result.fetchall()]
            logger.info(f"Fetched {len(data)} records from source database")
            return data
    
    def _get_target_data(self, query: Any) -> List[Dict[str, Any]]:
        """Execute query on target database and return results."""
        with self.target_session() as session:
            result = session.execute(query)
            data = [dict(zip(result.keys(), row)) for row in result.fetchall()]
            logger.info(f"Fetched {len(data)} records from target database")
            return data

    def _batch_insert_data(self, table: Any, data: List[Dict[str, Any]], batch_size: int = 1000) -> None:
        """Insert data in batches to target database."""
        total_batches = (len(data) + batch_size - 1) // batch_size
        with self.target_session() as session:
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                session.bulk_insert_mappings(table, batch)
                session.commit()
                current_batch = (i // batch_size) + 1
                logger.info(f"Inserted batch {current_batch} of {total_batches} ({len(batch)} records)")
                
    def _batch_update_data(self, table: Any, data: List[Dict[str, Any]], batch_size: int = 1000) -> None:
        """Update data in batches to target database using partial updates."""
        total_batches = (len(data) + batch_size - 1) // batch_size
        with self.target_session() as session:
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                session.bulk_update_mappings(table, batch)
                session.commit()
                current_batch = (i // batch_size) + 1
                logger.info(f"Updated batch {current_batch} of {total_batches} ({len(batch)} records)")

    @abstractmethod
    def migrate(self) -> None:
        """Abstract method to be implemented by concrete migration classes."""
        pass

    def execute_migration(self) -> None:
        """Execute the migration with proper logging and error handling."""
        migration_name = self.__class__.__name__
        try:
            self._log_migration_start(migration_name)
            self.migrate()
            self._log_migration_end(migration_name)
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}", exc_info=True)
            raise
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("Cleaning up database connections")
        self.source_engine.dispose()
        self.target_engine.dispose()