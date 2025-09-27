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
    """Format timetable data for web display with lunch periods inserted and lab blocks merged"""
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
    
    # Create schedule with lunch inserted at correct position and merge lab blocks
    for d in range(6):
        day_schedule = []
        teaching_period_index = 0
        
        # First pass: identify lab blocks
        lab_blocks = {}
        for p in range(7):
            subject = section.timetable[d][p]
            if subject and subject.is_lab:
                # Check if this is the start of a lab block
                if p == 0 or section.timetable[d][p-1] != subject:
                    # Count consecutive periods
                    span = 1
                    while (p + span < 7 and section.timetable[d][p + span] == subject):
                        span += 1
                    lab_blocks[p] = span
        
        for display_slot in range(8):  # 8 display slots total
            if display_slot == lunch_position:
                # Insert lunch break
                day_schedule.append({
                    'name': 'LUNCH',
                    'teacher': '',
                    'is_lab': False,
                    'is_lunch': True,
                    'colspan': 1,
                    'is_merged_lab': False
                })
            else:
                # Add teaching period
                if teaching_period_index >= 7:
                    break
                    
                subject = section.timetable[d][teaching_period_index]
                
                if subject and subject.is_lab and teaching_period_index in lab_blocks:
                    # This is the start of a lab block
                    lab_span = lab_blocks[teaching_period_index]
                    day_schedule.append({
                        'name': f"{subject.name} (Lab)",
                        'teacher': subject.teacher.name,
                        'is_lab': True,
                        'is_lunch': False,
                        'colspan': lab_span,
                        'is_merged_lab': True,
                        'block_size': lab_span
                    })
                    teaching_period_index += lab_span
                elif subject and not (subject.is_lab and teaching_period_index not in lab_blocks):
                    # Regular theory subject or standalone lab period
                    day_schedule.append({
                        'name': subject.name,
                        'teacher': subject.teacher.name,
                        'is_lab': subject.is_lab,
                        'is_lunch': False,
                        'colspan': 1,
                        'is_merged_lab': False
                    })
                    teaching_period_index += 1
                else:
                    # Empty slot or part of lab block already processed
                    if not (subject and subject.is_lab):
                        day_schedule.append(None)
                    teaching_period_index += 1
        
        timetable_data['schedule'].append(day_schedule)
    
    return timetable_data
