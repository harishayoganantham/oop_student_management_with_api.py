"""
OOP Student Management System with Public API Integration
=========================================================
Task 3 adds a country-information feature using the public REST Countries API.

Features:
- Student management: add, view, search, update, delete
- Student and class performance reports
- Save/load student records using JSON
- Search country information from a public REST API
- Friendly handling of invalid input, missing results, network/API errors

No third-party packages are required. Uses Python's standard library.

Run:
    python oop_student_management_with_api.py

Country API:
    https://restcountries.com/
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


# --------------------------- STUDENT CLASS ---------------------------

class Student:
    """Represents one student and encapsulates student information."""

    PASS_MARK = 40

    def __init__(
        self,
        student_id: str,
        name: str,
        age: int,
        department: str,
        marks: Dict[str, float],
        attendance: float,
        status: str = "Active",
    ):
        self.student_id = self._required_text(student_id, "Student ID").upper()
        self.name = self._required_text(name, "Name")
        self.age = self._validate_age(age)
        self.department = self._required_text(department, "Department")
        self.marks = self._validate_marks(marks)
        self.attendance = self._validate_percentage(attendance, "Attendance")
        self.status = self._required_text(status, "Status")

    @staticmethod
    def _required_text(value, field_name: str) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError(f"{field_name} cannot be empty.")
        return value

    @staticmethod
    def _validate_age(age) -> int:
        try:
            age = int(age)
        except (TypeError, ValueError):
            raise ValueError("Age must be a whole number.") from None
        if not 1 <= age <= 120:
            raise ValueError("Age must be between 1 and 120.")
        return age

    @staticmethod
    def _validate_percentage(value, field_name: str) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field_name} must be a number.") from None
        if not 0 <= value <= 100:
            raise ValueError(f"{field_name} must be between 0 and 100.")
        return value

    @classmethod
    def _validate_marks(cls, marks: Dict[str, float]) -> Dict[str, float]:
        if not isinstance(marks, dict) or not marks:
            raise ValueError("Enter marks for at least one subject.")
        validated = {}
        for subject, mark in marks.items():
            subject = cls._required_text(subject, "Subject")
            validated[subject] = cls._validate_percentage(mark, f"Mark for {subject}")
        return validated

    @property
    def average(self) -> float:
        return sum(self.marks.values()) / len(self.marks)

    @property
    def performance(self) -> str:
        if self.average >= 85:
            return "Excellent"
        if self.average >= 70:
            return "Good"
        if self.average >= 50:
            return "Average"
        return "Needs Improvement"

    @property
    def result(self) -> str:
        return "PASS" if all(mark >= self.PASS_MARK for mark in self.marks.values()) else "FAIL"

    def update(self, **changes) -> None:
        allowed = {"name", "age", "department", "marks", "attendance", "status"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unsupported field(s): {', '.join(sorted(unknown))}")

        candidate = {
            "name": self.name,
            "age": self.age,
            "department": self.department,
            "marks": self.marks.copy(),
            "attendance": self.attendance,
            "status": self.status,
        }
        candidate.update(changes)
        candidate["name"] = self._required_text(candidate["name"], "Name")
        candidate["age"] = self._validate_age(candidate["age"])
        candidate["department"] = self._required_text(candidate["department"], "Department")
        candidate["marks"] = self._validate_marks(candidate["marks"])
        candidate["attendance"] = self._validate_percentage(candidate["attendance"], "Attendance")
        candidate["status"] = self._required_text(candidate["status"], "Status")

        for field, value in candidate.items():
            setattr(self, field, value)

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "name": self.name,
            "age": self.age,
            "department": self.department,
            "marks": self.marks,
            "attendance": self.attendance,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Student":
        return cls(**data)


# --------------------------- FILE MANAGER ---------------------------

class FileManager:
    """Reads and writes student records in JSON format."""

    def __init__(self, filename: str = "students.json"):
        self.filepath = Path(filename)

    def save(self, students: List[Student]) -> None:
        try:
            data = [student.to_dict() for student in students]
            self.filepath.write_text(json.dumps(data, indent=4), encoding="utf-8")
        except OSError as error:
            raise OSError(f"Could not save student data: {error}") from error

    def load(self) -> List[Student]:
        if not self.filepath.exists():
            return []
        try:
            data = json.loads(self.filepath.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("Student data file must contain a list.")
            result = []
            for number, record in enumerate(data, start=1):
                try:
                    result.append(Student.from_dict(record))
                except (TypeError, ValueError, KeyError) as error:
                    raise ValueError(f"Invalid student record #{number}: {error}") from error
            return result
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Could not load student data: {error}") from error


# --------------------------- STUDENT MANAGER ---------------------------

class StudentManager:
    """Manages the collection of student objects."""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
        self.students: Dict[str, Student] = {}

    def add_student(self, student: Student) -> None:
        if student.student_id in self.students:
            raise ValueError(f"Student ID {student.student_id} already exists.")
        self.students[student.student_id] = student

    def get_student(self, student_id: str) -> Student:
        student_id = str(student_id).strip().upper()
        if student_id not in self.students:
            raise KeyError(f"No student found with ID {student_id}.")
        return self.students[student_id]

    def update_student(self, student_id: str, **changes) -> None:
        self.get_student(student_id).update(**changes)

    def delete_student(self, student_id: str) -> Student:
        student = self.get_student(student_id)
        del self.students[student.student_id]
        return student

    def all_students(self) -> List[Student]:
        return sorted(self.students.values(), key=lambda student: student.student_id)

    def save(self) -> None:
        self.file_manager.save(self.all_students())

    def load(self) -> int:
        records = self.file_manager.load()
        ids = [student.student_id for student in records]
        if len(ids) != len(set(ids)):
            raise ValueError("Student data contains duplicate IDs.")
        self.students = {student.student_id: student for student in records}
        return len(self.students)


# --------------------------- REPORT GENERATOR ---------------------------

class ReportGenerator:
    """Formats individual student and class performance reports."""

    @staticmethod
    def student_report(student: Student) -> str:
        return (
            "\nStudent Report\n"
            "---------------\n"
            f"{student.student_id} | {student.name} | {student.department}\n"
            f"Age: {student.age}\n"
            f"Average: {student.average:.1f}%\n"
            f"Attendance: {student.attendance:.1f}%\n"
            f"Status: {student.status}\n"
            f"Performance: {student.performance}\n"
            f"Result: {student.result}"
        )

    @staticmethod
    def class_report(students: List[Student]) -> str:
        if not students:
            return "No student records available."

        average = sum(student.average for student in students) / len(students)
        attendance = sum(student.attendance for student in students) / len(students)
        passed = sum(student.result == "PASS" for student in students)
        top = max(students, key=lambda student: student.average)

        lines = [
            "\nClass Performance Report",
            "------------------------",
            f"Total students: {len(students)}",
            f"Class average: {average:.1f}%",
            f"Average attendance: {attendance:.1f}%",
            f"Passed: {passed}",
            f"Failed: {len(students) - passed}",
            f"Top performer: {top.name} ({top.average:.1f}%)",
        ]
        return "\n".join(lines)


# --------------------------- PUBLIC API CLASS ---------------------------

class CountryAPI:
    """
    Gets country information from REST Countries API.

    The API response is JSON. This class extracts only the fields useful
    to the application and returns a small, clean dictionary.
    """

    BASE_URL = "https://restcountries.com/v3.1/name/"
    TIMEOUT_SECONDS = 10

    def get_country(self, country_name: str) -> dict:
        country_name = country_name.strip()
        if not country_name:
            raise ValueError("Country name cannot be empty.")
        if len(country_name) > 80:
            raise ValueError("Country name is too long.")

        url = self.BASE_URL + quote(country_name, safe="") + "?fields=name,capital,population,region,currencies"
        request = Request(
            url,
            headers={"User-Agent": "StudentManagementApp/1.0", "Accept": "application/json"},
        )

        try:
            with urlopen(request, timeout=self.TIMEOUT_SECONDS) as response:
                if response.status != 200:
                    raise RuntimeError(f"Country API returned HTTP status {response.status}.")
                raw_data = response.read().decode("utf-8")
        except HTTPError as error:
            if error.code == 404:
                raise LookupError(f"No country found matching '{country_name}'.") from error
            raise RuntimeError(f"Country API is unavailable (HTTP {error.code}).") from error
        except URLError as error:
            raise ConnectionError("Network error: unable to reach the country API.") from error
        except TimeoutError as error:
            raise ConnectionError("Network request timed out. Please try again.") from error
        except OSError as error:
            raise ConnectionError(f"Network error: {error}") from error

        try:
            payload = json.loads(raw_data)
        except json.JSONDecodeError as error:
            raise ValueError("The API returned invalid JSON data.") from error

        if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
            raise ValueError("The API response has an unexpected format.")

        # Use the first matching result, then transform it into display-ready data.
        item = payload[0]
        try:
            common_name = item["name"]["common"]
            capital_value = item.get("capital") or []
            capital = ", ".join(capital_value) if capital_value else "Not available"
            population = int(item["population"])
            region = item["region"] or "Not available"

            currency_data = item.get("currencies") or {}
            currency_codes = list(currency_data.keys())
            currency = ", ".join(currency_codes) if currency_codes else "Not available"

            if not isinstance(common_name, str) or not common_name.strip():
                raise ValueError
            if population < 0:
                raise ValueError
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("The API response is missing valid country information.") from error

        return {
            "name": common_name,
            "capital": capital,
            "population": population,
            "region": region,
            "currency": currency,
        }


# --------------------------- APPLICATION ---------------------------

class StudentManagementApp:
    """Console interface connecting student features and the country API."""

    def __init__(self):
        self.manager = StudentManager(FileManager())
        self.reports = ReportGenerator()
        self.country_api = CountryAPI()

    @staticmethod
    def read_int(prompt: str) -> int:
        try:
            return int(input(prompt).strip())
        except ValueError:
            raise ValueError("Please enter a valid whole number.") from None

    @staticmethod
    def read_float(prompt: str) -> float:
        try:
            return float(input(prompt).strip())
        except ValueError:
            raise ValueError("Please enter a valid number.") from None

    def input_marks(self) -> Dict[str, float]:
        marks = {}
        print("Enter subject marks. Type 'done' when finished.")
        while True:
            subject = input("Subject name (or done): ").strip()
            if subject.lower() == "done":
                break
            if not subject:
                print("Subject name cannot be empty.")
                continue
            if subject in marks:
                print("Subject already entered.")
                continue
            marks[subject] = self.read_float(f"Mark for {subject} (0-100): ")
        if not marks:
            raise ValueError("At least one subject mark is required.")
        return marks

    def add_student(self) -> None:
        student = Student(
            input("Student ID: "),
            input("Name: "),
            self.read_int("Age: "),
            input("Department: "),
            self.input_marks(),
            self.read_float("Attendance (0-100): "),
        )
        self.manager.add_student(student)
        self.manager.save()
        print("Student added successfully.")

    def view_students(self) -> None:
        students = self.manager.all_students()
        if not students:
            print("No student records found.")
            return
        for student in students:
            print(self.reports.student_report(student))

    def search_student(self) -> None:
        print(self.reports.student_report(self.manager.get_student(input("Student ID: "))))

    def update_student(self) -> None:
        student_id = input("Student ID to update: ")
        student = self.manager.get_student(student_id)
        print("Press Enter to keep the current value.")
        changes = {}
        for field, current in (
            ("name", student.name),
            ("age", student.age),
            ("department", student.department),
            ("attendance", student.attendance),
            ("status", student.status),
        ):
            value = input(f"{field.title()} [{current}]: ").strip()
            if value:
                changes[field] = value
        if input("Change subject marks? (y/n): ").strip().lower() == "y":
            changes["marks"] = self.input_marks()
        if not changes:
            print("No changes entered.")
            return
        self.manager.update_student(student_id, **changes)
        self.manager.save()
        print("Student updated successfully.")

    def delete_student(self) -> None:
        student_id = input("Student ID to delete: ")
        student = self.manager.get_student(student_id)
        if input(f"Delete {student.name}? (y/n): ").strip().lower() == "y":
            self.manager.delete_student(student_id)
            self.manager.save()
            print("Student deleted.")
        else:
            print("Delete cancelled.")

    def show_country_information(self) -> None:
        country_name = input("Enter country name: ")
        try:
            country = self.country_api.get_country(country_name)
            population = f"{country['population']:,}"
            print(
                "\nCountry Information\n"
                "-------------------\n"
                f"Name       : {country['name']}\n"
                f"Capital    : {country['capital']}\n"
                f"Population : {population}\n"
                f"Region     : {country['region']}\n"
                f"Currency   : {country['currency']}"
            )
        except ValueError as error:
            print(f"Invalid input/API response: {error}")
        except LookupError as error:
            print(f"No matching result: {error}")
        except ConnectionError as error:
            print(f"Connection problem: {error}")
        except RuntimeError as error:
            print(f"API unavailable: {error}")

    def run(self) -> None:
        try:
            count = self.manager.load()
            print(f"Loaded {count} student record(s).")
        except (OSError, ValueError) as error:
            print(f"Warning: {error}")

        actions = {
            "1": self.add_student,
            "2": self.view_students,
            "3": self.search_student,
            "4": self.update_student,
            "5": self.delete_student,
            "6": lambda: print(self.reports.class_report(self.manager.all_students())),
            "7": self.show_country_information,
            "8": lambda: (self.manager.save(), print("Student data saved.")),
        }

        while True:
            print(
                "\n===== STUDENT MANAGEMENT SYSTEM =====\n"
                "1. Add student\n"
                "2. View all students\n"
                "3. Search student\n"
                "4. Update student\n"
                "5. Delete student\n"
                "6. Class performance report\n"
                "7. Search country information (Public API)\n"
                "8. Save student data\n"
                "9. Exit"
            )
            choice = input("Enter your choice (1-9): ").strip()

            if choice == "9":
                try:
                    self.manager.save()
                    print("Data saved. Goodbye!")
                except OSError as error:
                    print(f"Could not save before exit: {error}")
                break

            action = actions.get(choice)
            if action is None:
                print("Invalid menu choice. Select a number from 1 to 9.")
                continue

            try:
                action()
            except (ValueError, KeyError, OSError) as error:
                print(f"Operation failed: {error}")
            except (EOFError, KeyboardInterrupt):
                print("\nInput cancelled.")
                break


if __name__ == "__main__":
    try:
        StudentManagementApp().run()
    except KeyboardInterrupt:
        print("\nProgram interrupted.")
