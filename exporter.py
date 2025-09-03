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
    """Format timetable data for web display with lunch periods"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    lunch_period = section.get_lunch_period()
    
    # Create period labels with lunch
    periods = []
    for i in range(7):
        if i == lunch_period:
            periods.append("LUNCH")
        elif i < lunch_period:
            periods.append(f"Period {i + 1}")
        else:
            periods.append(f"Period {i}")
    
    timetable_data = {
        'section_name': section.name,
        'section_year': section.year,
        'days': days,
        'periods': periods,
        'schedule': [],
        'lunch_period': lunch_period
    }
    
    for d in range(6):
        day_schedule = []
        for p in range(7):
            if p == lunch_period:
                # Add lunch break
                day_schedule.append({
                    'name': 'LUNCH',
                    'teacher': '',
                    'is_lab': False,
                    'is_lunch': True
                })
            else:
                subject = section.timetable[d][p]
                if subject:
                    day_schedule.append({
                        'name': subject.name,
                        'teacher': subject.teacher.name,
                        'is_lab': subject.is_lab,
                        'is_lunch': False
                    })
                else:
                    day_schedule.append(None)
        timetable_data['schedule'].append(day_schedule)
    
    return timetable_data
