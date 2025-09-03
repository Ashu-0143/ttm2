import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import Teacher, Subject, Section
from generator import generate_timetable
from exporter import format_timetable_for_web

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Initialize session data structure
def init_session():
    if 'teachers' not in session:
        session['teachers'] = []
    if 'subjects' not in session:
        session['subjects'] = []
    if 'sections' not in session:
        session['sections'] = []

@app.route('/')
def index():
    init_session()
    return render_template('index.html')

@app.route('/teachers')
def teachers():
    init_session()
    teachers = []
    for teacher_data in session['teachers']:
        teacher = Teacher(teacher_data['name'], teacher_data['max_load'])
        teacher.current_load = teacher_data.get('current_load', 0)
        teachers.append(teacher)
    return render_template('teachers.html', teachers=teachers)

@app.route('/add_teacher', methods=['POST'])
def add_teacher():
    init_session()
    name = request.form.get('name', '').strip()
    max_load = request.form.get('max_load', type=int)
    
    if not name:
        flash('Teacher name is required', 'error')
        return redirect(url_for('teachers'))
    
    if not max_load or max_load <= 0:
        flash('Maximum load must be a positive number', 'error')
        return redirect(url_for('teachers'))
    
    # Check if teacher already exists
    for teacher in session['teachers']:
        if teacher['name'].lower() == name.lower():
            flash('Teacher with this name already exists', 'error')
            return redirect(url_for('teachers'))
    
    session['teachers'].append({
        'name': name,
        'max_load': max_load,
        'current_load': 0
    })
    session.modified = True
    flash(f'Teacher {name} added successfully', 'success')
    return redirect(url_for('teachers'))

@app.route('/delete_teacher/<teacher_name>')
def delete_teacher(teacher_name):
    init_session()
    # Check if teacher is being used in any subject
    for subject in session['subjects']:
        if subject['teacher_name'] == teacher_name:
            flash(f'Cannot delete teacher {teacher_name} as they are assigned to subject {subject["name"]}', 'error')
            return redirect(url_for('teachers'))
    
    session['teachers'] = [t for t in session['teachers'] if t['name'] != teacher_name]
    session.modified = True
    flash(f'Teacher {teacher_name} deleted successfully', 'success')
    return redirect(url_for('teachers'))

@app.route('/subjects')
def subjects():
    init_session()
    teachers = [Teacher(t['name'], t['max_load']) for t in session['teachers']]
    subjects = []
    for subject_data in session['subjects']:
        teacher = next((t for t in teachers if t.name == subject_data['teacher_name']), None)
        if teacher:
            subject = Subject(
                subject_data['name'],
                teacher,
                subject_data['periods_per_week'],
                subject_data['is_lab'],
                subject_data['block_size']
            )
            subjects.append(subject)
    return render_template('subjects.html', subjects=subjects, teachers=teachers)

@app.route('/add_subject', methods=['POST'])
def add_subject():
    init_session()
    name = request.form.get('name', '').strip()
    teacher_name = request.form.get('teacher_name')
    periods_per_week = request.form.get('periods_per_week', type=int)
    is_lab = 'is_lab' in request.form
    block_size = request.form.get('block_size', type=int) if is_lab else 1
    
    if not name:
        flash('Subject name is required', 'error')
        return redirect(url_for('subjects'))
    
    if not teacher_name:
        flash('Teacher must be selected', 'error')
        return redirect(url_for('subjects'))
    
    if not periods_per_week or periods_per_week <= 0:
        flash('Periods per week must be a positive number', 'error')
        return redirect(url_for('subjects'))
    
    if is_lab and (not block_size or block_size <= 0):
        flash('Block size must be a positive number for lab subjects', 'error')
        return redirect(url_for('subjects'))
    
    # Check if teacher exists
    teacher_exists = any(t['name'] == teacher_name for t in session['teachers'])
    if not teacher_exists:
        flash('Selected teacher does not exist', 'error')
        return redirect(url_for('subjects'))
    
    # Check if subject already exists
    for subject in session['subjects']:
        if subject['name'].lower() == name.lower():
            flash('Subject with this name already exists', 'error')
            return redirect(url_for('subjects'))
    
    session['subjects'].append({
        'name': name,
        'teacher_name': teacher_name,
        'periods_per_week': periods_per_week,
        'is_lab': is_lab,
        'block_size': block_size or 1
    })
    session.modified = True
    flash(f'Subject {name} added successfully', 'success')
    return redirect(url_for('subjects'))

@app.route('/delete_subject/<subject_name>')
def delete_subject(subject_name):
    init_session()
    # Check if subject is being used in any section
    for section in session['sections']:
        if subject_name in section['subject_names']:
            flash(f'Cannot delete subject {subject_name} as it is assigned to section {section["name"]}', 'error')
            return redirect(url_for('subjects'))
    
    session['subjects'] = [s for s in session['subjects'] if s['name'] != subject_name]
    session.modified = True
    flash(f'Subject {subject_name} deleted successfully', 'success')
    return redirect(url_for('subjects'))

@app.route('/sections')
def sections():
    init_session()
    teachers = {t['name']: Teacher(t['name'], t['max_load']) for t in session['teachers']}
    subjects = []
    for subject_data in session['subjects']:
        teacher = teachers.get(subject_data['teacher_name'])
        if teacher:
            subject = Subject(
                subject_data['name'],
                teacher,
                subject_data['periods_per_week'],
                subject_data['is_lab'],
                subject_data['block_size']
            )
            subjects.append(subject)
    
    sections = []
    for section_data in session['sections']:
        section_subjects = [s for s in subjects if s.name in section_data['subject_names']]
        section = Section(section_data['name'], section_data['year'], section_subjects)
        sections.append(section)
    
    return render_template('sections.html', sections=sections, subjects=subjects)

@app.route('/add_section', methods=['POST'])
def add_section():
    init_session()
    name = request.form.get('name', '').strip()
    year = request.form.get('year', '').strip()
    subject_names = request.form.getlist('subject_names')
    
    if not name:
        flash('Section name is required', 'error')
        return redirect(url_for('sections'))
    
    if not year:
        flash('Year is required', 'error')
        return redirect(url_for('sections'))
    
    if not subject_names:
        flash('At least one subject must be selected', 'error')
        return redirect(url_for('sections'))
    
    # Check if section already exists
    for section in session['sections']:
        if section['name'].lower() == name.lower():
            flash('Section with this name already exists', 'error')
            return redirect(url_for('sections'))
    
    session['sections'].append({
        'name': name,
        'year': year,
        'subject_names': subject_names
    })
    session.modified = True
    flash(f'Section {name} added successfully', 'success')
    return redirect(url_for('sections'))

@app.route('/delete_section/<section_name>')
def delete_section(section_name):
    init_session()
    session['sections'] = [s for s in session['sections'] if s['name'] != section_name]
    session.modified = True
    flash(f'Section {section_name} deleted successfully', 'success')
    return redirect(url_for('sections'))

@app.route('/generate_timetable')
def generate_timetable_view():
    init_session()
    
    if not session['sections']:
        flash('No sections available. Please add at least one section.', 'error')
        return redirect(url_for('sections'))
    
    try:
        # Reset teacher loads
        for teacher_data in session['teachers']:
            teacher_data['current_load'] = 0
        
        # Create objects from session data
        teachers = {t['name']: Teacher(t['name'], t['max_load']) for t in session['teachers']}
        subjects = []
        for subject_data in session['subjects']:
            teacher = teachers.get(subject_data['teacher_name'])
            if teacher:
                subject = Subject(
                    subject_data['name'],
                    teacher,
                    subject_data['periods_per_week'],
                    subject_data['is_lab'],
                    subject_data['block_size']
                )
                subjects.append(subject)
        
        sections = []
        for section_data in session['sections']:
            section_subjects = [s for s in subjects if s.name in section_data['subject_names']]
            section = Section(section_data['name'], section_data['year'], section_subjects)
            sections.append(section)
        
        # Generate timetables
        generated_sections = generate_timetable(sections)
        
        # Format timetables for web display
        timetables = []
        for section in generated_sections:
            timetable_data = format_timetable_for_web(section)
            timetables.append(timetable_data)
        
        return render_template('timetable.html', timetables=timetables)
    
    except Exception as e:
        flash(f'Error generating timetable: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
