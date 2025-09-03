"""
Conflict detection and resolution system for timetable generation.
Helps identify and resolve teacher scheduling conflicts across sections.
"""

def detect_teacher_conflicts(sections):
    """
    Detect scheduling conflicts where teachers are assigned to multiple sections
    at the same time slot.
    
    Returns a list of conflicts with details about the clashing assignments.
    """
    conflicts = []
    days = 6
    periods = 7
    
    # Create a mapping of teacher -> time slot -> sections
    teacher_schedule = {}
    
    for section in sections:
        for day in range(days):
            for period in range(periods):
                subject = section.timetable[day][period]
                if subject and subject.teacher:
                    teacher_name = subject.teacher.name
                    time_slot = (day, period)
                    
                    if teacher_name not in teacher_schedule:
                        teacher_schedule[teacher_name] = {}
                    
                    if time_slot not in teacher_schedule[teacher_name]:
                        teacher_schedule[teacher_name][time_slot] = []
                    
                    teacher_schedule[teacher_name][time_slot].append({
                        'section': section,
                        'subject': subject,
                        'day': day,
                        'period': period
                    })
    
    # Find conflicts (teacher in multiple sections at same time)
    for teacher_name, schedule in teacher_schedule.items():
        for time_slot, assignments in schedule.items():
            if len(assignments) > 1:
                day, period = time_slot
                conflicts.append({
                    'teacher': teacher_name,
                    'day': day,
                    'period': period,
                    'assignments': assignments,
                    'conflict_type': 'teacher_overlap'
                })
    
    return conflicts

def get_conflict_summary(conflicts):
    """
    Generate a human-readable summary of conflicts.
    """
    if not conflicts:
        return "No scheduling conflicts detected."
    
    summary = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    
    for conflict in conflicts:
        day_name = days[conflict['day']]
        period_num = conflict['period'] + 1
        teacher = conflict['teacher']
        
        sections = [assign['section'].name for assign in conflict['assignments']]
        subjects = [assign['subject'].name for assign in conflict['assignments']]
        
        summary.append({
            'teacher': teacher,
            'time': f"{day_name}, Period {period_num}",
            'sections': sections,
            'subjects': subjects,
            'message': f"Teacher {teacher} is scheduled in multiple sections ({', '.join(sections)}) at {day_name}, Period {period_num}"
        })
    
    return summary

def suggest_conflict_resolution(conflicts, sections):
    """
    Suggest possible resolutions for scheduling conflicts.
    """
    suggestions = []
    
    for conflict in conflicts:
        teacher = conflict['teacher']
        day = conflict['day']
        period = conflict['period']
        assignments = conflict['assignments']
        
        # Find alternative time slots for conflicting assignments
        for i, assignment in enumerate(assignments[1:], 1):  # Keep first assignment, move others
            section = assignment['section']
            subject = assignment['subject']
            
            # Find free slots for this subject
            alternative_slots = []
            for alt_day in range(6):
                for alt_period in range(7):
                    if section.timetable[alt_day][alt_period] is None:
                        alternative_slots.append((alt_day, alt_period))
            
            suggestions.append({
                'conflict_teacher': teacher,
                'conflict_time': f"Day {day+1}, Period {period+1}",
                'move_section': section.name,
                'move_subject': subject.name,
                'alternative_slots': alternative_slots[:5],  # Show first 5 alternatives
                'suggestion': f"Move {subject.name} from {section.name} to an available time slot"
            })
    
    return suggestions

def apply_conflict_resolution(sections, resolution_data):
    """
    Apply a manual conflict resolution by moving a subject to a different time slot.
    
    resolution_data should contain:
    - section_name: name of section to modify
    - from_day, from_period: current position
    - to_day, to_period: new position
    """
    section = next((s for s in sections if s.name == resolution_data['section_name']), None)
    if not section:
        return False, "Section not found"
    
    from_day = resolution_data['from_day']
    from_period = resolution_data['from_period']
    to_day = resolution_data['to_day']
    to_period = resolution_data['to_period']
    
    # Check if source slot has a subject
    subject = section.timetable[from_day][from_period]
    if not subject:
        return False, "No subject found at source position"
    
    # Check if destination slot is empty
    if section.timetable[to_day][to_period] is not None:
        return False, "Destination slot is not empty"
    
    # Move the subject
    section.timetable[to_day][to_period] = subject
    section.timetable[from_day][from_period] = None
    
    return True, f"Moved {subject.name} successfully"

def validate_timetable_integrity(sections):
    """
    Validate that timetables maintain integrity after edits.
    Check for proper period counts and teacher load constraints.
    """
    issues = []
    
    for section in sections:
        # Count periods for each subject
        subject_counts = {}
        for day in range(6):
            for period in range(7):
                subject = section.timetable[day][period]
                if subject:
                    if subject.name not in subject_counts:
                        subject_counts[subject.name] = 0
                    subject_counts[subject.name] += 1
        
        # Check if period counts match expected
        for subject in section.subjects:
            actual_count = subject_counts.get(subject.name, 0)
            if actual_count != subject.periods_per_week:
                issues.append({
                    'type': 'period_count_mismatch',
                    'section': section.name,
                    'subject': subject.name,
                    'expected': subject.periods_per_week,
                    'actual': actual_count
                })
    
    return issues