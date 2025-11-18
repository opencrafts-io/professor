"""
Transformation module to convert extracted exam timetable data to Magnet ScheduleEntry format
"""
from datetime import datetime, time, date
from typing import Dict, Any, Optional, List, Tuple
import re


def parse_time_string(time_str: str) -> Tuple[Optional[time], Optional[time]]:
    """
    Parse time string to start_time and end_time objects
    Handles formats: "8:00AM-10:00AM", "0800-1000 HRS", "2.30 pm - 4.30pm", "11:00AM-14.00"
    """
    if not time_str:
        return None, None

    try:
        clean_time = str(time_str).strip().upper()
        clean_time = re.sub(r'\b(HR|HRS)\b', '', clean_time).strip()
        clean_time = re.sub(r'\s*-\s*', '-', clean_time)
        clean_time = re.sub(r'\s+', ' ', clean_time)
        clean_time = clean_time.strip()

        if '-' not in clean_time:
            return None, None

        parts = clean_time.split('-', 1)
        start_str = parts[0].strip()
        end_str = parts[1].strip()

        def parse_single_time(time_str: str, ampm_hint: Optional[str] = None) -> Optional[time]:
            """Parse a single time string to time object"""
            if not time_str:
                return None

            original = time_str
            time_str = str(time_str).strip()
            ampm = None

            ampm_match = re.search(r'([AP]M)', time_str, re.IGNORECASE)
            if ampm_match:
                ampm = ampm_match.group(1).upper()
                time_str = re.sub(r'[AP]M', '', time_str, flags=re.IGNORECASE).strip()

            if not ampm:
                ampm = ampm_hint

            time_str = time_str.replace('.', ':')

            if ':' in time_str:
                parts = time_str.split(':')
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            elif len(time_str) == 4 and time_str.isdigit():
                hour = int(time_str[:2])
                minute = int(time_str[2:])
            elif len(time_str) == 3 and time_str.isdigit():
                hour = int(time_str[0])
                minute = int(time_str[1:])
            else:
                try:
                    hour = int(time_str)
                    minute = 0
                except ValueError:
                    return None

            if ampm:
                if ampm == 'PM' and hour < 12:
                    hour += 12
                elif ampm == 'AM' and hour == 12:
                    hour = 0
            else:
                if hour >= 13:
                    hour = hour
                elif hour == 12:
                    hour = 12
                elif hour == 0:
                    hour = 0
                else:
                    hour = hour

            if hour >= 24:
                hour = hour % 24

            if minute >= 60:
                hour += minute // 60
                minute = minute % 60
                if hour >= 24:
                    hour = hour % 24

            try:
                return time(hour, minute)
            except (ValueError, TypeError) as e:
                return None

        start_ampm = None
        end_ampm = None

        start_ampm_match = re.search(r'([AP]M)', start_str)
        if start_ampm_match:
            start_ampm = start_ampm_match.group(1)
            start_str = re.sub(r'[AP]M', '', start_str).strip()

        end_ampm_match = re.search(r'([AP]M)', end_str)
        if end_ampm_match:
            end_ampm = end_ampm_match.group(1)
            end_str = re.sub(r'[AP]M', '', end_str).strip()

        start_time = parse_single_time(start_str, start_ampm)
        end_time = parse_single_time(end_str, end_ampm or start_ampm)

        return start_time, end_time

    except Exception:
        return None, None


def extract_day_of_week(date_val: Any) -> Optional[str]:
    """
    Extract day of week from date string or datetime object
    Returns: Monday, Tuesday, Wednesday, etc.
    """
    if not date_val:
        return None

    try:
        if isinstance(date_val, datetime):
            return date_val.strftime('%A')

        if isinstance(date_val, date):
            return date_val.strftime('%A')

        date_str = str(date_val).strip()

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days:
            if day.lower() in date_str.lower():
                return day

        try:
            dt = datetime.fromisoformat(date_str.replace(' 00:00:00', ''))
            return dt.strftime('%A')
        except:
            try:
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        return dt.strftime('%A')
                    except:
                        continue
            except:
                pass

        return None
    except Exception:
        return None


def to_magnet_schedule_entry(extracted_course: Dict[str, Any], is_exam: bool = True) -> Dict[str, Any]:
    """
    Transform extracted course data to Magnet ScheduleEntry format
    """
    course_code = extracted_course.get('course_code') or extracted_course.get('unit_code', '')
    course_name = extracted_course.get('course_name') or extracted_course.get('unit_name', '')

    date_val = extracted_course.get('date') or extracted_course.get('day')
    day_of_week = extract_day_of_week(date_val)

    time_str = extracted_course.get('time', '')
    start_time, end_time = parse_time_string(time_str)

    venue = extracted_course.get('venue') or extracted_course.get('room', '')
    location = venue
    room = venue if venue else None
    building = None

    if venue:
        parts = venue.split()
        if len(parts) > 1:
            building = parts[0]

    instructor = (
        extracted_course.get('instructor') or
        extracted_course.get('lecturer') or
        extracted_course.get('principal_invigilator') or
        extracted_course.get('coordinator', '')
    )

    result = {
        'course_code': course_code,
        'course_name': course_name,
        'day_of_week': day_of_week,
        'start_time': start_time.isoformat() if start_time else None,
        'end_time': end_time.isoformat() if end_time else None,
        'location': location if location else None,
        'room': room if room else None,
        'building': building if building else None,
        'instructor': instructor if instructor else None,
        'is_recurring': False if is_exam else True,
        'recurrence_pattern': None if is_exam else 'weekly',
        'raw_data': extracted_course
    }

    return result


def transform_exam_schedules(extracted_courses: List[Dict[str, Any]], source: str = 'kca') -> List[Dict[str, Any]]:
    """
    Transform a list of extracted courses to Magnet ScheduleEntry format
    """
    return [to_magnet_schedule_entry(course, is_exam=True) for course in extracted_courses]

