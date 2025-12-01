#!/usr/bin/env python3

"""
Test script for Nursing timetable extractor

Tests all Nursing Excel files in the uploads/nursing folder
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

from examtimetable.helpers import nursing_exam_timetable_parser

project_root = Path(__file__).parent.parent.parent
log_file = project_root / "docs" / "nursing_test_results.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file)),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_nursing_files():
    """
    Test Nursing extractor on all files in uploads/nursing folder
    """
    nursing_folder = project_root / "uploads" / "nursing"

    if not nursing_folder.exists():
        logger.error(f"Nursing folder not found: {nursing_folder}")
        return

    excel_files = list(nursing_folder.glob("*.xlsx")) + list(nursing_folder.glob("*.xls"))

    if not excel_files:
        logger.warning(f"No Excel files found in {nursing_folder}")
        return

    logger.info(f"Found {len(excel_files)} Nursing Excel files to test")

    all_results = {}
    total_courses = 0

    for excel_file in excel_files:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing file: {excel_file.name}")
        logger.info(f"{'='*80}")

        try:
            courses = nursing_exam_timetable_parser(str(excel_file))

            logger.info(f"Successfully extracted {len(courses)} courses")

            if courses:
                logger.info(f"Sample course (first entry):")
                sample_course = courses[0]
                for key, value in sample_course.items():
                    logger.info(f"  {key}: {value}")

                course_codes = [course.get('course_code', 'N/A') for course in courses]
                logger.info(f"Course codes found: {', '.join(course_codes[:10])}{'...' if len(course_codes) > 10 else ''}")

                venues = set(course.get('venue', '') for course in courses if course.get('venue'))
                logger.info(f"Venues found: {', '.join(list(venues)[:10])}{'...' if len(venues) > 10 else ''}")

                times = [course.get('time', '') for course in courses if course.get('time')]
                if times:
                    unique_times = set(times)
                    logger.info(f"Time slots: {', '.join(sorted(unique_times))}")

                days = set(course.get('day', '') for course in courses if course.get('day'))
                logger.info(f"Days found: {', '.join(sorted(days))}")

                campuses = set(course.get('campus', '') for course in courses if course.get('campus'))
                logger.info(f"Campuses found: {', '.join(sorted(campuses))}")

                coordinators = set(course.get('coordinator', '') for course in courses if course.get('coordinator'))
                logger.info(f"Coordinators found: {', '.join(list(coordinators)[:10])}{'...' if len(coordinators) > 10 else ''}")

                invigilators = set(course.get('invigilator', '') for course in courses if course.get('invigilator'))
                logger.info(f"Invigilators found: {', '.join(list(invigilators)[:10])}{'...' if len(invigilators) > 10 else ''}")

                hours_distribution = {}
                for course in courses:
                    hrs = course.get('hrs', '2')
                    hours_distribution[hrs] = hours_distribution.get(hrs, 0) + 1
                logger.info(f"Hours distribution: {hours_distribution}")

                all_results[excel_file.name] = {
                    'file_path': str(excel_file),
                    'total_courses': len(courses),
                    'courses': courses,
                    'venues': list(venues),
                    'time_slots': list(set(times)),
                    'days': list(days),
                    'campuses': list(campuses),
                    'coordinators': list(coordinators),
                    'invigilators': list(invigilators),
                    'hours_distribution': hours_distribution
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
            import traceback
            logger.error(traceback.format_exc())
            all_results[excel_file.name] = {
                'file_path': str(excel_file),
                'total_courses': 0,
                'courses': [],
                'error': str(e)
            }

    logger.info(f"\n{'='*80}")
    logger.info(f"NURSING EXTRACTION SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total files processed: {len(excel_files)}")
    logger.info(f"Total courses extracted: {total_courses}")
    if len(excel_files) > 0:
        logger.info(f"Average courses per file: {total_courses/len(excel_files):.1f}")

    results_file = project_root / "docs" / "nursing_test_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    logger.info(f"Detailed results saved to: {results_file}")
    logger.info(f"Log file will be saved to: {log_file}")

if __name__ == "__main__":
    test_nursing_files()

