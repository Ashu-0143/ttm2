def print_section_timetable(section):
    """Original console printing function (preserved for compatibility)"""
    print(f"\nTimetable for {section.name} ({section.year})")
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    for d in range(6):
        row = []
        for p in range(7):
            subj = section.timetable[d][p]
            row.append(subj.name if subj else "--")
        print(days[d], " | ", " | ".join(row))

def format_timetable_for_web(section):
    """Format timetable data for web display"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    periods = ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5", "Period 6", "Period 7"]
    
    timetable_data = {
        'section_name': section.name,
        'section_year': section.year,
        'days': days,
        'periods': periods,
        'schedule': []
    }
    
    for d in range(6):
        day_schedule = []
        for p in range(7):
            subject = section.timetable[d][p]
            if subject:
                day_schedule.append({
                    'name': subject.name,
                    'teacher': subject.teacher.name,
                    'is_lab': subject.is_lab
                })
            else:
                day_schedule.append(None)
        timetable_data['schedule'].append(day_schedule)
    
    return timetable_data
