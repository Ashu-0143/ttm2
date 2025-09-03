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
        self.timetable = [[None for _ in range(7)] for _ in range(6)]
    
    def get_lunch_period(self):
        """Get lunch period index based on year level"""
        year_str = str(self.year).lower()
        if '1st' in year_str or 'first' in year_str or '1' in year_str:
            return 3  # Lunch after 3rd period (index 3 = 4th slot)
        else:  # 2nd year and above
            return 4  # Lunch after 4th period (index 4 = 5th slot)
    
    def get_available_periods_before_lunch(self):
        """Get list of period indices before lunch"""
        lunch_period = self.get_lunch_period()
        return list(range(lunch_period))
    
    def get_available_periods_after_lunch(self):
        """Get list of period indices after lunch"""
        lunch_period = self.get_lunch_period()
        return list(range(lunch_period + 1, 7))
