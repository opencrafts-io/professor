"""
Copyright (c) 2025 Open Crafts Interactive Ltd. All Rights Reserved.
email: developers@opencrafts.io

Standard data structures that all magnet_adapters must return
after performing certain operations.

Conforming to these data structures ensures that there is consistent
data regardless of the university portal difference.
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, time, date
from typing import Any, Dict, List, Optional


class AuthMethodType(Enum):
    """Types of authentication strategies that are supported by magnet"""

    FORM_BASED = "form"  # Username/password html form
    OAUTH_2 = "oauth2"  # oauth2 authentication flow
    MULTI_FACTOR = "mfa"  # Required multi factor authentication


class PortalFeature(Enum):
    """Features that a portal may support"""

    COURSES = "courses"  # Enrolled courses
    GRADES = "grades"  # Grade history
    SCHEDULE = "schedule"  # Class schedule/timetable
    EXAMS = "exams"  # Exam/schedule
    TRANSCRIPT = "transcript"  # Academic transcript
    ATTENDANCE = "attendance"  # Attendance records
    FEES = "fees"  # Fee statements
    LIBRARY = "library"  # Library records
    ASSIGNMENTS = "assignments"  # Assignment submissions
    ANNOUNCEMENTS = "announcements"  # Portal announcements
    PROFILE = "profile"  # Student profile


class GradeScale(Enum):
    """Common grading scales"""

    LETTER = "letter"  # A, B, C, D, F
    GPA_4 = "gpa_4"  # 0.0 - 4.0
    GPA_5 = "gpa_5"  # 0.0 - 5.0
    PERCENTAGE = "percentage"  # 0 - 100
    PASS_FAIL = "pass_fail"  # Pass/Fail


@dataclass
class AuthCredentials:
    """Credentials for portal authentication"""

    username: str
    password: str
    additional_fields: Dict[str, str] = field(default_factory=dict)

    # For MFA
    mfa_code: Optional[str] = None
    mfa_method: Optional[str] = None  # 'sms', 'email', 'app'

    # For OAuth/SAML
    oauth_token: Optional[str] = None
    oauth_state: Optional[str] = None


@dataclass
class SessionToken:
    """Represents an authenticated session"""

    access_token: str
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    refresh_token: Optional[str] = None

    # Session-specific data (cookies, etc)
    session_data: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if token is expired"""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at

    def to_dict(self) -> Dict:
        """Serialize to dictionary for caching"""
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "refresh_token": self.refresh_token,
            "session_data": self.session_data,
        }



@dataclass
class AuthenticationResult:
    """Result of authentication attempt"""

    success: bool
    session_token: Optional[SessionToken] = None
    error_message: Optional[str] = None
    requires_mfa: bool = False
    mfa_methods_available: List[str] = field(default_factory=list)

    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StudentProfile:
    """Normalized student profile data"""

    student_id: str
    email: str

    # Name
    full_name: str 
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    # Nationality information
    national_id: Optional[str] = None
    nationality: Optional[str] = None

    # Study information
    program: Optional[str] = None
    major: Optional[str] = None
    year: Optional[int] = None
    gpa: Optional[float] = None

    # The disability status of the student
    disability_status: Optional[str] = None
    # The school / branch the student is from
    school: Optional[str] = None

    # Contact
    phone: Optional[str] = None
    address: Optional[str] = None

    # Metadata
    enrollment_date: Optional[date] = None
    expected_graduation: Optional[date] = None

    # Raw data from portal (for debugging)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Course:
    """Normalized course data"""

    course_code: str
    course_name: str
    semester: str

    # Optional fields
    course_id: Optional[str] = None  # Internal university ID
    instructor: Optional[str] = None
    credits: Optional[float] = None
    department: Optional[str] = None

    # Schedule info (if available)
    meeting_times: List[str] = field(default_factory=list)
    location: Optional[str] = None

    # Metadata
    description: Optional[str] = None
    enrollment_status: Optional[str] = None  # enrolled, waitlisted, dropped

    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Grade:
    """Normalized grade data"""

    course_code: str
    course_name: str
    semester: str
    grade: str  # Letter grade or numeric

    # Optional fields
    grade_points: Optional[float] = None  # Numeric grade
    credits: Optional[float] = None
    grade_scale: Optional[GradeScale] = None

    # Additional info
    instructor: Optional[str] = None
    remarks: Optional[str] = None

    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleEntry:
    """Normalized schedule/timetable entry"""

    course_code: str
    course_name: str
    day_of_week: str  # Monday, Tuesday, etc.
    start_time: time
    end_time: time

    # Optional fields
    location: Optional[str] = None
    room: Optional[str] = None
    building: Optional[str] = None
    instructor: Optional[str] = None

    # Recurrence info
    is_recurring: bool = True
    recurrence_pattern: Optional[str] = None  # weekly, biweekly

    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transcript:
    """Normalized academic transcript"""

    student_id: str
    student_name: str
    program: str

    # Academic summary
    overall_gpa: Optional[float] = None
    total_credits: Optional[float] = None

    # Grades by semester
    grades: List[Grade] = field(default_factory=list)

    # Additional info
    awards: List[str] = field(default_factory=list)
    academic_standing: Optional[str] = None  # Good standing, probation, etc.

    generated_date: Optional[date] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemesterInfo:
    """Information about a semester/term"""

    code: str  # Internal code
    name: str  # Display name
    start_date: date
    end_date: date
    is_current: bool = False

    # Academic year info
    year: Optional[int] = None
    term: Optional[str] = None
