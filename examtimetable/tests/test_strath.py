#!/usr/bin/env python3

"""
Test script for Strathmore University timetable extractor

Tests all Strathmore Excel files in the uploads/strath folder
"""
import os
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professor.settings')
import django
django.setup()

from examtimetable.helpers import strath_extractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('strath_test_results.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_strath_files():
    """
    Test Strathmore extractor on all files in uploads/strath folder
    """
    project_root = Path(__file__).parent.parent.parent
    strath_folder = project_root / "uploads" / "strath"

    if not strath_folder.exists():
        logger.error(f"Strathmore folder not found: {strath_folder}")
        return

    excel_files = list(strath_folder.glob("*.xlsx"))

    if not excel_files:
        logger.warning(f"No Excel files found in {strath_folder}")
        return

    logger.info(f"Found {len(excel_files)} Strathmore Excel files to test")

    all_results = {}
    total_courses = 0

    for excel_file in excel_files:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing file: {excel_file.name}")
        logger.info(f"{'='*80}")

        try:
            courses = strath_extractor(str(excel_file))

            logger.info(f"Successfully extracted {len(courses)} courses")

            if courses:
                logger.info(f"Sample course (first entry):")
                sample_course = courses[0]
                for key, value in sample_course.items():
                    logger.info(f"  {key}: {value}")

                course_codes = [course.get('course_code', 'N/A') for course in courses]
                logger.info(f"Course codes found: {', '.join(course_codes[:10])}{'...' if len(course_codes) > 10 else ''}")

                programs = set(course.get('program', '') for course in courses if course.get('program'))
                logger.info(f"Programs found: {', '.join(programs)}")

                venues = set(course.get('venue', '') for course in courses if course.get('venue'))
                logger.info(f"Venues found: {', '.join(list(venues)[:10])}{'...' if len(venues) > 10 else ''}")

                times = [course.get('time', '') for course in courses if course.get('time')]
                if times:
                    logger.info(f"Time slots: {', '.join(set(times))}")

                lecturers = set(course.get('lecturer', '') for course in courses if course.get('lecturer'))
                logger.info(f"Lecturers found: {', '.join(list(lecturers)[:10])}{'...' if len(lecturers) > 10 else ''}")

                groups = set(course.get('group', '') for course in courses if course.get('group'))
                logger.info(f"Student groups found: {', '.join(list(groups)[:10])}{'...' if len(groups) > 10 else ''}")

                days = set(course.get('day', '') for course in courses if course.get('day'))
                logger.info(f"Days found: {', '.join(days)}")

                all_results[excel_file.name] = {
                    'file_path': str(excel_file),
                    'total_courses': len(courses),
                    'courses': courses,
                    'programs': list(programs),
                    'venues': list(venues),
                    'time_slots': list(set(times)),
                    'lecturers': list(lecturers),
                    'groups': list(groups),
                    'days': list(days)
                }

                total_courses += len(courses)
            else:
                logger.warning(f"No courses extracted from {excel_file.name}")
                all_results[excel_file.name] = {
                    'file_path': str(excel_file),
                    'total_courses': 0,
                    'courses': [],
                    'error': 'No courses extracted'
                }

        except Exception as e:
            logger.error(f"Error processing {excel_file.name}: {str(e)}")
            all_results[excel_file.name] = {
                'file_path': str(excel_file),
                'total_courses': 0,
                'courses': [],
                'error': str(e)
            }

    logger.info(f"\n{'='*80}")
    logger.info(f"STRATHMORE EXTRACTION SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total files processed: {len(excel_files)}")
    logger.info(f"Total courses extracted: {total_courses}")
    logger.info(f"Average courses per file: {total_courses/len(excel_files):.1f}")

    results_file = project_root / "strath_test_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    logger.info(f"Detailed results saved to: {results_file}")
    logger.info(f"Log file saved to: strath_test_results.log")

if __name__ == "__main__":
    test_strath_files()

