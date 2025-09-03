import random

def generate_timetable(sections):
    days = 6
    periods = 7

    for section in sections:
        # Step 1: Place labs
        for subj in [s for s in section.subjects if s.is_lab]:
            placed = False
            while not placed:
                day = random.randint(0, days-1)
                start = random.randint(0, periods - subj.block_size)
                if all(section.timetable[day][p] is None for p in range(start, start + subj.block_size)):
                    for p in range(start, start + subj.block_size):
                        section.timetable[day][p] = subj
                    subj.teacher.current_load += subj.block_size
                    placed = True

        # Step 2: Place theories
        for subj in [s for s in section.subjects if not s.is_lab]:
            for _ in range(subj.periods_per_week):
                placed = False
                while not placed:
                    day = random.randint(0, days-1)
                    p = random.randint(0, periods-1)
                    if section.timetable[day][p] is None and subj.teacher.can_teach(1):
                        section.timetable[day][p] = subj
                        subj.teacher.current_load += 1
                        placed = True

    return sections
