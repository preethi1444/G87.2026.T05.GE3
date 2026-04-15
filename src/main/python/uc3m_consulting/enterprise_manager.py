"""Module """
import re
import json

from datetime import datetime, timezone
from freezegun import freeze_time
from uc3m_consulting.enterprise_project import EnterpriseProject
from uc3m_consulting.enterprise_management_exception import EnterpriseManagementException
from uc3m_consulting.enterprise_manager_config import (PROJECTS_STORE_FILE,
                                                       TEST_DOCUMENTS_STORE_FILE,
                                                       TEST_NUMDOCS_STORE_FILE)
from uc3m_consulting.project_document import ProjectDocument

class EnterpriseManager:
    """Class for providing the methods for managing the orders"""
    def __init__(self):
        pass

    @staticmethod
    def validate_cif(cif_code: str):
        """validates a cif number """
        if not isinstance(cif_code, str):
            raise EnterpriseManagementException("CIF code must be a string")
        # p: cif_regex_pattern
        cif_regex_pattern = re.compile(r"^[ABCDEFGHJKNPQRSUVW]\d{7}[0-9A-J]$")
        if not cif_regex_pattern.fullmatch(cif_code):
            raise EnterpriseManagementException("Invalid CIF format")

        cif_letter = cif_code[0]
        control_digit = cif_code[8]

        # Call the extracted calculation logic
        control_result = EnterpriseManager._calculate_cif_control(cif_code[1:8])

        # dic -> control_letter_mapping
        control_letter_mapping = "JABCDEFGHI"

        if cif_letter in ('A', 'B', 'E', 'H'):
            if str(control_result) != control_digit:
                raise EnterpriseManagementException("Invalid CIF character control number")
        elif cif_letter in ('P', 'Q', 'S', 'K'):
            if control_letter_mapping[control_result] != control_digit:
                raise EnterpriseManagementException("Invalid CIF character control letter")
        else:
            raise EnterpriseManagementException("CIF type not supported")
        return True

    @staticmethod
    def _calculate_cif_control(cif_numbers):
        """Internal helper to calculate the CIF control digit/letter (2.1a)"""
        even_sum = 0
        odd_sum = 0

        for i, digit_str in enumerate(cif_numbers):
            digit = int(digit_str)
            if i % 2 == 0:
                digit_multiplied = digit * 2
                even_sum += (digit_multiplied // 10) + (digit_multiplied % 10)
            else:
                odd_sum += digit

        total_sum = even_sum + odd_sum
        control_result = (10 - (total_sum % 10)) % 10
        return control_result

    @staticmethod
    def validate_date_format(date_string: str):
        """Unified validation for DD/MM/YYYY date format to remove duplication"""
        date_pattern = re.compile(r"^(([0-2]\d|3[0-1])\/(0\d|1[0-2])\/\d\d\d\d)$")
        date_match = date_pattern.fullmatch(date_string)
        if not date_match:
            raise EnterpriseManagementException("Invalid date format")

        try:
            parsed_date = datetime.strptime(date_string, "%d/%m/%Y").date()
        except ValueError as ex:
            raise EnterpriseManagementException("Invalid date format") from ex
        return parsed_date


    def validate_starting_date(self, date_string):
        parsed_date = self.validate_date_format(date_string)

        if parsed_date < datetime.now(timezone.utc).date():
            raise EnterpriseManagementException("Project's date must be today or later.")

        if parsed_date.year < 2025 or parsed_date.year > 2050:
            raise EnterpriseManagementException("Invalid date format")
        return date_string
    #pylint: disable=too-many-arguments, too-many-positional-arguments

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
    def _validate_budget(budget):
        """Internal helper to validate budget format and range (2.1a)"""
        try:
            budget_amount = float(budget)
        except ValueError as exc:
            raise EnterpriseManagementException("Invalid budget amount") from exc

        budget_string = str(budget_amount)
        if '.' in budget_string:
            decimal_places = len(budget_string.split('.')[1])
            if decimal_places > 2:
                raise EnterpriseManagementException("Invalid budget amount")

        if budget_amount < 50000 or budget_amount > 1000000:
            raise EnterpriseManagementException("Invalid budget amount")
        return budget_amount

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
        self.validate_cif(company_cif)
        acronym_pattern = re.compile(r"^[a-zA-Z0-9]{5,10}")
        acronym_match = acronym_pattern.fullmatch(project_acronym)
        if not acronym_match:
            raise EnterpriseManagementException("Invalid acronym")
        description_pattern = re.compile(r"^.{10,30}$")
        description_match = description_pattern.fullmatch(project_description)
        if not description_match:
            raise EnterpriseManagementException("Invalid description format")

        department_pattern = re.compile(r"(HR|FINANCE|LEGAL|LOGISTICS)")
        department_match = department_pattern.fullmatch(department)
        if not department_match:
            raise EnterpriseManagementException("Invalid department")

        self.validate_starting_date(date)
        self._validate_budget(budget)

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

    @staticmethod
    def _count_valid_docs_for_date(documents_data, date_str):
        """Internal helper to count documents with valid signatures (2.1a)"""
        count = 0
        for document in documents_data:
            registration_timestamp = document["register_date"]
            formatted_doc_date = datetime.fromtimestamp(registration_timestamp).strftime("%d/%m/%Y")

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

    def find_docs(self, date_str):
        """
        Generates a JSON report counting valid documents for a specific date.

        Checks cryptographic hashes and timestamps to ensure historical data integrity.
        Saves the output to 'resultado.json'.

        Args:
            date_str (str): date to query.

        Returns:
            number of documents found if report is successfully generated and saved.

        Raises:
            EnterpriseManagementException: On invalid date, file IO errors,
                missing data, or cryptographic integrity failure.
        """
        self.validate_date_format(date_str)
        # open documents
        documents_data = EnterpriseManager._load_json_data(TEST_DOCUMENTS_STORE_FILE)
        valid_document_count = self._count_valid_docs_for_date(documents_data, date_str)

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
