import random

def generate_clash_free_timetable(sections):
    """
    Generate clash-free timetables by tracking teacher availability globally.
    This algorithm ensures no teacher conflicts from the first try.
    """
    days = 6
    periods = 8  # 8 teaching periods
    
    # Global teacher availability tracker
    # teacher_schedule[teacher_name][day][period] = section_name or None
    teacher_schedule = {}
    
    # Initialize teacher schedules
    for section in sections:
        for subject in section.subjects:
            teacher_name = subject.teacher.name
            if teacher_name not in teacher_schedule:
                teacher_schedule[teacher_name] = [[None for _ in range(periods)] for _ in range(days)]
    
    # Clear existing timetables and reset teacher loads
    for section in sections:
        section.timetable = [[None for _ in range(periods)] for _ in range(days)]
        for subject in section.subjects:
            subject.teacher.current_load = 0
    
    # Phase 1: Place lab subjects first (labs must be either morning OR evening, not crossing lunch)
    for section in sections:
        lab_subjects = [s for s in section.subjects if s.is_lab]
        for lab_subject in lab_subjects:
            teacher_name = lab_subject.teacher.name
            placed = False
            attempts = 0
            max_attempts = 200  # Increased attempts due to lunch constraints
            
            morning_periods = section.get_morning_periods()
            evening_periods = section.get_evening_periods()
            
            while not placed and attempts < max_attempts:
                day = random.randint(0, days-1)
                
                # Try to place lab block either completely in morning OR evening
                possible_slots = []
                
                # Check if lab can fit in morning periods
                if len(morning_periods) >= lab_subject.block_size:
                    for start in range(len(morning_periods) - lab_subject.block_size + 1):
                        end = start + lab_subject.block_size
                        if end <= len(morning_periods):
                            possible_slots.append((start, end))
                
                # Check if lab can fit in evening periods
                if len(evening_periods) >= lab_subject.block_size:
                    for start in range(len(evening_periods) - lab_subject.block_size + 1):
                        actual_start = evening_periods[start]
                        actual_end = actual_start + lab_subject.block_size
                        if actual_end <= periods:  # Make sure we don't exceed 8 periods
                            possible_slots.append((actual_start, actual_end))
                
                if not possible_slots:
                    attempts += 1
                    continue
                
                # Randomly choose one of the possible slots
                start_period, end_period = random.choice(possible_slots)
                
                # Check if all consecutive periods are free in section timetable
                section_slots_free = all(
                    section.timetable[day][p] is None 
                    for p in range(start_period, end_period)
                )
                
                # Check if teacher is available for all consecutive periods
                teacher_available = all(
                    teacher_schedule[teacher_name][day][p] is None 
                    for p in range(start_period, end_period)
                )
                
                # Check teacher load capacity
                teacher_can_handle = lab_subject.teacher.can_teach(lab_subject.block_size)
                
                if section_slots_free and teacher_available and teacher_can_handle:
                    # Place the lab subject
                    for p in range(start_period, end_period):
                        section.timetable[day][p] = lab_subject
                        teacher_schedule[teacher_name][day][p] = section.name
                    
                    lab_subject.teacher.current_load += lab_subject.block_size
                    placed = True
                
                attempts += 1
            
            if not placed:
                raise Exception(f"Could not place lab subject {lab_subject.name} in section {section.name}. Try reducing lab block sizes or teacher loads.")
    
    # Phase 2: Place theory subjects one period at a time
    for section in sections:
        theory_subjects = [s for s in section.subjects if not s.is_lab]
        for theory_subject in theory_subjects:
            teacher_name = theory_subject.teacher.name
            periods_to_place = theory_subject.periods_per_week
            periods_placed = 0
            
            while periods_placed < periods_to_place:
                placed = False
                attempts = 0
                max_attempts = 100
                
                while not placed and attempts < max_attempts:
                    day = random.randint(0, days-1)
                    
                    # Theory subjects can be placed in any of the 8 teaching periods
                    period = random.randint(0, periods-1)
                    
                    # Check section slot is free
                    section_slot_free = section.timetable[day][period] is None
                    
                    # Check teacher availability
                    teacher_available = teacher_schedule[teacher_name][day][period] is None
                    
                    # Check teacher load capacity
                    teacher_can_handle = theory_subject.teacher.can_teach(1)
                    
                    if section_slot_free and teacher_available and teacher_can_handle:
                        # Place the subject
                        section.timetable[day][period] = theory_subject
                        teacher_schedule[teacher_name][day][period] = section.name
                        theory_subject.teacher.current_load += 1
                        periods_placed += 1
                        placed = True
                    
                    attempts += 1
                
                if not placed:
                    raise Exception(f"Could not place all periods for {theory_subject.name} in section {section.name}. Try adjusting teacher loads or periods per week.")
    
    return sections

def generate_timetable(sections):
    """
    Main timetable generation function.
    First tries the clash-free algorithm, falls back to original if needed.
    """
    try:
        # Try the new clash-free algorithm first
        return generate_clash_free_timetable(sections)
    except Exception as e:
        # If clash-free algorithm fails, fall back to original algorithm
        print(f"Clash-free generation failed: {e}")
        return generate_timetable_original(sections)

def generate_timetable_original(sections):
    """
    Original timetable generation algorithm (fallback).
    First places lab subjects (which require consecutive periods),
    then places theory subjects one period at a time.
    """
    days = 6
    periods = 8  # Updated to 8 periods

    for section in sections:
        # Clear existing timetable
        section.timetable = [[None for _ in range(periods)] for _ in range(days)]
        
        # Reset teacher loads for this generation
        for subject in section.subjects:
            subject.teacher.current_load = 0

        # Step 1: Place labs first (they need consecutive periods)
        lab_subjects = [s for s in section.subjects if s.is_lab]
        for subj in lab_subjects:
            placed = False
            attempts = 0
            max_attempts = 100  # Prevent infinite loops
            
            while not placed and attempts < max_attempts:
                day = random.randint(0, days-1)
                start = random.randint(0, periods - subj.block_size)
                
                # Check if all required consecutive periods are available
                if all(section.timetable[day][p] is None for p in range(start, start + subj.block_size)):
                    # Check if teacher is available for all these periods
                    if subj.teacher.can_teach(subj.block_size):
                        # Place the lab subject in consecutive periods
                        for p in range(start, start + subj.block_size):
                            section.timetable[day][p] = subj
                        subj.teacher.current_load += subj.block_size
                        placed = True
                
                attempts += 1
            
            if not placed:
                raise Exception(f"Could not place lab subject {subj.name} in section {section.name}. Try adjusting teacher loads or lab block sizes.")

        # Step 2: Place theory subjects (one period at a time)
        theory_subjects = [s for s in section.subjects if not s.is_lab]
        for subj in theory_subjects:
            periods_placed = 0
            
            while periods_placed < subj.periods_per_week:
                placed = False
                attempts = 0
                max_attempts = 100
                
                while not placed and attempts < max_attempts:
                    day = random.randint(0, days-1)
                    period = random.randint(0, periods-1)
                    
                    # Check if slot is empty and teacher can teach
                    if section.timetable[day][period] is None and subj.teacher.can_teach(1):
                        section.timetable[day][period] = subj
                        subj.teacher.current_load += 1
                        periods_placed += 1
                        placed = True
                    
                    attempts += 1
                
                if not placed:
                    raise Exception(f"Could not place all periods for subject {subj.name} in section {section.name}. Try adjusting teacher loads.")

    return sections
