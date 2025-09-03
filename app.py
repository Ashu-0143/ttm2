import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import Teacher, Subject, Section
from generator import generate_timetable
from exporter import format_timetable_for_web
from conflicts import detect_teacher_conflicts, get_conflict_summary, suggest_conflict_resolution, apply_conflict_resolution

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
    if 'saved_timetables' not in session:
        session['saved_timetables'] = []

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
        
        # Detect conflicts
        conflicts = detect_teacher_conflicts(generated_sections)
        conflict_summary = get_conflict_summary(conflicts)
        suggestions = suggest_conflict_resolution(conflicts, generated_sections) if conflicts else []
        
        # Store generated sections in session for editing
        session['generated_sections'] = []
        for section in generated_sections:
            # Convert section to serializable format
            section_data = {
                'name': section.name,
                'year': section.year,
                'subject_names': [s.name for s in section.subjects],
                'timetable': []
            }
            
            # Store timetable with subject names (not objects)
            for day in range(6):
                day_schedule = []
                for period in range(7):
                    subject = section.timetable[day][period]
                    if subject:
                        day_schedule.append({
                            'name': subject.name,
                            'teacher': subject.teacher.name,
                            'is_lab': subject.is_lab
                        })
                    else:
                        day_schedule.append(None)
                section_data['timetable'].append(day_schedule)
            
            session['generated_sections'].append(section_data)
        
        session.modified = True
        
        # Format timetables for web display
        timetables = []
        for section in generated_sections:
            timetable_data = format_timetable_for_web(section)
            timetables.append(timetable_data)
        
        # Show conflict warnings if any
        if conflicts:
            flash(f"⚠️ {len(conflicts)} teacher scheduling conflicts detected! Check the conflicts tab for details.", 'warning')
        
        return render_template('timetable.html', 
                             timetables=timetables,
                             conflicts=conflict_summary,
                             suggestions=suggestions,
                             has_conflicts=len(conflicts) > 0)
    
    except Exception as e:
        flash(f'Error generating timetable: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/edit_timetable')
def edit_timetable():
    """Display timetables in edit mode with conflict information"""
    init_session()
    
    if 'generated_sections' not in session or not session['generated_sections']:
        flash('No timetables generated yet. Please generate timetables first.', 'error')
        return redirect(url_for('generate_timetable_view'))
    
    # Reconstruct sections from session data for conflict detection
    teachers = {t['name']: Teacher(t['name'], t['max_load']) for t in session['teachers']}
    subjects_dict = {}
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
            subjects_dict[subject.name] = subject
    
    sections = []
    for section_data in session['generated_sections']:
        section_subjects = [subjects_dict[name] for name in section_data['subject_names'] if name in subjects_dict]
        section = Section(section_data['name'], section_data['year'], section_subjects)
        
        # Reconstruct timetable from stored data
        for day in range(6):
            for period in range(7):
                stored_subject = section_data['timetable'][day][period]
                if stored_subject:
                    subject = subjects_dict.get(stored_subject['name'])
                    section.timetable[day][period] = subject
    
        sections.append(section)
    
    # Detect current conflicts
    conflicts = detect_teacher_conflicts(sections)
    conflict_summary = get_conflict_summary(conflicts)
    suggestions = suggest_conflict_resolution(conflicts, sections)
    
    # Format for display
    timetables = []
    for section in sections:
        timetable_data = format_timetable_for_web(section)
        timetables.append(timetable_data)
    
    return render_template('edit_timetable.html',
                         timetables=timetables,
                         conflicts=conflict_summary,
                         suggestions=suggestions,
                         has_conflicts=len(conflicts) > 0)

@app.route('/move_subject', methods=['POST'])
def move_subject():
    """Move a subject from one time slot to another"""
    init_session()
    
    data = request.get_json()
    section_name = data.get('section_name')
    from_day = data.get('from_day')
    from_period = data.get('from_period')
    to_day = data.get('to_day')
    to_period = data.get('to_period')
    
    # Find the section in stored data
    section_data = next((s for s in session['generated_sections'] if s['name'] == section_name), None)
    if not section_data:
        return jsonify({'success': False, 'message': 'Section not found'})
    
    # Get subject from source position
    source_subject = section_data['timetable'][from_day][from_period]
    if not source_subject:
        return jsonify({'success': False, 'message': 'No subject at source position'})
    
    # Check if destination is empty
    dest_subject = section_data['timetable'][to_day][to_period]
    if dest_subject:
        return jsonify({'success': False, 'message': 'Destination slot is occupied'})
    
    # Move the subject
    section_data['timetable'][to_day][to_period] = source_subject
    section_data['timetable'][from_day][from_period] = None
    session.modified = True
    
    return jsonify({'success': True, 'message': f'Moved {source_subject["name"]} successfully'})

@app.route('/swap_subjects', methods=['POST'])
def swap_subjects():
    """Swap two subjects between time slots"""
    init_session()
    
    data = request.get_json()
    section_name = data.get('section_name')
    slot1_day = data.get('slot1_day')
    slot1_period = data.get('slot1_period')
    slot2_day = data.get('slot2_day')
    slot2_period = data.get('slot2_period')
    
    # Find the section in stored data
    section_data = next((s for s in session['generated_sections'] if s['name'] == section_name), None)
    if not section_data:
        return jsonify({'success': False, 'message': 'Section not found'})
    
    # Get subjects from both positions
    subject1 = section_data['timetable'][slot1_day][slot1_period]
    subject2 = section_data['timetable'][slot2_day][slot2_period]
    
    # Swap the subjects
    section_data['timetable'][slot1_day][slot1_period] = subject2
    section_data['timetable'][slot2_day][slot2_period] = subject1
    session.modified = True
    
    return jsonify({'success': True, 'message': 'Subjects swapped successfully'})

@app.route('/save_timetable', methods=['POST'])
def save_timetable():
    """Save the current edited timetable permanently"""
    init_session()
    
    if 'generated_sections' not in session or not session['generated_sections']:
        return jsonify({'success': False, 'message': 'No timetable to save'})
    
    # Store the current timetable as saved
    import time
    timestamp = int(time.time())
    
    saved_timetable = {
        'id': timestamp,
        'name': f"Saved Timetable - {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}",
        'sections': session['generated_sections'].copy(),
        'created_at': timestamp
    }
    
    session['saved_timetables'].append(saved_timetable)
    session.modified = True
    
    return jsonify({'success': True, 'message': 'Timetable saved successfully!', 'saved_id': timestamp})

@app.route('/load_saved_timetable/<int:saved_id>')
def load_saved_timetable(saved_id):
    """Load a previously saved timetable"""
    init_session()
    
    saved_timetable = next((st for st in session['saved_timetables'] if st['id'] == saved_id), None)
    if not saved_timetable:
        flash('Saved timetable not found.', 'error')
        return redirect(url_for('index'))
    
    # Load the saved timetable back into generated_sections
    session['generated_sections'] = saved_timetable['sections'].copy()
    session.modified = True
    
    flash(f'Loaded: {saved_timetable["name"]}', 'success')
    return redirect(url_for('edit_timetable'))

@app.route('/saved_timetables')
def saved_timetables():
    """Display all saved timetables"""
    init_session()
    
    saved_timetables = session.get('saved_timetables', [])
    # Sort by creation date, newest first
    saved_timetables = sorted(saved_timetables, key=lambda x: x['created_at'], reverse=True)
    
    return render_template('saved_timetables.html', saved_timetables=saved_timetables)

@app.route('/delete_saved_timetable/<int:saved_id>', methods=['POST'])
def delete_saved_timetable(saved_id):
    """Delete a saved timetable"""
    init_session()
    
    session['saved_timetables'] = [st for st in session['saved_timetables'] if st['id'] != saved_id]
    session.modified = True
    
    return jsonify({'success': True, 'message': 'Timetable deleted successfully'})

@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    """Convert timestamp to readable date"""
    import time
    return time.strftime('%Y-%m-%d %H:%M', time.localtime(timestamp))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
