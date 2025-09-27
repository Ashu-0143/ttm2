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
    
    # Create schedule with lunch inserted at correct position and maintain exact 8-slot structure
    for d in range(6):
        day_schedule = []
        
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
        
        # Create display schedule ensuring exactly 8 slots
        teaching_period_index = 0
        for display_slot in range(8):
            if display_slot == lunch_position:
                # Insert lunch break
                day_schedule.append({
                    'name': 'LUNCH',
                    'teacher': '',
                    'is_lab': False,
                    'is_lunch': True,
                    'colspan': 1,
                    'is_merged_lab': False,
                    'is_hidden': False
                })
            else:
                # Add teaching period
                if teaching_period_index >= 7:
                    # Add empty slot if we've run out of teaching periods
                    day_schedule.append(None)
                else:
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
                            'block_size': lab_span,
                            'is_hidden': False
                        })
                        teaching_period_index += lab_span
                    elif subject and not (subject.is_lab and teaching_period_index not in lab_blocks):
                        # Regular theory subject
                        day_schedule.append({
                            'name': subject.name,
                            'teacher': subject.teacher.name,
                            'is_lab': subject.is_lab,
                            'is_lunch': False,
                            'colspan': 1,
                            'is_merged_lab': False,
                            'is_hidden': False
                        })
                        teaching_period_index += 1
                    elif subject and subject.is_lab:
                        # This is a continuation of a lab block, add hidden placeholder
                        day_schedule.append({
                            'name': '',
                            'teacher': '',
                            'is_lab': True,
                            'is_lunch': False,
                            'colspan': 1,
                            'is_merged_lab': False,
                            'is_hidden': True,
                            'is_part_of_lab': True
                        })
                        teaching_period_index += 1
                    else:
                        # Empty slot
                        day_schedule.append(None)
                        teaching_period_index += 1
        
        timetable_data['schedule'].append(day_schedule)
    
    return timetable_data
