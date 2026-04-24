"""
Refactored to break up validation and document info into two
helper classes to reduce divergent changes and large classes.
"""

#import re
import json

from datetime import datetime, timezone
#from freezegun import freeze_time
from uc3m_consulting.enterprise_project import EnterpriseProject
from uc3m_consulting.enterprise_management_exception import EnterpriseManagementException
from uc3m_consulting.enterprise_manager_config import (PROJECTS_STORE_FILE,
                                                       TEST_DOCUMENTS_STORE_FILE,
                                                       TEST_NUMDOCS_STORE_FILE)
#from uc3m_consulting.project_document import ProjectDocument
from uc3m_consulting.project_valid import project_valid
from uc3m_consulting.document_info import document_info


class EnterpriseManager:
    """Class for providing the methods for managing the orders"""

    __instance = None

    def __new__(cls):
        """Implementation of the Singleton pattern (Step 3.1)"""
        if EnterpriseManager.__instance is None:
            EnterpriseManager.__instance = super(EnterpriseManager, cls).__new__(cls)
        return EnterpriseManager.__instance

    #removed to increase pylint score
    # def __init__(self):
    #     """
    #     Constructor remains, but since __new__ handles the instance,
    #     we can use this to initialize values only once if needed.
    #     """
    #     pass

    @staticmethod
    def _load_json_data(file_path):
        """Helper to unify JSON loading logic and error handling (2.1b)"""
        try:
            with open(file_path, "r", encoding="utf-8", newline="") as file:
                return json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex

    @staticmethod
    def _save_json_data(file_path, data):
        """Helper to unify JSON saving logic and error handling (2.1b)"""
        try:
            with open(file_path, "w", encoding="utf-8", newline="") as file:
                json.dump(data, file, indent=2)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file  or file path") from ex

    @staticmethod
    def _check_if_project_exists(projects_list, new_project):
        """Internal helper to check for duplicate projects (2.1a)"""
        for existing_project in projects_list:
            if existing_project == new_project.to_json():
                raise EnterpriseManagementException("Duplicated project in projects list")


    def register_project(self,
                         company_cif: str,
                         project_acronym: str,
                         project_description: str,
                         department: str,
                         date: str,
                         budget: str):
        """registers a new project"""
        project_valid.validate_cif(company_cif)
        project_valid.validate_project_params(project_acronym, project_description, department)
        project_valid.validate_starting_date(date)
        project_valid.validate_budget(budget)

        new_project = EnterpriseProject(company_cif=company_cif,
                                        project_acronym=project_acronym,
                                        project_description=project_description,
                                        department=department,
                                        starting_date=date,
                                        project_budget=budget)

        projects_list = EnterpriseManager._load_json_data(PROJECTS_STORE_FILE)
        EnterpriseManager._check_if_project_exists(projects_list, new_project)

        projects_list.append(new_project.to_json())
        EnterpriseManager._save_json_data(PROJECTS_STORE_FILE, projects_list)

        return new_project.project_id

    def find_docs(self, date_str):
        """
        Generates a JSON report counting valid documents for a specific date.

        Checks cryptographic hashes and timestamps to ensure historical data integrity.
        Saves the output to 'result.json'.

        Args:
            date_str (str): date to query.

        Returns:
            number of documents found if report is successfully generated and saved.

        Raises:
            EnterpriseManagementException: On invalid date, file IO errors,
                missing data, or cryptographic integrity failure.
        """

        project_valid.validate_date_format(date_str)
        # open documents
        documents_data = EnterpriseManager._load_json_data(TEST_DOCUMENTS_STORE_FILE)
        valid_document_count = document_info.count_valid_docs_for_date(documents_data, date_str)

        if valid_document_count == 0:
            raise EnterpriseManagementException("No documents found")
        # prepare json text
        current_timestamp = datetime.now(timezone.utc).timestamp()
        report_entry = {"Querydate":  date_str,
             "ReportDate": current_timestamp,
             "Numfiles": valid_document_count
             }

        reports_history = EnterpriseManager._load_json_data(TEST_NUMDOCS_STORE_FILE)
        reports_history.append(report_entry)

        EnterpriseManager._save_json_data(TEST_NUMDOCS_STORE_FILE, reports_history)
        return valid_document_count
