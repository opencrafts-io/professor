# contains helper functions
from openpyxl import load_workbook
from datetime import datetime
from typing import Any, Dict, List, Optional
import re

# parses nursing exam timetable
def nursing_exam_timetable_parser(file):

    # Define the list of column headers
    column_headers = ['Day', 'Campus', 'Coordinator', 'Courses', 'Hours',
                      'Venue', 'Invigilators', 'Courses_Afternoon',
                      'Hours_Afternoon', 'Invigilators_Afternoon',
                      'Venue_Afternoon']

    def extract_course_info(column_data_dict, time_key, time_range):
        courses = []
        existing_course_codes = set()
        for i in range(len(column_data_dict["Day"])):
            course_code = column_data_dict[time_key][i]
            if course_code not in time_range and course_code not in existing_course_codes:
                course_info = {
                    "course_code": column_data_dict[time_key][i].strip(), #.replace(" ", ""),
                    "coordinator": column_data_dict["Coordinator"][i],
                    "time": '8:30AM-11:30AM' if "8.30" in time_range[0] else '1:30PM-4:30PM',
                    "day": column_data_dict["Day"][i],
                    "campus": column_data_dict["Campus"][i],
                    "hrs": column_data_dict[f"Hours{'_Afternoon' if '_Afternoon' in time_key else ''}"][i],
                    "venue": column_data_dict[f"Venue{'_Afternoon' if '_Afternoon' in time_key else ''}"][i],
                    "invigilator": column_data_dict[f"Invigilators{'_Afternoon' if '_Afternoon' in time_key else ''}"][i]
                }

                courses.append(course_info)
                existing_course_codes.add(course_code)
        return courses

    # Loading the excel workbook
    wb_obj = load_workbook(file)
    sheet = wb_obj.active  # Activating the sheet for use

    # Initialize dictionary to store column data
    column_data_dict = {}

    # Iterate over columns and store data in dictionary
    for i, column in enumerate(sheet.iter_cols(values_only=True) if sheet else []):
        last_value = None
        column_data = []
        for cell in column:
            if cell is not None:
                # if column_headers[i] == 'Day':
                #     cell = cell.strftime('%A %d-%m-%Y')
                last_value = cell
                column_data.append(cell)
            else:
                column_data.append(last_value)
        if any(cell is not None for cell in column_data):
            column_data_dict[column_headers[i]] = column_data

    # Extract course information
    morning_exams = extract_course_info(column_data_dict, "Courses", ['8.30AM-11.30AM', '8.30-11.30 AM'])
    afternoon_exams = extract_course_info(column_data_dict, "Courses_Afternoon", ['1.30PM-4.30PM', '1.30-4.30PM'])

    # Combine morning and afternoon exams
    courses = morning_exams + afternoon_exams

    return courses


# parses nursing school timetable
def parse_nursing_timetable(file_path):
    # holds start and end times of every column number
    time_dictionary = {
        "2": ("8AM", "9AM"),
        "3": ("9AM", "10AM"),
        "4": ("10AM", "11AM"),
        "5": ("11AM", "12PM"),
        "6": ("12PM", "1PM"),
        "7": ("1PM", "2PM"),
        "8": ("2PM", "3PM"),
        "9": ("3PM", "4PM"),
        "10": ("4PM", "5PM"),
        "11": ("5PM", "6PM"),
    }

    days_of_the_week = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
    unnecessary_course_values = ["CHAPEL", "CLP", "SDL", "KEY",
                                "CLP-CLINICAL PRACTICE",
                                "SDL- SELF DIRECTED LEARNING"]

    courses = [] # will hold dictionaries of courses

    # loading the excel workbook
    wb_obj = load_workbook(filename=file_path)
    work_sheets = wb_obj.sheetnames # getting available work sheets

    # getting info from from first worksheet
    first_work_sheet = wb_obj[work_sheets[0]]

    # will hold course names and lecturers key being course code
    course_lectures = {}

    # iterating through the sheet
    for row in first_work_sheet.iter_rows(values_only=True):
        if row[1] == "CODE" or row[1] is None:
            continue

        # concantenating course name and the lecturer
        course_lectures[row[1]] = [row[2] , row[3]]

     # getting info from from second worksheet
    second_work_sheet = wb_obj[work_sheets[1]]

    # course contents
    day = ""
    venue = ""
    course_time = ""
    course_name = ""

    # itearating the workbook
    for row_idx, rows in enumerate(second_work_sheet.iter_rows(values_only=True)):
        # skipping the unnecessary titles
        if row_idx in [0, 1, 2]:
            continue

        # skipping row with dates and taking the day of the course
        if rows[1] in days_of_the_week:
            day = rows[1]
            continue

        for idx ,row_value in enumerate(rows):
            # skipping the cohort part
            if idx == 1:
                continue

            # skipping unnecessary course values
            if row_value is None or (isinstance(row_value, str) and row_value.strip() in unnecessary_course_values):
                continue

            # getting the venue
            if idx == 0:
                venue = row_value
                continue

            # getting course time
            start_time = time_dictionary[f"{idx}"][0]

            # setting course code
            course_name = str(row_value).strip() if row_value is not None else ""

            # handling merged rows
            remaining_cells = rows[idx+1:]
            rem_idx = idx + 1
            for rem_idx_iter, rem in enumerate(remaining_cells, start=idx+1):
                if rem is not None:
                    rem_idx = rem_idx_iter
                    break

            # concatenating start time and end time
            course_time = start_time + "-" + time_dictionary[f"{rem_idx}"][1]

            courses.append({
                "course_code": course_name[:7].strip().replace(" ", ""),
                "lecturer": course_lectures[course_name[:7].strip()][1],
                "course_name": course_name,
                "day":day,
                "venue":venue,
                "time":course_time
                })

    return courses

def parse_school_exam_timetable(file):
    def time_difference(start_time, end_time):
        """
        Returns the difference in hrs between two
        time intervals
        """

        format = '%I:%M%p'
        start_time = datetime.strptime(start_time, format)
        end_time = datetime.strptime(end_time, format)
        hrs = (end_time - start_time).total_seconds() / 3600
        return str(hrs)

    # loading the workbook
    wb_obj = load_workbook(filename=file)

    work_sheets = wb_obj.sheetnames # getting available work sheets

    # getting info from from first workbook
    # first_work_sheet = wb_obj[work_sheets[0]]
    # for sheet in book.worksheets: #For each worksheet


    rooms = {} # will hold room informationhold information about courses

    courses = [] # will hold courses information

    days_of_the_week = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
    for sheet in work_sheets:
        work_sheet = wb_obj[sheet]

        # iterating through the rooms and storing them
        for column_one in work_sheet.iter_cols(values_only=True): #For each Column in a worksheet
            for i, room in enumerate(column_one):
                # skipping none values and room word
                if room is None or room == "ROOM":
                    continue
                rooms[f'{i}'] = room
            break
        # a list of the remaining columns without the rooms
        data_columns = list(work_sheet.iter_cols(values_only=True))[1:]

        # values for the course code
        day = ""
        course_time = ""
        course_code = ""
        hours = "2"

        # iterating through the columns data
        for column in data_columns:
            for idx, value in enumerate(column):
                # skipping empty cell values
                if value is None:
                    continue

                # checking if its date and day specification
                if isinstance(value, datetime):
                    day = days_of_the_week[value.weekday()] + " " + str(value.date()).replace("-", "/")
                elif isinstance(value, str) and value.split(" ")[0] in days_of_the_week:
                    day = value

                # checking if its time specification
                elif isinstance(value, str) and len(value) > 0 and value[0].isdigit():
                    course_time = value.strip()
                    start_time = course_time.split("-")[0]
                    end_time = course_time.split("-")[1]
                    hours = time_difference(start_time, end_time)
                elif isinstance(value, str):
                    course_code = value
                    hours_str = "2"  # default
                    if hours and len(hours) > 0:
                        hours_str = "2" if hours[0] == "-" else hours[0]
                    courses.append(
                        {
                            "course_code": course_code,
                            "day": day,
                            "time": course_time,
                            "venue": rooms.get(f'{idx}', ""),
                            # handles errors recorded in exam timetable defaults to 2
                            "hrs": hours_str,
                        }
                    )
    return courses

def strath_extractor(file):
    """
    Extracts TT data for Strathmore University
    """

    def format_strath_time(time):
        """
        converts format (8:00-10:00) to (8:00AM-10:00AM)
        """
        if not time or "-" not in time:
            return time

        start_time, end_time = time.split("-", 1)
        start_time = start_time.strip()
        end_time = end_time.strip()

        def convert_to_12hour(time_24):
            if ":" in time_24:
                hour, minute = time_24.split(":")
                hour = int(hour)
                if hour == 0:
                    return f"12:{minute}AM"
                elif hour < 12:
                    return f"{hour}:{minute}AM"
                elif hour == 12:
                    return f"12:{minute}PM"
                else:
                    return f"{hour-12}:{minute}PM"
            return time_24

        formatted_start_time = convert_to_12hour(start_time)
        formatted_end_time = convert_to_12hour(end_time)

        return f"{formatted_start_time}-{formatted_end_time}"

    web_obj = load_workbook(file)
    sheet = web_obj.active

    # Variables to track merged cells
    current_date = ""
    current_time = ""
    current_course = ""
    current_group = ""
    current_number = ""
    current_venue = ""
    current_lecturer = ""

    course = []

    for row_idx, row in enumerate(sheet.iter_rows(values_only=True) if sheet else []):
        # Skip header rows (assuming first 3 rows are intro/header)
        if row_idx < 3:
            continue

        date_val = row[0] if len(row) > 0 else None
        time_val = row[2] if len(row) > 2 else None
        course_val = row[4] if len(row) > 4 else None
        group_val = row[6] if len(row) > 6 else None
        number_val = row[7] if len(row) > 7 else None
        venue_val = row[8] if len(row) > 8 else None
        lecturer_val = row[10] if len(row) > 10 else None

        # Handle merged cells - update current values when new data is found
        if date_val and str(date_val).strip():
            current_date = str(date_val).strip().rstrip('.')
        if time_val and str(time_val).strip():
            current_time = str(time_val).strip()
        if course_val and str(course_val).strip():
            current_course = str(course_val).strip()
        if group_val and str(group_val).strip():
            current_group = str(group_val).strip()
        if number_val is not None:  # Allow 0 as valid
            current_number = str(number_val).strip()
        if venue_val and str(venue_val).strip():
            current_venue = str(venue_val).strip()
        if lecturer_val and str(lecturer_val).strip():
            current_lecturer = str(lecturer_val).strip()

        # Append if there's a new group or a new venue (for split venues)
        if current_course and current_group and current_venue:
            if (group_val and str(group_val).strip()) or (venue_val and str(venue_val).strip()):
                # Split course code and name
                course_parts = current_course.split(":", 1)
                course_code = course_parts[0].strip() if course_parts else current_course
                course_name = course_parts[1].strip() if len(course_parts) > 1 else ""

                # Format time to match existing pattern
                formatted_time = format_strath_time(current_time)

                course_info = {
                    "course_code": course_code,
                    "course_name": course_name,
                    "day": current_date,
                    "time": formatted_time,
                    "venue": current_venue,
                    "lecturer": current_lecturer,
                    "group": current_group,
                    "student_count": current_number,
                    "program": current_group.split()[0] if current_group else "",
                }
                course.append(course_info)

    return course

def kca_extractor(file):
    """
    Extracts TT data for KCA University
    Resulted to using simple regex to handle the different formats in different timetables.
    """

    def format_time(time_str):
        """
        Standardizes various time formats to (8:00AM-10:00AM)
        """
        if not time_str:
            return ""

        # Normalize: remove "HR"/"HRS", handle dots/spaces/AM/PM
        clean_time = re.sub(r'(HR|HRS)', '', time_str.upper()).strip()
        clean_time = re.sub(r'\s*-\s*', '-', clean_time)

        # Match patterns like "8.30am-10.30am", "0800-1000", "8am-10am", "5pm-7pm"
        match = re.match(r'(\d{1,2}(?:\.\d{2})?)([AP]M)?-(\d{1,2}(?:\.\d{2})?)([AP]M)?', clean_time)
        if not match:
            return time_str

        start_hour, start_ampm, end_hour, end_ampm = match.groups()
        start_hour = start_hour.replace('.', ':')
        end_hour = end_hour.replace('.', ':')

        # Ensure minutes if missing
        if ':' not in start_hour:
            start_hour += ':00'
        if ':' not in end_hour:
            end_hour += ':00'

        # Handle AM/PM or infer from 24h format
        def to_12hour(hour_min, ampm=None):
            hour, minute = map(int, hour_min.split(':'))
            if ampm is None:
                if hour >= 12:
                    ampm = 'PM'
                    hour = hour - 12 if hour > 12 else hour
                else:
                    ampm = 'AM'
            return f"{hour}:{minute:02d}{ampm}"

        formatted_start = to_12hour(start_hour, start_ampm)
        formatted_end = to_12hour(end_hour, end_ampm or start_ampm)

        return f"{formatted_start}-{formatted_end}"

    def convert_date(date_val):
        """Convert Excel serial or string to readable date
        from (Monday, 1st January 2025) to (2025-01-01)
        """
        if isinstance(date_val, (int, float)):
            try:
                return datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(date_val) - 2).strftime('%Y-%m-%d')
            except ValueError:
                return str(date_val)
        return str(date_val).strip()

    def compute_session_from_time(formatted_time):
        """Map formatted time to session number"""
        if formatted_time == "8:00AM-10:00AM":
            return "1"
        elif formatted_time == "11:00AM-1:00PM":
            return "2"
        elif formatted_time == "2:00PM-4:00PM":
            return "3"
        elif formatted_time == "5:00PM-7:00PM":
            return "4"
        else:
            return ""

    wb_obj = load_workbook(file, data_only=True)
    sheet = wb_obj.active

    # Find header row
    header_row = None
    header_idx = 0
    for row_idx, row in enumerate(sheet.iter_rows(values_only=True) if sheet else [], start=1):
        if any('UNIT CODE' in str(cell).upper() for cell in row if cell):
            header_row = list(map(str, row))
            header_idx = row_idx
            break
    if not header_row:
        return []

    # Normalize headers
    norm_headers = {h.upper().strip().replace(' ', '_'): idx for idx, h in enumerate(header_row) if h}

    key_map = {
        "SESSION": "SESSION",
        "DATE": "DATE",
        "TIME": "TIME",
        "ROOM": "ROOM|VENUE",
        "UNIT_CODE": "UNIT_CODE|UNIT CODE",
        "UNIT_NAME": "UNIT_NAME|UNIT NAME",
        "PRINCIPAL_INVIGILATOR": "PRINCIPAL_INVIGILATORS|PRINCIPAL INVIGILATORS - MAIN|PRINCIPAL INVIGILATORS (MAIN)|INVIGILATOR OF THE SESSION",
        "SUPPORT_INVIGILATOR": "SUPPORT_INVIGILATORS|ADDITIONAL_INVIGILATORS_MAIN|OTHER INVIGILATORS (MAIN)",
        "STUDENT_COUNT": "COUNTER|COUNT",
        "PROGRAM": "PROGRAM_NAME|PROG",
        "MODE_OF_STUDY": "MODE_OF_STUDY",
        "SCHOOL": "SCHOOL",
        "DEPARTMENT": "DEPARTMENT|DEPARMENT",
        "TRIMESTER": "TRIMESTER",
        "CAMPUS": "CAMPUS",
        "SESSION_LEADER": "SESSION_LEADER",
        "REMARKS": "REMARKS",
    }

    courses: List[Dict[str, Any]] = []
    current_entry: Optional[Dict[str, Any]] = None

    for row_idx, row in enumerate(sheet.iter_rows(min_row=header_idx + 1, values_only=True) if sheet else [], start=header_idx + 1):
        row = list(map(lambda x: x if x is not None else "", row))

        unit_code = ""
        for pattern in key_map["UNIT_CODE"].split('|'):
            if pattern in norm_headers:
                unit_code = str(row[norm_headers[pattern]]).strip()
                break

        if unit_code:
            if current_entry:
                courses.append(current_entry)
            current_entry = {"course_code": unit_code}
            raw_time = ""
            for out_key, patterns in key_map.items():
                for pattern in patterns.split('|'):
                    if pattern in norm_headers:
                        val = row[norm_headers[pattern]]
                        if out_key == "DATE":
                            val = convert_date(val)
                        elif out_key == "TIME":
                            raw_time = str(val)
                            val = format_time(raw_time)
                        current_entry[out_key.lower()] = str(val).strip()
                        break
                if out_key.lower() not in current_entry:
                    current_entry[out_key.lower()] = ""
            program_val = current_entry.get("program", "")
            if isinstance(program_val, str):
                current_entry["program"] = [program_val] if program_val else []
            else:
                current_entry["program"] = program_val if isinstance(program_val, list) else []
            current_entry["venue"] = current_entry.pop("room", "")

            # Handle formula in session
            if current_entry["session"].startswith('=IF'):
                current_entry["session"] = compute_session_from_time(current_entry["time"])

        elif current_entry:
            for out_key, patterns in key_map.items():
                for pattern in patterns.split('|'):
                    if pattern in norm_headers:
                        val = str(row[norm_headers[pattern]]).strip()
                        if val and out_key.lower() in ["program", "venue", "principal_invigilator", "support_invigilator"]:
                            existing_val = current_entry.get(out_key.lower(), "")
                            if isinstance(existing_val, str):
                                current_entry[out_key.lower()] = [existing_val] if existing_val else []
                            elif not isinstance(existing_val, list):
                                current_entry[out_key.lower()] = []
                            if isinstance(current_entry[out_key.lower()], list):
                                current_entry[out_key.lower()].append(val)
                        break

    if current_entry:
        courses.append(current_entry)

    for course in courses:
        for key in ["program", "venue", "principal_invigilator", "support_invigilator"]:
            if isinstance(course[key], list):
                course[key] = ", ".join(set(filter(None, course[key])))  # Unique non-empty

    return courses