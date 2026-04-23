"""
Extracted from Entreprise Manager to implement CIF, date,
budget, and param checks
"""
import re
from datetime import datetime, timezone
from uc3m_consulting.enterprise_management_exception import EnterpriseManagementException

class project_valid:

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
        control_result = project_valid._calculate_cif_control(cif_code[1:8])

        # dic -> control_letter_mapping
        control_letter_mapping = "JABCDEFGHI"

        #cif types to see if control is numeric or alphabetic
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
            #have to double for even positions
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

    @staticmethod
    def validate_starting_date(date_string):
        parsed_date = project_valid.validate_date_format(date_string)

        #project can't start in past
        if parsed_date < datetime.now(timezone.utc).date():
            raise EnterpriseManagementException("Project's date must be today or later.")

        if parsed_date.year < 2025 or parsed_date.year > 2050:
            raise EnterpriseManagementException("Invalid date format")
        return date_string
    #pylint: disable=too-many-arguments, too-many-positional-arguments

    @staticmethod
    def validate_budget(budget):
        """Internal helper to validate budget format and range (2.1a)"""
        try:
            budget_amount = float(budget)
        except ValueError as exc:
            raise EnterpriseManagementException("Invalid budget amount") from exc

        #makes sure 2 decimal places max
        budget_string = str(budget_amount)
        if '.' in budget_string:
            decimal_places = len(budget_string.split('.')[1])
            if decimal_places > 2:
                raise EnterpriseManagementException("Invalid budget amount")

        if budget_amount < 50000 or budget_amount > 1000000:
            raise EnterpriseManagementException("Invalid budget amount")
        return budget_amount

    @staticmethod
    def validate_project_params(acronym, description, department):
        """Internal helper to validate basic project string parameters (2.1a)"""
        acronym_pattern = re.compile(r"^[a-zA-Z0-9]{5,10}")
        if not acronym_pattern.fullmatch(acronym):
            raise EnterpriseManagementException("Invalid acronym")

        description_pattern = re.compile(r"^.{10,30}$")
        if not description_pattern.fullmatch(description):
            raise EnterpriseManagementException("Invalid description format")

        department_pattern = re.compile(r"(HR|FINANCE|LEGAL|LOGISTICS)")
        if not department_pattern.fullmatch(department):
            raise EnterpriseManagementException("Invalid department")