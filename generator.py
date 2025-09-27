import random

def generate_clash_free_timetable(sections):
    """
    Generate clash-free timetables using constraint-driven scheduling with lunch-aware lab placement.
    This algorithm ensures no teacher conflicts and respects lunch break constraints.
    """
    days = 6
    periods = 7  # 7 teaching periods
    
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
    
    # Phase 1: Constraint-driven lab placement with MRV heuristic
    lab_tasks = []
    for section in sections:
        lab_subjects = [s for s in section.subjects if s.is_lab]
        for lab_subject in lab_subjects:
            lab_tasks.append((section, lab_subject))
    
    # Sort lab tasks by block size (descending) and then by fewest feasible positions (MRV)
    def get_feasible_positions(section, lab_subject):
        allowed_starts = section.get_allowed_lab_starts(lab_subject.block_size)
        count = 0
        for day in range(days):
            for start in allowed_starts:
                if start + lab_subject.block_size <= periods:
                    # Check if slots would be available (ignoring teacher for MRV calculation)
                    if all(section.timetable[day][p] is None for p in range(start, start + lab_subject.block_size)):
                        count += 1
        return count
    
    lab_tasks.sort(key=lambda x: (-x[1].block_size, get_feasible_positions(x[0], x[1])))
    
    # Place lab subjects with constraint satisfaction and limited backtracking
    placed_labs = []
    for section, lab_subject in lab_tasks:
        teacher_name = lab_subject.teacher.name
        placed = False
        allowed_starts = section.get_allowed_lab_starts(lab_subject.block_size)
        
        # Generate all valid placement options
        candidates = []
        for day in range(days):
            for start in allowed_starts:
                if start + lab_subject.block_size <= periods:
                    # Check constraints
                    section_slots_free = all(
                        section.timetable[day][p] is None 
                        for p in range(start, start + lab_subject.block_size)
                    )
                    teacher_available = all(
                        teacher_schedule[teacher_name][day][p] is None 
                        for p in range(start, start + lab_subject.block_size)
                    )
                    teacher_can_handle = lab_subject.teacher.can_teach(lab_subject.block_size)
                    already_assigned = lab_subject.teacher.is_assigned_to_section(section, lab_subject.name)
                    
                    if section_slots_free and teacher_available and teacher_can_handle and not already_assigned:
                        candidates.append((day, start))
        
        if candidates:
            # Choose randomly from valid candidates to add variety
            day, start = random.choice(candidates)
            # Place the lab subject
            for p in range(start, start + lab_subject.block_size):
                section.timetable[day][p] = lab_subject
                teacher_schedule[teacher_name][day][p] = section.name
            lab_subject.teacher.current_load += lab_subject.block_size
            placed_labs.append((section, lab_subject, day, start))
            placed = True
        else:
            # Limited backtracking: try removing last few labs and retry
            if len(placed_labs) > 0:
                # Remove last lab and retry
                last_section, last_subject, last_day, last_start = placed_labs.pop()
                last_teacher = last_subject.teacher.name
                # Clear the placement
                for p in range(last_start, last_start + last_subject.block_size):
                    last_section.timetable[last_day][p] = None
                    teacher_schedule[last_teacher][last_day][p] = None
                last_subject.teacher.current_load -= last_subject.block_size
                
                # Re-insert the removed lab task to try later
                lab_tasks.append((last_section, last_subject))
                # Retry current lab
                lab_tasks.append((section, lab_subject))
                continue
            else:
                raise Exception(f"Could not place lab subject {lab_subject.name} in section {section.name}. Try reducing lab block sizes or teacher loads.")
    
    # Phase 2: Enhanced theory subject placement with better distribution
    for section in sections:
        theory_subjects = [s for s in section.subjects if not s.is_lab]
        
        for theory_subject in theory_subjects:
            teacher_name = theory_subject.teacher.name
            periods_to_place = theory_subject.periods_per_week
            periods_placed = 0
            
            # Track days where this subject has been placed to encourage distribution
            days_used = set()
            
            while periods_placed < periods_to_place:
                placed = False
                candidates = []
                
                # Generate weighted candidates (prefer empty days and slots)
                for day in range(days):
                    for period in range(periods):
                        # Check basic constraints
                        section_slot_free = section.timetable[day][period] is None
                        teacher_available = teacher_schedule[teacher_name][day][period] is None
                        teacher_can_handle = theory_subject.teacher.can_teach(1)
                        already_assigned = theory_subject.teacher.is_assigned_to_section(section, theory_subject.name)
                        
                        if section_slot_free and teacher_available and teacher_can_handle and not already_assigned:
                            # Calculate weight (prefer days not yet used for this subject)
                            weight = 2 if day not in days_used else 1
                            
                            # Avoid placing same subject multiple times per day if possible
                            same_subject_today = any(
                                section.timetable[day][p] == theory_subject for p in range(periods)
                            )
                            if same_subject_today:
                                weight *= 0.5
                            
                            candidates.append((day, period, weight))
                
                if candidates:
                    # Weighted random selection
                    total_weight = sum(w for _, _, w in candidates)
                    if total_weight > 0:
                        r = random.uniform(0, total_weight)
                        cumulative = 0
                        for day, period, weight in candidates:
                            cumulative += weight
                            if r <= cumulative:
                                # Place the subject
                                section.timetable[day][period] = theory_subject
                                teacher_schedule[teacher_name][day][period] = section.name
                                theory_subject.teacher.current_load += 1
                                periods_placed += 1
                                days_used.add(day)
                                placed = True
                                break
                
                if not placed:
                    # Fallback: try any available slot
                    fallback_attempts = 0
                    while not placed and fallback_attempts < 50:
                        day = random.randint(0, days-1)
                        period = random.randint(0, periods-1)
                        
                        section_slot_free = section.timetable[day][period] is None
                        teacher_available = teacher_schedule[teacher_name][day][period] is None
                        teacher_can_handle = theory_subject.teacher.can_teach(1)
                        already_assigned = theory_subject.teacher.is_assigned_to_section(section, theory_subject.name)
                        
                        if section_slot_free and teacher_available and teacher_can_handle and not already_assigned:
                            section.timetable[day][period] = theory_subject
                            teacher_schedule[teacher_name][day][period] = section.name
                            theory_subject.teacher.current_load += 1
                            periods_placed += 1
                            placed = True
                        
                        fallback_attempts += 1
                    
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
    periods = 7  # Updated to 7 periods

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
