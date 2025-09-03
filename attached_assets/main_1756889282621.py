from timetable.models import Teacher, Subject, Section
from timetable.generator import generate_timetable
from timetable.exporter import print_section_timetable

# Sample Teachers
t1 = Teacher("T1")
t2 = Teacher("T2")
t3 = Teacher("T3")

# Sample Subjects
math = Subject("Math-II", t1, 5)
mech = Subject("Mechanics", t2, 4)
prog_lab = Subject("Prog Lab", t3, 1, is_lab=True, block_size=4)

# Section A
secA = Section("CME-2A", "2nd Year", [math, mech, prog_lab])

# Generate timetable
sections = generate_timetable([secA])

# Print output
for sec in sections:
    print_section_timetable(sec)
