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
        # Calculate current load based on section assignments
        current_load = 0
        for section_data in session.get('sections', []):
            for assignment in section_data.get('subject_assignments', []):
                if assignment.get('teacher') == teacher.name:
                    # Find the subject to get periods per week
                    for subject_data in session.get('subjects', []):
                        if subject_data['name'] == assignment['subject']:
                            current_load += subject_data['periods_per_week']
                            break
        teacher.current_load = current_load
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
    # Check if teacher is being used in any section
    for section_data in session['sections']:
        if 'subject_assignments' in section_data:
            for assignment in section_data['subject_assignments']:
                if assignment.get('teacher_name') == teacher_name:
                    flash(f'Cannot delete teacher {teacher_name} as they are assigned to a subject in section {section_data["name"]}', 'error')
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
        subject = Subject(
            subject_data['name'],
            subject_data['periods_per_week'],
            subject_data['is_lab'],
            subject_data['block_size']
        )
        # Attach assigned teachers list for template rendering
        subject.teachers = subject_data.get('teachers', [])
        subjects.append(subject)
    return render_template('subjects.html', subjects=subjects, teachers=teachers)

@app.route('/add_subject', methods=['POST'])
def add_subject():
    # Add teachers to the subject
    teachers = request.form.getlist('teachers')
    
    init_session()
    name = request.form.get('name', '').strip()
    periods_per_week = request.form.get('periods_per_week', type=int)
    is_lab = 'is_lab' in request.form
    block_size = request.form.get('block_size', type=int) if is_lab else 1
    
    if not name:
        flash('Subject name is required', 'error')
        return redirect(url_for('subjects'))
    
    if not periods_per_week or periods_per_week <= 0:
        flash('Periods per week must be a positive number', 'error')
        return redirect(url_for('subjects'))
    
    if is_lab and (not block_size or block_size <= 0):
        flash('Block size must be a positive number for lab subjects', 'error')
        return redirect(url_for('subjects'))
    
    # Check if subject already exists
    for subject in session['subjects']:
        if subject['name'].lower() == name.lower():
            flash('Subject with this name already exists', 'error')
            return redirect(url_for('subjects'))
    
    session['subjects'].append({
        'name': name,
        'periods_per_week': periods_per_week,
        'is_lab': is_lab,
        'block_size': block_size or 1,
        'teachers': teachers
    })
    session.modified = True
    flash(f'Subject {name} added successfully', 'success')
    return redirect(url_for('subjects'))

@app.route('/delete_subject/<subject_name>')
def delete_subject(subject_name):
    init_session()
    # Check if subject is being used in any section
    for section_data in session['sections']:
        if 'subject_assignments' in section_data:
            for assignment in section_data['subject_assignments']:
                if assignment.get('subject_name') == subject_name:
                    flash(f'Cannot delete subject {subject_name} as it is assigned to section {section_data["name"]}', 'error')
                    return redirect(url_for('subjects'))
        elif 'subject_names' in section_data and subject_name in section_data['subject_names']:
            flash(f'Cannot delete subject {subject_name} as it is assigned to section {section_data["name"]}', 'error')
            return redirect(url_for('subjects'))
    
    session['subjects'] = [s for s in session['subjects'] if s['name'] != subject_name]
    session.modified = True
    flash(f'Subject {subject_name} deleted successfully', 'success')
    return redirect(url_for('subjects'))


@app.route('/sections')
def sections():
    init_session()
    teachers = [Teacher(t['name'], t['max_load']) for t in session['teachers']]
    subjects = []
    for subject_data in session['subjects']:
        subject = Subject(
            subject_data['name'],
            subject_data['periods_per_week'],
            subject_data['is_lab'],
            subject_data['block_size']
        )
        subject.teachers = subject_data.get('teachers', [])
        subjects.append(subject)
    # Prepare section data with subject-teacher assignments
    section_list = []
    for section_data in session['sections']:
        assignments = section_data.get('subject_assignments', [])
        section_subjects = []
        for subj_name in section_data.get('subject_names', []):
            subj = next((s for s in subjects if s.name == subj_name), None)
            teacher_name = None
            for a in assignments:
                if a['subject'] == subj_name:
                    teacher_name = a['teacher']
            section_subjects.append({'subject': subj, 'teacher': teacher_name})
        section_list.append({
            'name': section_data['name'],
            'year': section_data['year'],
            'subjects': section_subjects
        })
    return render_template('sections.html', sections=section_list, subjects=subjects, teachers=teachers)
    
@app.route('/assign_teachers_to_subject/<subject_name>', methods=['POST'])
def assign_teachers_to_subject(subject_name):
    init_session()
    selected_teachers = request.form.getlist('teachers')
    found = False
    for subject in session['subjects']:
        if subject['name'] == subject_name:
            subject['teachers'] = selected_teachers
            found = True
            break
    session.modified = True
    if found:
        flash(f'Teachers assigned to {subject_name} successfully.', 'success')
    else:
        flash(f'Subject {subject_name} not found.', 'error')
    return redirect(url_for('subjects'))


@app.route('/add_section', methods=['POST'])
def add_section():
    init_session()
    name = request.form.get('name', '').strip()
    year = request.form.get('year', '').strip()
    subject_names = request.form.getlist('subject_names')
    subject_assignments = []
    for subj_name in subject_names:
        teacher = request.form.get(f'teacher_for_{subj_name}')
        # Only allow selection from assigned teachers
        subject_data = next((s for s in session['subjects'] if s['name'] == subj_name), None)
        if subject_data and teacher and teacher not in subject_data.get('teachers', []):
            flash(f'Teacher {teacher} is not assigned to subject {subj_name}.', 'error')
            return redirect(url_for('sections'))
        subject_assignments.append({'subject': subj_name, 'teacher': teacher})
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
        'subject_names': subject_names,
        'subject_assignments': subject_assignments
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
    
    # Force regeneration by clearing any existing generated timetables
    if 'generated_sections' in session:
        del session['generated_sections']
    session.modified = True
    
    try:
        # Reset teacher loads
        for teacher_data in session['teachers']:
            teacher_data['current_load'] = 0
        # Create objects from session data
        teachers = {t['name']: Teacher(t['name'], t['max_load']) for t in session['teachers']}
        
        # Create a subject template lookup for creating section-specific instances
        subject_templates = {}
        for subject_data in session['subjects']:
            subject_templates[subject_data['name']] = subject_data
            
        sections = []
        for section_data in session['sections']:
            subject_assignments = []
            for assignment in section_data.get('subject_assignments', []):
                subject_name = assignment['subject']
                teacher_name = assignment['teacher']
                
                # Create a NEW subject instance for this specific section assignment
                if subject_name in subject_templates and teacher_name:
                    template = subject_templates[subject_name]
                    # Create a separate subject instance for this section
                    subject_instance = Subject(
                        template['name'],
                        template['periods_per_week'],
                        template['is_lab'],
                        template['block_size']
                    )
                    
                    teacher_obj = teachers.get(teacher_name)
                    if teacher_obj:
                        # Assign the specific teacher to this section's subject instance
                        subject_instance.teacher = teacher_obj
                        subject_assignments.append((subject_instance, teacher_obj))
                        
            section = Section(section_data['name'], section_data['year'], subject_assignments)
            sections.append(section)
        # Generate timetables
        generated_sections = generate_timetable(sections)
        
        # Detect conflicts
        conflicts = detect_teacher_conflicts(generated_sections)
        conflict_summary = get_conflict_summary(conflicts)
        suggestions = suggest_conflict_resolution(conflicts, generated_sections) if conflicts else []
        
        # Store generated sections in session for editing with complete teacher assignment data
        session['generated_sections'] = []
        for section in generated_sections:
            # Convert section to serializable format with complete teacher assignments
            subject_assignments = []
            for subject in section.subjects:
                if subject.teacher:
                    subject_assignments.append({
                        'subject': subject.name,
                        'teacher': subject.teacher.name
                    })
            
            section_data = {
                'name': section.name,
                'year': section.year,
                'subject_names': [s.name for s in section.subjects],
                'subject_assignments': subject_assignments,
                'timetable': []
            }
            
            # Store timetable with complete subject and teacher data
            for day in range(6):
                day_schedule = []
                for period in range(7):
                    subject = section.timetable[day][period]
                    if subject:
                        day_schedule.append({
                            'name': subject.name,
                            'teacher': subject.teacher.name if subject.teacher else 'Unassigned',
                            'is_lab': subject.is_lab,
                            'block_size': getattr(subject, 'block_size', 1)
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
    
    # Create subject templates for reference
    subject_templates = {}
    for subject_data in session['subjects']:
        subject_templates[subject_data['name']] = subject_data
    
    sections = []
    for section_data in session['generated_sections']:
        # Create subject assignments with proper teacher assignments from stored data
        section_subject_instances = {}  # Track subject instances for this specific section
        subject_assignments = []
        
        for assignment in section_data.get('subject_assignments', []):
            subject_name = assignment['subject']
            teacher_name = assignment['teacher']
            
            if subject_name in subject_templates and teacher_name in teachers:
                template = subject_templates[subject_name]
                # Create a NEW subject instance specifically for this section
                subject_instance = Subject(
                    template['name'],
                    template['periods_per_week'],
                    template['is_lab'],
                    template['block_size']
                )
                subject_instance.teacher = teachers[teacher_name]
                section_subject_instances[subject_name] = subject_instance
                subject_assignments.append((subject_instance, teachers[teacher_name]))
        
        section = Section(section_data['name'], section_data['year'], subject_assignments)
        
        # Reconstruct timetable from stored data with proper section-specific subject instances
        for day in range(6):
            for period in range(7):
                stored_subject = section_data['timetable'][day][period]
                if stored_subject:
                    subject_name = stored_subject['name']
                    teacher_name = stored_subject.get('teacher', '')
                    
                    # Use the section-specific subject instance
                    if subject_name in section_subject_instances:
                        subject_instance = section_subject_instances[subject_name]
                        # Ensure teacher is properly assigned from stored data
                        if teacher_name and teacher_name in teachers:
                            subject_instance.teacher = teachers[teacher_name]
                        section.timetable[day][period] = subject_instance
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

def display_index_to_timetable_index(display_period, lunch_position):
    """Convert display period index (0-7 including lunch) to timetable index (0-6 teaching periods)"""
    if display_period == lunch_position:
        return None  # This is lunch, not a teaching period
    elif display_period < lunch_position:
        return display_period  # Before lunch, same index
    else:
        return display_period - 1  # After lunch, subtract 1

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
    
    # Get lunch position (assume 4th position - between 3rd and 4th period)
    lunch_position = 4
    
    # Convert display indices to timetable indices
    from_timetable_period = display_index_to_timetable_index(from_period, lunch_position)
    to_timetable_period = display_index_to_timetable_index(to_period, lunch_position)
    
    # Check if trying to move from/to lunch slot
    if from_timetable_period is None:
        return jsonify({'success': False, 'message': 'Cannot move from lunch period'})
    if to_timetable_period is None:
        return jsonify({'success': False, 'message': 'Cannot move to lunch period'})
    
    # Get subject from source position
    source_subject = section_data['timetable'][from_day][from_timetable_period]
    if not source_subject:
        return jsonify({'success': False, 'message': 'No subject at source position'})
    
    # Check if destination is empty
    dest_subject = section_data['timetable'][to_day][to_timetable_period]
    if dest_subject:
        return jsonify({'success': False, 'message': 'Destination slot is occupied'})
    
    # Move the subject
    section_data['timetable'][to_day][to_timetable_period] = source_subject
    section_data['timetable'][from_day][from_timetable_period] = None
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
    
    # Get lunch position (assume 4th position - between 3rd and 4th period)
    lunch_position = 4
    
    # Convert display indices to timetable indices
    slot1_timetable_period = display_index_to_timetable_index(slot1_period, lunch_position)
    slot2_timetable_period = display_index_to_timetable_index(slot2_period, lunch_position)
    
    # Check if trying to swap with lunch slot
    if slot1_timetable_period is None or slot2_timetable_period is None:
        return jsonify({'success': False, 'message': 'Cannot swap with lunch period'})
    
    # Get subjects from both positions
    subject1 = section_data['timetable'][slot1_day][slot1_timetable_period]
    subject2 = section_data['timetable'][slot2_day][slot2_timetable_period]
    
    # Swap the subjects
    section_data['timetable'][slot1_day][slot1_timetable_period] = subject2
    section_data['timetable'][slot2_day][slot2_timetable_period] = subject1
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
    return redirect(url_for('view_saved_timetable', saved_id=saved_id))

@app.route('/saved_timetables')
def saved_timetables():
    """Display all saved timetables"""
    init_session()
    
    saved_timetables = session.get('saved_timetables', [])
    # Sort by creation date, newest first
    saved_timetables = sorted(saved_timetables, key=lambda x: x['created_at'], reverse=True)
    
    return render_template('saved_timetables.html', saved_timetables=saved_timetables)

@app.route('/view_current_timetable')
def view_current_timetable():
    """View the current edited timetable without regenerating"""
    init_session()
    
    if 'generated_sections' not in session or not session['generated_sections']:
        flash('No timetables available. Please generate timetables first.', 'error')
        return redirect(url_for('generate_timetable_view'))
    
    # Reconstruct sections from session data for conflict detection
    teachers = {t['name']: Teacher(t['name'], t['max_load']) for t in session['teachers']}
    subjects_dict = {}
    for subject_data in session['subjects']:
        subject = Subject(
            subject_data['name'],
            subject_data['periods_per_week'],
            subject_data['is_lab'],
            subject_data['block_size']
        )
        subjects_dict[subject.name] = subject
    
    sections = []
    for section_data in session['generated_sections']:
        # Create subject assignments with proper teacher assignments from stored data
        subject_assignments = []
        for assignment in section_data.get('subject_assignments', []):
            subj = subjects_dict.get(assignment['subject'])
            teacher_obj = teachers.get(assignment['teacher'])
            if subj and teacher_obj:
                subj.teacher = teacher_obj
                subject_assignments.append((subj, teacher_obj))
        
        section = Section(section_data['name'], section_data['year'], subject_assignments)
        
        # Reconstruct timetable from stored data
        for day in range(6):
            for period in range(7):
                stored_subject = section_data['timetable'][day][period]
                if stored_subject:
                    subject = subjects_dict.get(stored_subject['name'])
                    section.timetable[day][period] = subject
        
        sections.append(section)
    
    # Detect conflicts in current timetable
    conflicts = detect_teacher_conflicts(sections)
    conflict_summary = get_conflict_summary(conflicts)
    suggestions = suggest_conflict_resolution(conflicts, sections) if conflicts else []
    
    # Format timetables for web display
    timetables = []
    for section in sections:
        timetable_data = format_timetable_for_web(section)
        timetables.append(timetable_data)
    
    return render_template('timetable.html', 
                         timetables=timetables,
                         conflicts=conflict_summary,
                         suggestions=suggestions,
                         has_conflicts=len(conflicts) > 0)

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

@app.route('/remove_teacher_from_section/<section_name>/<subject_name>', methods=['POST'])
def remove_teacher_from_section(section_name, subject_name):
    init_session()
    for section in session['sections']:
        if section['name'] == section_name:
            for assignment in section.get('subject_assignments', []):
                if assignment['subject'] == subject_name:
                    assignment['teacher'] = None
                    break
            break
    session.modified = True
    flash(f'Removed teacher from {subject_name} in {section_name}.', 'success')
    return redirect(url_for('sections'))

@app.route('/remove_teacher_from_subject/<subject_name>/<teacher_name>', methods=['POST'])
def remove_teacher_from_subject(subject_name, teacher_name):
    init_session()
    for subject in session['subjects']:
        if subject['name'] == subject_name:
            if 'teachers' in subject and teacher_name in subject['teachers']:
                subject['teachers'].remove(teacher_name)
                session.modified = True
                flash(f'Removed {teacher_name} from {subject_name}.', 'success')
            break
    return redirect(url_for('subjects'))

@app.route('/export_data')
def export_data():
    """Export all session data as a JSON file"""
    import json
    import time
    from flask import Response
    
    init_session()
    
    # Collect all data from session
    export_data = {
        'teachers': session.get('teachers', []),
        'subjects': session.get('subjects', []),
        'sections': session.get('sections', []),
        'saved_timetables': session.get('saved_timetables', []),
        'generated_sections': session.get('generated_sections', []),
        'export_timestamp': int(time.time()),
        'version': '1.0'
    }
    
    json_str = json.dumps(export_data, indent=2)
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filename = f'timetable_data_{timestamp}.json'
    
    return Response(
        json_str,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/import_data', methods=['GET', 'POST'])
def import_data():
    """Import data from uploaded JSON file"""
    import json
    
    init_session()
    
    if request.method == 'GET':
        return render_template('import_data.html')
    
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('import_data'))
    
    file = request.files['file']
    if file.filename == '' or file.filename is None:
        flash('No file selected', 'error')
        return redirect(url_for('import_data'))
    
    if not file.filename.lower().endswith('.json'):
        flash('Please upload a JSON file', 'error')
        return redirect(url_for('import_data'))
    
    try:
        # Read and parse JSON data
        file_content = file.read().decode('utf-8')
        imported_data = json.loads(file_content)
        
        # Validate required fields
        required_fields = ['teachers', 'subjects', 'sections', 'saved_timetables']
        for field in required_fields:
            if field not in imported_data:
                flash(f'Invalid file format: missing {field} data', 'error')
                return redirect(url_for('import_data'))
        
        # Import data into session
        session['teachers'] = imported_data['teachers']
        session['subjects'] = imported_data['subjects']
        session['sections'] = imported_data['sections']
        session['saved_timetables'] = imported_data['saved_timetables']
        
        # Import generated sections if available
        if 'generated_sections' in imported_data:
            session['generated_sections'] = imported_data['generated_sections']
        
        session.modified = True
        
        # Show summary of imported data
        summary = []
        summary.append(f"{len(imported_data['teachers'])} teachers")
        summary.append(f"{len(imported_data['subjects'])} subjects")
        summary.append(f"{len(imported_data['sections'])} sections")
        summary.append(f"{len(imported_data['saved_timetables'])} saved timetables")
        
        flash(f'Successfully imported: {", ".join(summary)}', 'success')
        return redirect(url_for('index'))
        
    except json.JSONDecodeError:
        flash('Invalid JSON file format', 'error')
        return redirect(url_for('import_data'))
    except Exception as e:
        flash(f'Error importing file: {str(e)}', 'error')
        return redirect(url_for('import_data'))

@app.route('/view_saved_timetable/<int:saved_id>')
def view_saved_timetable(saved_id):
    """View a saved timetable in read-only mode"""
    init_session()
    
    saved_timetable = next((st for st in session['saved_timetables'] if st['id'] == saved_id), None)
    if not saved_timetable:
        flash('Saved timetable not found.', 'error')
        return redirect(url_for('saved_timetables'))
    
    # Reconstruct sections from saved timetable data for display
    teachers = {t['name']: Teacher(t['name'], t['max_load']) for t in session['teachers']}
    
    subject_templates = {}
    for subject_data in session['subjects']:
        subject_templates[subject_data['name']] = subject_data
    
    sections = []
    for section_data in saved_timetable['sections']:
        section_subject_instances = {}
        subject_assignments = []
        
        for assignment in section_data.get('subject_assignments', []):
            subject_name = assignment['subject']
            teacher_name = assignment['teacher']
            
            if subject_name in subject_templates and teacher_name in teachers:
                template = subject_templates[subject_name]
                subject_instance = Subject(
                    template['name'],
                    template['periods_per_week'],
                    template['is_lab'],
                    template['block_size']
                )
                subject_instance.teacher = teachers[teacher_name]
                section_subject_instances[subject_name] = subject_instance
                subject_assignments.append((subject_instance, teachers[teacher_name]))
        
        section = Section(section_data['name'], section_data['year'], subject_assignments)
        
        for day in range(6):
            for period in range(7):
                stored_subject = section_data['timetable'][day][period]
                if stored_subject:
                    subject_name = stored_subject['name']
                    if subject_name in section_subject_instances:
                        section.timetable[day][period] = section_subject_instances[subject_name]
        
        sections.append(section)
    
    conflicts = detect_teacher_conflicts(sections)
    conflict_summary = get_conflict_summary(conflicts)
    
    timetables = []
    for section in sections:
        timetable_data = format_timetable_for_web(section)
        timetables.append(timetable_data)
    
    return render_template('view_saved_timetable.html', 
                         timetables=timetables,
                         conflicts=conflict_summary,
                         has_conflicts=len(conflicts) > 0,
                         saved_id=saved_id,
                         saved_name=saved_timetable['name'])

@app.route('/regenerate_saved_timetable/<int:saved_id>')
def regenerate_saved_timetable(saved_id):
    """Regenerate a saved timetable with new randomization"""
    init_session()
    
    saved_timetable = next((st for st in session['saved_timetables'] if st['id'] == saved_id), None)
    if not saved_timetable:
        flash('Saved timetable not found.', 'error')
        return redirect(url_for('saved_timetables'))
    
    if not session['sections']:
        flash('No sections available. Cannot regenerate.', 'error')
        return redirect(url_for('sections'))
    
    try:
        for teacher_data in session['teachers']:
            teacher_data['current_load'] = 0
        
        teachers = {t['name']: Teacher(t['name'], t['max_load']) for t in session['teachers']}
        subject_templates = {}
        for subject_data in session['subjects']:
            subject_templates[subject_data['name']] = subject_data
            
        sections = []
        for section_data in session['sections']:
            subject_assignments = []
            for assignment in section_data.get('subject_assignments', []):
                subject_name = assignment['subject']
                teacher_name = assignment['teacher']
                
                if subject_name in subject_templates and teacher_name:
                    template = subject_templates[subject_name]
                    subject_instance = Subject(
                        template['name'],
                        template['periods_per_week'],
                        template['is_lab'],
                        template['block_size']
                    )
                    
                    teacher_obj = teachers.get(teacher_name)
                    if teacher_obj:
                        subject_instance.teacher = teacher_obj
                        subject_assignments.append((subject_instance, teacher_obj))
                        
            section = Section(section_data['name'], section_data['year'], subject_assignments)
            sections.append(section)
        
        generated_sections = generate_timetable(sections)
        
        session['generated_sections'] = []
        for section in generated_sections:
            subject_assignments = []
            for subject in section.subjects:
                if subject.teacher:
                    subject_assignments.append({
                        'subject': subject.name,
                        'teacher': subject.teacher.name
                    })
            
            section_data = {
                'name': section.name,
                'year': section.year,
                'subject_assignments': subject_assignments,
                'timetable': []
            }
            
            for day in range(6):
                day_schedule = []
                for period in range(7):
                    cell = section.timetable[day][period]
                    if cell:
                        day_schedule.append({
                            'name': cell.name,
                            'is_lab': cell.is_lab,
                            'teacher': cell.teacher.name if cell.teacher else ''
                        })
                    else:
                        day_schedule.append(None)
                section_data['timetable'].append(day_schedule)
            
            session['generated_sections'].append(section_data)
        
        session['saved_timetables'] = [st for st in session['saved_timetables'] if st['id'] != saved_id]
        
        import time
        new_timestamp = int(time.time())
        new_saved_timetable = {
            'id': new_timestamp,
            'name': f"Regenerated - {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_timestamp))}",
            'sections': session['generated_sections'].copy(),
            'created_at': new_timestamp
        }
        
        session['saved_timetables'].append(new_saved_timetable)
        session.modified = True
        
        flash('Timetable regenerated successfully with new randomization!', 'success')
        return redirect(url_for('view_saved_timetable', saved_id=new_timestamp))
        
    except Exception as e:
        flash(f'Error regenerating timetable: {str(e)}', 'error')
        return redirect(url_for('saved_timetables'))

@app.route('/reset_all_data', methods=['POST'])
def reset_all_data():
    """Reset all data - clears teachers, subjects, sections, saved timetables, and generated sections"""
    init_session()
    
    session['teachers'] = []
    session['subjects'] = []
    session['sections'] = []
    session['saved_timetables'] = []
    if 'generated_sections' in session:
        del session['generated_sections']
    session.modified = True
    
    flash('All data has been reset successfully.', 'success')
    return jsonify({'success': True, 'message': 'All data has been reset successfully.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
