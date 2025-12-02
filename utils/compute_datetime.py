from datetime import datetime
import re

def compute_datetime_str(day_str, time_str):
        """
        Compute datetime_str in ISO format UTC from day and time strings.
        Returns None if parsing fails.
        Handles formats like:
        - "Saturday 6th December 2025" + "2:00PM-4:00PM"
        - "13th December 2025" + "5:00PM-7:00PM"
        - "2025-12-01 00:00:00" + "8:00AM-10:00AM"
        - "Monday, December 01, 2025" + "0800-1000 HRS"

        regex muscles must be flexxed at any convinience. : )
        """
        if not day_str or not time_str:
            return None

        try:
            date_obj = None
            time_obj = None

            day_str = str(day_str).strip()
            time_str = str(time_str).strip()

            if "-" in time_str:
                start_time_str = time_str.split("-")[0].strip()
            else:
                start_time_str = time_str

            for fmt in ["%I:%M%p", "%I:%M %p", "%H:%M", "%H.%M"]:
                try:
                    time_obj = datetime.strptime(start_time_str, fmt).time()
                    break
                except ValueError:
                    continue

            if not time_obj:
                return None

            day_str_lower = day_str.lower()
            date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})', day_str_lower)
            if date_match:
                day_num, month_name, year = date_match.groups()
                month_map = {
                    'january': 1, 'february': 2, 'march': 3, 'april': 4,
                    'may': 5, 'june': 6, 'july': 7, 'august': 8,
                    'september': 9, 'october': 10, 'november': 11, 'december': 12
                }
                if month_name in month_map:
                    try:
                        date_obj = datetime(int(year), month_map[month_name], int(day_num)).date()
                    except ValueError:
                        return None
            elif re.match(r'\d{4}-\d{2}-\d{2}', day_str):
                try:
                    date_obj = datetime.strptime(day_str.split()[0], "%Y-%m-%d").date()
                except ValueError:
                    return None
            elif "/" in day_str:
                parts = day_str.split()
                if len(parts) >= 2:
                    date_part = parts[-1]
                    try:
                        date_obj = datetime.strptime(date_part, "%d/%m/%y").date()
                    except ValueError:
                        try:
                            date_obj = datetime.strptime(date_part, "%d/%m/%Y").date()
                        except ValueError:
                            return None
                else:
                    date_part = day_str
                    day_prefix_match = re.match(r'^[A-Z]{3}\s*(\d{1,2}/\d{1,2}/\d{2,4})', day_str, re.IGNORECASE)
                    if day_prefix_match:
                        date_part = day_prefix_match.group(1)
                    try:
                        date_obj = datetime.strptime(date_part, "%d/%m/%y").date()
                    except ValueError:
                        try:
                            date_obj = datetime.strptime(date_part, "%d/%m/%Y").date()
                        except ValueError:
                            return None

            if date_obj and time_obj:
                dt = datetime.combine(date_obj, time_obj)
                return dt.isoformat() + "Z"

        except Exception:
            pass

        return None