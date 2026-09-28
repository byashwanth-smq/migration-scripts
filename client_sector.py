import uuid
from migrations.constants import POSTGRES_TABLES, ALLOY_TABLES
from typing import List, Dict, Any
from migrations.base.base_migration import BaseMigration
from models.db.sector_client_site_association import SectorClientSiteAssociation
from datetime import datetime, timezone
from sqlalchemy import text

class ClientSectorAssociationMigration(BaseMigration):

    def __init__(self):
        super().__init__()
        DEFAULT_ADMIN_ID = 42784196460024914
        self.DEFAULT_ADMIN_UUID = self.big_int_to_uuid(DEFAULT_ADMIN_ID)
        self.execute_migration()

    def fetch_sector_mappings(self):
        query = text(f"""
            SELECT sector_id, sector_key
            FROM {ALLOY_TABLES['SECTOR']}
        """)
        return self._get_target_data(query)

    def sector_mappings(self):
        sectors = self.fetch_sector_mappings()
        return self.process_mapping_data(sectors, 'sector_id', 'sector_key')

    def fetch_client_site_data(self) -> List[Dict[str, Any]]:
        query = text(f"""
            SELECT controldesk$clientid as clientid, controldesk$categoryid as categoryid
            FROM {POSTGRES_TABLES['CLIENT_CATEGORY']}
        """)
        return self._get_source_data(query)

    def migrate(self) -> None:
        sector_ids = self.sector_mappings()
        client_site_data = self.fetch_client_site_data()
        migrated_list = []

        for record in client_site_data:
            sector_id = self.big_int_to_uuid(record['categoryid'])
            client_id = self.big_int_to_uuid(record['clientid'])

            if uuid.UUID(sector_id) not in sector_ids:
                self._log(f'Skipping category id {record['categoryid']} not found in the sector table alloy db')
                continue

            mydict = dict()
            mydict['client_site_id'] = uuid.uuid4()
            mydict['sector_id'] = sector_id
            mydict['client_id'] = client_id
            mydict['site_id'] = None
            mydict['modified_on'] = datetime.now(timezone.utc)
            mydict['modified_by'] = self.DEFAULT_ADMIN_UUID

            migrated_list.append(mydict)

        self._batch_insert_data(SectorClientSiteAssociation, migrated_list)

if __name__ == "__main__":
    ClientSectorAssociationMigration()