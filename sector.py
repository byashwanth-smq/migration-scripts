from sqlalchemy import text
from datetime import datetime, timezone
from migrations.base.base_migration import BaseMigration
from models.db.sector import Sector;
from typing import List, Dict, Any
from migrations.constants import POSTGRES_TABLES

class SectorMigration(BaseMigration):
        
    def __init__(self):
        super().__init__()
        DEFAULT_ADMIN_ID = 42784196460024914
        self.DEFAULT_ADMIN_UUID = self.big_int_to_uuid(DEFAULT_ADMIN_ID)
        self.execute_migration()

    def fetch_category_data(self) -> List[Dict[str, Any]]:
        """Fetch category data using raw SQL query."""
        query = text(f"""
            SELECT * FROM {POSTGRES_TABLES['CATEGORY']}
        """)
        return self._get_source_data(query)
    
    def fetch_category_country(self):
        """Fetch category_country data using raw SQL query."""
        query = text(f"""
            SELECT * FROM {POSTGRES_TABLES['CATEGORY_COUNTRY']}
        """)
        return self._get_source_data(query)
    
    def get_category_country_mappings(self):
        category_country = self.fetch_category_country()
        return self.process_mapping_data(category_country, 'controldesk$categoryid', 'controldesk$countryid')
    
    def get_country_id(self, category_country_mappings, category_id):
        if category_id:
            if category_id in category_country_mappings:
                country_uuid =  self.big_int_to_uuid(category_country_mappings[category_id])
                return country_uuid
            
    def get_category_key(self, name, key):
        if key:
            return key
        else:
            formatted_key = name.replace(" ", "").lower()
            return formatted_key

    def migrate(self) -> None:
        """Execute the migration."""
        category_country_mappings = self.get_category_country_mappings()
        category_data = self.fetch_category_data()
        migrated_sector_list = []
        
        for category in category_data:
            if not self.get_country_id(category_country_mappings, category['id']):
                self._log(f'Skipping {category['id']} not available in category country association table')
                continue

            category_key = self.get_category_key(name=category['name'], key=category['categorykey'])
            mydict = dict()
            mydict['sector_id'] = self.big_int_to_uuid(category['id'])
            mydict['name'] = category['name']
            mydict['sector_key'] = category_key
            mydict['description'] = category['description']
            mydict['target'] = category['target']
            mydict['is_active'] = category['isactive']
            mydict['country_id'] = self.get_country_id(category_country_mappings, category['id'])
            mydict['modified_on'] = datetime.now(timezone.utc)
            mydict['modified_by'] = self.DEFAULT_ADMIN_UUID
            migrated_sector_list.append(mydict)
        self._batch_insert_data(Sector, migrated_sector_list)

if __name__ == "__main__":
    SectorMigration()