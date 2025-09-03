import random

def generate_timetable(sections):
    """
    Generate timetables for all sections using the existing algorithm.
    First places lab subjects (which require consecutive periods),
    then places theory subjects one period at a time.
    """
    days = 6
    periods = 7

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
