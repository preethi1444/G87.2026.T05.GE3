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

        # Extract components of the CIF
        cif_letter = cif_code[0]
        cif_numbers = cif_code[1:8]
        control_digit = cif_code[8]

        even_sum = 0 #even_sum (positions 0, 2, 4, 6 in the 1-indexed algorithm)
        odd_sum = 0 #odd_sum (positions 1, 3, 5)

        for i in range(len(cif_numbers)):
            if i % 2 == 0:
                # x -> digit_multiplied
                digit_multiplied = int(cif_numbers[i]) * 2
                if digit_multiplied > 9:
                    even_sum = even_sum + (digit_multiplied // 10) + (digit_multiplied % 10)
                else:
                    even_sum = even_sum + digit_multiplied
            else:
                odd_sum = odd_sum + int(cif_numbers[i])

        total_sum = even_sum + odd_sum
        last_digit_of_sum = total_sum % 10
        control_result = 10 - last_digit_of_sum

        if control_result == 10:
            control_result = 0

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

        try:
            budget_amount  = float(budget)
        except ValueError as exc:
            raise EnterpriseManagementException("Invalid budget amount") from exc

        budget_string = str(budget_amount)
        if '.' in budget_string:
            decimal_places = len(budget_string.split('.')[1])
            if decimal_places > 2:
                raise EnterpriseManagementException("Invalid budget amount")

        if budget_amount < 50000 or budget_amount > 1000000:
            raise EnterpriseManagementException("Invalid budget amount")


        new_project = EnterpriseProject(company_cif=company_cif,
                                        project_acronym=project_acronym,
                                        project_description=project_description,
                                        department=department,
                                        starting_date=date,
                                        project_budget=budget)

        try:
            with open(PROJECTS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                projects_list = json.load(file)
        except FileNotFoundError:
            projects_list = []
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex

        for existing_project in projects_list:
            if existing_project == new_project.to_json():
                raise EnterpriseManagementException("Duplicated project in projects list")

        projects_list.append(new_project.to_json())

        try:
            with open(PROJECTS_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(projects_list, file, indent=2)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex
        return new_project.project_id


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
        date_pattern = re.compile(r"^(([0-2]\d|3[0-1])\/(0\d|1[0-2])\/\d\d\d\d)$")
        date_match = date_pattern.fullmatch(date_str)
        if not date_match:
            raise EnterpriseManagementException("Invalid date format")

        try:
            target_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError as ex:
            raise EnterpriseManagementException("Invalid date format") from ex


        # open documents
        try:
            with open(TEST_DOCUMENTS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                documents_data = json.load(file)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file  or file path") from ex


        valid_document_count = 0

        # loop to find
        for document in documents_data:
            registration_timestamp = document["register_date"]

            # string conversion for easy match
            formatted_doc_date = datetime.fromtimestamp(registration_timestamp).strftime("%d/%m/%Y")

            if formatted_doc_date == date_str:
                document_datetime = datetime.fromtimestamp(registration_timestamp, tz=timezone.utc)
                with freeze_time(document_datetime):
                    # check the project id (thanks to freezetime)
                    # if project_id are different then the data has been
                    #manipulated
                    project_doc = ProjectDocument(document["project_id"], document["file_name"])
                    if project_doc.document_signature == document["document_signature"]:
                        valid_document_count += 1
                    else:
                        raise EnterpriseManagementException("Inconsistent document signature")

        if valid_document_count == 0:
            raise EnterpriseManagementException("No documents found")
        # prepare json text
        current_timestamp = datetime.now(timezone.utc).timestamp()
        report_entry = {"Querydate":  date_str,
             "ReportDate": current_timestamp,
             "Numfiles": valid_document_count
             }

        try:
            with open(TEST_NUMDOCS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                reports_history = json.load(file)
        except FileNotFoundError:
            reports_history = []
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex
        reports_history.append(report_entry)

        try:
            with open(TEST_NUMDOCS_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(reports_history, file, indent=2)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file  or file path") from ex
        return valid_document_count
