from migrations.constants import POSTGRES_TABLES
from typing import List, Dict, Any
from migrations.base.base_migration import BaseMigration
from models.db.section import Section;
from datetime import datetime, timezone
from sqlalchemy import text

class SectionMigration(BaseMigration):

    def __init__(self):
        super().__init__()
        DEFAULT_ADMIN_ID = 42784196460024914
        self.DEFAULT_ADMIN_UUID = self.big_int_to_uuid(DEFAULT_ADMIN_ID)
        self.execute_migration()

    def fetch_section_checklist_data(self) -> List[Dict[str, Any]]:
        """Fetch section checklist data using raw SQL query."""
        query = text(f"""
            SELECT S.*, SC.controldesk$checklistid as checklistid 
            FROM {POSTGRES_TABLES['SECTION']} as S
            INNER JOIN {POSTGRES_TABLES['SECTION_CHECKLIST']} as SC
            ON S.id = SC.controldesk$sectionid
        """)
        return self._get_source_data(query)

    def migrate(self) -> None:
        """Execute the migration."""
        section_checklist_data = self.fetch_section_checklist_data()
        migrated_section_list = []

        for record in section_checklist_data:
            section_name = record['sectionname']
            if not section_name:
                self._log(f'section id {record['id']} not having proper section name {section_name}')
                continue

            mydict = dict()
            mydict['section_id'] = self.big_int_to_uuid(record['id'])
            mydict['section_name'] = section_name
            mydict['weight_per'] = record['weightper']
            mydict['section_index'] = record['index']
            mydict['total_score'] = record['totalscore']
            mydict['has_subsection'] = record['issubsection']
            mydict['checklist_id'] = self.big_int_to_uuid(record['checklistid'])
            mydict['modified_on'] = record['changeddate']
            mydict['modified_by'] = self.DEFAULT_ADMIN_UUID
            migrated_section_list.append(mydict)
        self._batch_insert_data(Section, migrated_section_list)

if __name__ == "__main__":
    SectionMigration()