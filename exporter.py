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
    """Format timetable data for web display with lunch periods inserted between teaching periods"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    lunch_position = section.get_lunch_period_position()
    
    # Create period labels with lunch inserted at the right position
    periods = []
    display_schedule = []
    
    # Generate periods list with lunch inserted
    for i in range(8):  # 7 teaching periods + 1 lunch = 8 slots
        if i == lunch_position:
            periods.append("LUNCH")
        elif i < lunch_position:
            periods.append(f"Period {i + 1}")
        else:
            periods.append(f"Period {i}")  # i already accounts for lunch shift
    
    timetable_data = {
        'section_name': section.name,
        'section_year': section.year,
        'days': days,
        'periods': periods,
        'schedule': [],
        'lunch_position': lunch_position
    }
    
    # Create schedule with lunch inserted at correct position
    for d in range(6):
        day_schedule = []
        teaching_period_index = 0
        
        for display_slot in range(8):  # 8 display slots total
            if display_slot == lunch_position:
                # Insert lunch break
                day_schedule.append({
                    'name': 'LUNCH',
                    'teacher': '',
                    'is_lab': False,
                    'is_lunch': True
                })
            else:
                # Add teaching period
                subject = section.timetable[d][teaching_period_index]
                if subject:
                    day_schedule.append({
                        'name': subject.name,
                        'teacher': subject.teacher.name,
                        'is_lab': subject.is_lab,
                        'is_lunch': False
                    })
                else:
                    day_schedule.append(None)
                teaching_period_index += 1
        
        timetable_data['schedule'].append(day_schedule)
    
    return timetable_data
