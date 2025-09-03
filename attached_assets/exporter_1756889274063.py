def print_section_timetable(section):
    print(f"\nTimetable for {section.name} ({section.year})")
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    for d in range(6):
        row = []
        for p in range(7):
            subj = section.timetable[d][p]
            row.append(subj.name if subj else "--")
        print(days[d], " | ", " | ".join(row))
