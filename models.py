class Teacher:
    def __init__(self, name, max_load=28):
        self.name = name
        self.max_load = max_load
        self.current_load = 0

    def can_teach(self, periods):
        return self.current_load + periods <= self.max_load


class Subject:
    def __init__(self, name, teacher, periods_per_week, is_lab=False, block_size=1):
        self.name = name
        self.teacher = teacher
        self.periods_per_week = periods_per_week
        self.is_lab = is_lab
        self.block_size = block_size


class Section:
    def __init__(self, name, year, subjects):
        self.name = name
        self.year = year
        self.subjects = subjects
        self.timetable = [[None for _ in range(7)] for _ in range(6)]  # 7 teaching periods
    
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
