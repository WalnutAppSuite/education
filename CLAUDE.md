# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Unity ERP Context

**This app is part of Unity ERP** - a comprehensive educational institution management system serving schools with complete student lifecycle management.

**📖 For complete Unity business context, see:** `UNITY_CONTEXT.md` in this directory.

### App Role in Unity Ecosystem
**education** is the **foundational core module** that provides the base educational DocTypes and workflows that Unity ERP extends. This app establishes the fundamental data models and processes that all other Unity educational modules build upon.

### Cross-Module Dependencies
- **edu_quality**: Extends and customizes core education DocTypes with Unity-specific functionality
- **walnut_hrms**: Teacher and instructor management integration
- **erpnext**: Accounting integration for fee collection and financial management
- **frappe**: Core framework providing the foundation for all DocType definitions

### Educational Domain Impact
This app provides the **foundational data model** for Unity ERP's educational functionality:
1. **Core DocTypes**: Student, Guardian, Program, Course, Assessment Group
2. **Base Workflows**: Student lifecycle, program enrollment, fee structure
3. **Academic Structure**: Programs, courses, topics, academic years
4. **Assessment Framework**: Base assessment and grading systems
5. **ERPNext Integration**: Student as party type for accounting integration

## Overview

**education** is the core foundation module that provides essential DocTypes and workflows for educational institution management within Unity ERP. It establishes the fundamental data models and processes that all Unity educational functionality builds upon.

## Architecture

### Core Data Models

1. **Student Management**
   - `Student` - Core student records with personal details, guardians, address
   - `Student Applicant` - Application workflow management
   - `Guardian` - Parent/guardian information and relationships
   - `Student Group` - Batch/class organization
   - `Student Admission` - Web-based admission process

2. **Academic Structure**
   - `Program` - Degree/certification programs
   - `Course` - Individual subjects within programs
   - `Topic` - Content organization within courses
   - `Academic Year/Term` - Time-based organization
   - `Program Enrollment` - Student-program relationships

3. **Fee Management**
   - `Fee Structure` - Template for fee components
   - `Fee Schedule` - Fee due dates and scheduling
   - `Fees` - Individual fee records per student
   - `Fee Category` - Classification of different fee types

4. **Assessment System**
   - `Assessment Plan` - Scheduled assessments
   - `Assessment Group` - Hierarchical assessment organization
   - `Assessment Result` - Individual student results
   - `Assessment Criteria` - Grading standards
   - `Grading Scale` - Grade boundaries and classifications

5. **Content and Learning**
   - `Article` - Text-based content
   - `Video` - Video content integration
   - `Quiz` - Interactive assessments
   - `Question` - Quiz question bank
   - `Course Activity` - Learning activities
   - `Topic Content` - Structured content delivery

6. **Scheduling and Attendance**
   - `Course Schedule` - Class timetables
   - `Student Attendance` - Attendance tracking
   - `Room` - Physical classroom management
   - `Instructor` - Teacher/faculty management

## Key Commands

### Development
```bash
# Start development server
bench start

# Build app
bench build --app education

# Install app on site
bench --site [site_name] install-app education
```

### Testing
```bash
# Run app tests
bench --site [site_name] run-tests --app education

# Run specific test modules
bench --site [site_name] run-tests --module education.tests.test_student
```

### Database Operations
```bash
# Apply migrations
bench --site [site_name] migrate

# Access database console
bench --site [site_name] mariadb
```

## Key Integration Points

### ERPNext Integration
- **Student as Party Type**: Integrates with ERPNext accounting for fee collection
- **Department Linkage**: Connects with organizational structure
- **Payment Integration**: Fee collection linked to payment entries

### Website Integration
- **Student Portals**: Fee payments and admission access
- **Public Admission Forms**: Web-based application process
- **Website Generators**: Automated admission page creation

### Framework Integration
- **Calendar Integration**: Course schedules appear in Frappe calendar
- **Tree View**: Assessment groups organized hierarchically
- **Global Search**: All education DocTypes searchable
- **Role-based Access**: Student role with portal permissions

## Development Patterns

### Student Lifecycle Pattern
```
Student Applicant → Student → Program Enrollment → Fee Generation → Assessment → Graduation
```

### Academic Structure Pattern
```
Program → Course → Topic → Topic Content → Assessment Plan → Assessment Result
```

### Fee Management Pattern
```
Fee Structure → Fee Schedule → Fee Generation → Payment Collection → Accounting Integration
```

## Tools and Utilities

### Bulk Operations
- **Course Scheduling Tool**: Automated timetable generation
- **Student Attendance Tool**: Bulk attendance marking
- **Program Enrollment Tool**: Batch enrollment processing
- **Assessment Result Tool**: Bulk result entry

### Reporting
- **Fee Collection Reports**: Program-wise, student-wise analysis
- **Attendance Reports**: Monthly sheets, absent student tracking
- **Assessment Reports**: Course-wise, final grades
- **Student Contact Details**: Guardian and emergency contacts

### Portal Features
- **Student Portal**: Fees and admission access
- **Guardian Portal**: Student information access
- **Public Forms**: Admission workflow integration

## Extensibility Points

### Custom App Integration
The education app is designed as a foundation for custom apps to extend:
- **DocType Overrides**: Custom business logic in child apps
- **Hook System**: Event-driven customizations
- **Custom Fields**: Institution-specific data requirements
- **API Extensions**: External system integrations

### Installation Features
- Creates "Student" party type for accounting integration
- Sets up "Student" role with portal access
- Creates parent assessment group structure
- Configures default permissions and workflows

## Migration History

### Major Changes
- **v14.0**: LMS functionality moved to separate "Frappe LMS" app
- **Enhanced Student Party Type**: Better accounting integration
- **Assessment Group Structure**: Improved hierarchical organization
- **Student Name Handling**: Better name field management

## Dependencies

### Required Apps
- **ERPNext**: Core business application framework
- **Frappe**: Underlying web framework

### Optional Integrations
- **Frappe LMS**: Learning Management System (separate app)
- **HRMS**: Teacher and staff management
- **Accounting**: Fee collection and financial reporting

## Performance Considerations

### Database Design
- **Efficient Indexing**: Core fields indexed for fast queries
- **Hierarchical Structure**: Tree-based organization for scalability
- **Bulk Operations**: Optimized for large student populations

### Web Performance
- **Portal Optimization**: Student-specific data filtering
- **Website Caching**: Public admission forms cached
- **Search Performance**: Full-text search across education content

## Security and Permissions

### Role-Based Access
- **Student Role**: Portal access with restricted permissions
- **Instructor Role**: Course and assessment management
- **Academic User**: Full academic operations access
- **Administrator**: Complete system access

### Data Protection
- **Student Data Privacy**: Restricted access to personal information
- **Guardian Information**: Secure parent/guardian data handling
- **Assessment Security**: Protected grade and result data