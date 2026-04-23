"""
Extracted from Entreprise Manager to handle document validity checks
and valid document counting.
"""

from datetime import datetime, timezone
from freezegun import freeze_time
from uc3m_consulting.project_document import ProjectDocument
from uc3m_consulting.enterprise_management_exception import EnterpriseManagementException


class document_info:
    """
    Helper class for counting valid docs from Entreprise Manager
    """
    @staticmethod
    def count_valid_docs_for_date(documents_data, date_str):
        """Internal helper to count documents with valid signatures (2.1a)"""
        count = 0
        for document in documents_data:
            registration_timestamp = document["register_date"]
            formatted_doc_date = datetime.fromtimestamp(registration_timestamp).strftime("%d/%m/%Y")
            #converting timestamp to desired dd/mm/yyyy format
            if formatted_doc_date == date_str:
                document_datetime = datetime.fromtimestamp(registration_timestamp, tz=timezone.utc)
                with freeze_time(document_datetime):
                    # Integrity check
                    project_doc = ProjectDocument(document["project_id"], document["file_name"])
                    if project_doc.document_signature == document["document_signature"]:
                        count += 1
                    else:
                        raise EnterpriseManagementException("Inconsistent document signature")
        return count
