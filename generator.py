import random

# Old function removed - consolidated into improved version

def generate_clash_free_timetable_improved(sections):
    """
    Improved clash-free timetable generation with enhanced randomization,
    better constraint handling, and robust backtracking.
    """
    days = 6
    periods = 7  # 7 teaching periods
    
    # Global teacher availability tracker
    teacher_schedule = {}
    
    # Initialize teacher schedules and clear existing timetables
    for section in sections:
        section.timetable = [[None for _ in range(periods)] for _ in range(days)]
        for subject in section.subjects:
            teacher_name = subject.teacher.name
            if teacher_name not in teacher_schedule:
                teacher_schedule[teacher_name] = [[None for _ in range(periods)] for _ in range(days)]
            subject.teacher.current_load = 0
    
    # Phase 1: Enhanced lab placement with flexible constraints
    lab_tasks = []
    for section in sections:
        lab_subjects = [s for s in section.subjects if s.is_lab]
        for lab_subject in lab_subjects:
            lab_tasks.append((section, lab_subject))
    
    # Sort by block size (largest first) for better placement success
    lab_tasks.sort(key=lambda x: -x[1].block_size)
    
    # Place lab subjects with improved flexibility
    for section, lab_subject in lab_tasks:
        teacher_name = lab_subject.teacher.name
        placed = False
        
        # Generate all possible placement positions
        candidates = []
        allowed_starts = section.get_allowed_lab_starts(lab_subject.block_size)
        
        # First try with allowed starts (respecting lunch constraints)
        for day in range(days):
            for start in allowed_starts:
                if start + lab_subject.block_size <= periods:
                    if check_lab_placement_feasible(section, lab_subject, teacher_schedule, teacher_name, day, start):
                        candidates.append((day, start, 'preferred'))
        
        # If no preferred slots, try any valid position
        if not candidates:
            for day in range(days):
                for start in range(periods - lab_subject.block_size + 1):
                    if check_lab_placement_feasible(section, lab_subject, teacher_schedule, teacher_name, day, start):
                        candidates.append((day, start, 'fallback'))
        
        # Place lab with priority to preferred slots
        if candidates:
            # Prefer 'preferred' slots, then randomly select
            preferred = [c for c in candidates if c[2] == 'preferred']
            if preferred:
                day, start, _ = random.choice(preferred)
            else:
                day, start, _ = random.choice(candidates)
            
            # Place the lab subject
            for p in range(start, start + lab_subject.block_size):
                section.timetable[day][p] = lab_subject
                teacher_schedule[teacher_name][day][p] = section.name
            lab_subject.teacher.current_load += lab_subject.block_size
            placed = True
        
        if not placed:
            raise Exception(f"Could not place lab subject {lab_subject.name} (block size {lab_subject.block_size}) in section {section.name}. Try reducing lab block sizes or teacher loads.")
    
    # Phase 2: Enhanced theory subject placement with smart distribution
    for section in sections:
        theory_subjects = [s for s in section.subjects if not s.is_lab]
        
        # Randomize order of theory subjects for better distribution
        random.shuffle(theory_subjects)
        
        for theory_subject in theory_subjects:
            teacher_name = theory_subject.teacher.name
            periods_to_place = theory_subject.periods_per_week
            periods_placed = 0
            
            # Track used days for better distribution
            days_used = set()
            max_per_day = min(3, periods_to_place)  # Limit periods per day
            
            placement_attempts = 0
            max_placement_attempts = periods_to_place * 50  # More generous attempts
            
            while periods_placed < periods_to_place and placement_attempts < max_placement_attempts:
                placed = False
                candidates = []
                
                # Generate weighted candidates
                for day in range(days):
                    day_count = sum(1 for p in range(periods) if section.timetable[day][p] == theory_subject)
                    
                    # Skip if already at max for this day
                    if day_count >= max_per_day:
                        continue
                    
                    for period in range(periods):
                        if (section.timetable[day][period] is None and 
                            teacher_schedule[teacher_name][day][period] is None):
                            
                            # Check teacher load more flexibly
                            load_ok = (theory_subject.teacher.can_teach(1) or 
                                     theory_subject.teacher.current_load < theory_subject.teacher.max_load * 1.2)  # 20% flexibility
                            
                            if load_ok:
                                # Calculate weight for smart placement
                                weight = calculate_placement_weight(day, period, days_used, day_count, max_per_day)
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
                    # Fallback: try any available slot with more flexibility
                    fallback_candidates = []
                    for day in range(days):
                        for period in range(periods):
                            if (section.timetable[day][period] is None and 
                                teacher_schedule[teacher_name][day][period] is None):
                                fallback_candidates.append((day, period))
                    
                    if fallback_candidates:
                        day, period = random.choice(fallback_candidates)
                        section.timetable[day][period] = theory_subject
                        teacher_schedule[teacher_name][day][period] = section.name
                        theory_subject.teacher.current_load += 1
                        periods_placed += 1
                        placed = True
                
                placement_attempts += 1
            
            if periods_placed < periods_to_place:
                raise Exception(f"Could not place all {periods_to_place} periods for {theory_subject.name} in section {section.name}. Placed {periods_placed}. Try adjusting teacher loads or periods per week.")
    
    return sections

def check_lab_placement_feasible(section, lab_subject, teacher_schedule, teacher_name, day, start):
    """Check if a lab can be placed at the given position without conflicts."""
    # Check section slots are free
    section_slots_free = all(
        section.timetable[day][p] is None 
        for p in range(start, start + lab_subject.block_size)
    )
    
    # Check teacher availability
    teacher_available = all(
        teacher_schedule[teacher_name][day][p] is None 
        for p in range(start, start + lab_subject.block_size)
    )
    
    # Check teacher load with flexibility
    teacher_can_handle = (lab_subject.teacher.can_teach(lab_subject.block_size) or 
                         lab_subject.teacher.current_load + lab_subject.block_size <= lab_subject.teacher.max_load * 1.2)
    
    return section_slots_free and teacher_available and teacher_can_handle

def calculate_placement_weight(day, period, days_used, day_count, max_per_day):
    """Calculate placement weight for smart theory subject distribution."""
    weight = 1.0
    
    # Prefer days not yet used for this subject
    if day not in days_used:
        weight *= 2.0
    
    # Prefer slots that don't overload a single day
    remaining_capacity = max_per_day - day_count
    if remaining_capacity > 1:
        weight *= 1.5
    
    # Slight preference for middle periods (avoid first/last)
    if 1 <= period <= 5:
        weight *= 1.1
    
    return weight

def generate_timetable(sections):
    """
    Main timetable generation function.
    Uses improved clash-free algorithm with multiple attempts, conflict verification,
    and guaranteed conflict-free results or clear failure with guidance.
    """
    # Import conflicts module for verification
    from conflicts import detect_teacher_conflicts
    
    max_attempts = 8
    original_random_state = random.getstate()
    
    print(f"Starting timetable generation with {len(sections)} sections...")
    
    for attempt in range(max_attempts):
        try:
            # Use different random seed for each attempt for variety
            seed = random.randint(1, 50000) + attempt * 1000
            random.seed(seed)
            print(f"Attempt {attempt + 1}/{max_attempts} with seed {seed}")
            
            # Clear all state before generation attempt
            clear_all_state(sections)
            
            # Generate using improved clash-free algorithm
            result_sections = generate_clash_free_timetable_improved(sections)
            
            # Verify no conflicts exist
            conflicts = detect_teacher_conflicts(result_sections)
            
            if not conflicts:
                print(f"✓ Success! Generated conflict-free timetable on attempt {attempt + 1}")
                # Restore original random state
                random.setstate(original_random_state)
                return result_sections
            else:
                print(f"✗ Attempt {attempt + 1} failed: {len(conflicts)} conflicts detected")
                
        except Exception as e:
            print(f"✗ Attempt {attempt + 1} failed with error: {str(e)}")
            
        # Clear state before next attempt
        clear_all_state(sections)
    
    # All attempts failed
    random.setstate(original_random_state)
    clear_all_state(sections)
    
    raise Exception(f"Could not generate conflict-free timetable after {max_attempts} attempts. "
                   f"This usually means:\n"
                   f"1. Teacher loads are too restrictive (try increasing max_load)\n"
                   f"2. Too many periods per week for subjects (try reducing)\n"
                   f"3. Lab block sizes are too large (try smaller blocks)\n"
                   f"4. Not enough teachers for the workload (try adding more teachers or reducing subject assignments)")

def clear_all_state(sections):
    """Clear all timetable and teacher load state for clean generation attempt."""
    for section in sections:
        section.timetable = [[None for _ in range(7)] for _ in range(6)]
        for subject in section.subjects:
            subject.teacher.current_load = 0

# Old original function removed - only conflict-free generation is now used
