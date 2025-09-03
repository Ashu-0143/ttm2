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
