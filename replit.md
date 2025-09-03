# Overview

This is a Flask-based web application for generating academic timetables for schools or colleges. The system manages teachers, subjects, sections, and automatically generates weekly timetables using a constraint-based algorithm. It handles both regular theory subjects and lab subjects that require consecutive periods, ensuring teacher workload limits are respected.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Flask with Jinja2 templating engine
- **UI Library**: Bootstrap with dark theme and Font Awesome icons
- **Design Pattern**: Server-side rendered templates with responsive design
- **Styling**: Custom CSS for timetable grid display with color-coded subjects

## Backend Architecture
- **Framework**: Flask web framework with session-based data storage
- **Data Models**: Simple Python classes (Teacher, Subject, Section) without ORM
- **Storage**: Flask sessions for temporary data persistence
- **Algorithm**: Custom constraint-based timetable generation with two-phase placement (labs first, then theory subjects)

## Core Components

### Data Models
- **Teacher**: Manages name, maximum teaching load, and current load tracking
- **Subject**: Handles subject details, assigned teacher, weekly periods, lab configuration, and block sizes
- **Section**: Represents class sections with assigned subjects and generated timetables

### Timetable Generation
- **Two-phase Algorithm**: Places lab subjects requiring consecutive periods first, then distributes theory subjects
- **Constraint Handling**: Respects teacher workload limits and time slot availability
- **Grid Structure**: 6 days × 7 periods weekly schedule

### Web Interface
- **Multi-page Navigation**: Separate pages for teachers, subjects, sections, and timetable generation
- **Form-based Input**: User-friendly forms for data entry with validation
- **Visual Timetable Display**: Color-coded grid showing subject assignments with teacher names

## External Dependencies

- **Flask**: Web framework for routing, templating, and session management
- **Bootstrap**: CSS framework for responsive UI design
- **Font Awesome**: Icon library for enhanced visual elements
- **Python Standard Library**: Random module for timetable generation algorithm

No database or external API integrations are currently implemented - all data is stored in Flask sessions.