class Teacher:
    def __init__(self, name, max_load=28, subjects=None):
        self.name = name
        self.max_load = max_load
        self.current_load = 0
        self.subjects = subjects if subjects is not None else []  # List of subject names

    def can_teach(self, periods):
        return self.current_load + periods <= self.max_load

    def can_teach_subject(self, subject_name):
        return subject_name in self.subjects

    def is_assigned_to_section(self, section, subject_name):
        # Check if this teacher is already assigned to this section for any subject
        for subj, teacher in section.subject_assignments:
            if teacher.name == self.name and subj.name != subject_name:
                return True
        return False


class Subject:
    def __init__(self, name, periods_per_week, is_lab=False, block_size=1):
        self.name = name
        self.periods_per_week = periods_per_week
        self.is_lab = is_lab
        self.block_size = block_size
        self.teachers = []  # List of teacher names assigned to this subject
        self.teacher = None  # Currently assigned teacher object


class Section:
    def __init__(self, name, year, subject_assignments):
        self.name = name
        self.year = year
        self.subject_assignments = subject_assignments  # List of (subject, teacher) pairs
        self.timetable = [[None for _ in range(7)] for _ in range(6)]  # 7 teaching periods
        # For compatibility: subjects property is a list of subject objects
        self.subjects = [subj for subj, teacher in subject_assignments] if subject_assignments else []
    
    def get_lunch_period_position(self):
        """Get lunch break position based on year level (for display purposes)"""
        year_str = str(self.year).lower()
        if '1st' in year_str or 'first' in year_str or '1' in year_str:
            return 3  # Lunch after 3rd period (between period 3 and 4)
        else:  # 2nd year and above
            return 4  # Lunch after 4th period (between period 4 and 5)
    
    def get_morning_periods(self):
        """Get list of morning period indices (before lunch)"""
        lunch_pos = self.get_lunch_period_position()
        return list(range(lunch_pos))
    
    def get_evening_periods(self):
        """Get list of evening period indices (after lunch)"""
        lunch_pos = self.get_lunch_period_position()
        return list(range(lunch_pos, 7))  # 7 total teaching periods
