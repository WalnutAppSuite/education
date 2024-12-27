# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from education.education.api import enroll_student


class ProgramEnrollmentTool(Document):
	def onload(self):
		academic_term_reqd = cint(
			frappe.db.get_single_value("Education Settings", "academic_term_reqd")
		)
		self.set_onload("academic_term_reqd", academic_term_reqd)

	@frappe.whitelist()
	def get_students(self):
		students = []
		if not self.get_students_from:
			frappe.throw(_("Mandatory field - Get Students From"))
		elif not self.program:
			frappe.throw(_("Mandatory field - Program"))
		elif not self.academic_year:
			frappe.throw(_("Mandatory field - Academic Year"))
		else:
			condition = "and academic_term=%(academic_term)s" if self.academic_term else ""
			condition2 = "and student_batch_name=%(student_batch)s" if self.student_batch else ""

			if self.get_students_from == "Student Applicant":
				students = frappe.db.sql(
					"""
					SELECT 
						name AS student_applicant, 
						title AS student_name 
					FROM 
						`tabStudent Applicant`
					WHERE 
						application_status='Approved' 
						AND program=%(program)s 
						AND academic_year=%(academic_year)s 
						{condition}
					""".format(condition=condition),
					{"academic_year": self.academic_year, "program": self.program, "academic_term": self.academic_term},
					as_dict=1,
				)

			elif self.get_students_from == "Program Enrollment":
				students = frappe.db.sql(
					"""
					SELECT 
						pe.student, 
						pe.student_name, 
						pe.student_batch_name, 
						pe.student_category,
						s.custom_division AS current_division
					FROM 
						`tabProgram Enrollment` pe
					LEFT JOIN 
						`tabStudent` s 
					ON 
						pe.student = s.name 
					WHERE 
						pe.program=%(program)s 
						AND pe.academic_year=%(academic_year)s 
						{condition} 
						{condition2}
						AND pe.docstatus != 2
						AND s.student_status in ('Current student', 'Defaulter')
						AND s.confirm_for_next_year != "No"
					""".format(condition=condition, condition2=condition2),
					{
						"academic_year": self.academic_year, 
						"program": self.program, 
						"student_batch": self.student_batch, 
						"academic_term": self.academic_term,
					},
					as_dict=1,
				)

		if students:
			return students
		else:
			frappe.throw(_("No students Found"))

	@frappe.whitelist()
	def enroll_students(self):
		total = len(self.students)
		for i, stud in enumerate(self.students):
			frappe.publish_realtime(
				"program_enrollment_tool", dict(progress=[i + 1, total]), user=frappe.session.user
			)
			if stud.student:
				filters = {"student_group_name": stud.current_division, "academic_year": self.academic_year, "program": self.program}
				student_group = frappe.get_value("Student Group", filters, "name")
				prog_enrollment = frappe.new_doc("Program Enrollment")
				prog_enrollment.student = stud.student
				prog_enrollment.rte_status = self.get_rte_status(stud, self.new_program)
				prog_enrollment.student_name = stud.student_name
				prog_enrollment.student_group = student_group
				prog_enrollment.student_category = stud.student_category
				prog_enrollment.program = self.new_program
				prog_enrollment.academic_year = self.new_academic_year
				prog_enrollment.academic_term = self.new_academic_term
				prog_enrollment.student_batch_name = (
					stud.student_batch_name if stud.student_batch_name else self.new_student_batch
				)
				prog_enrollment.save()
			elif stud.student_applicant:
				prog_enrollment = enroll_student(stud.student_applicant)
				prog_enrollment.academic_year = self.academic_year
				prog_enrollment.academic_term = self.academic_term
				prog_enrollment.student_batch_name = (
					stud.student_batch_name if stud.student_batch_name else self.new_student_batch
				)
				prog_enrollment.save()
		frappe.msgprint(_("{0} Students have been enrolled").format(total))


	def get_rte_status(self, student, new_program):
		"""
		Get the previous RTE status of the student and determine the new RTE status based on the new program.
	
		:param student: Student object containing student details.
		:param new_program: The new program the student is enrolling in.
		:return: New RTE status.
		"""
		try:
			school = frappe.get_value("Student", student.student, "school")
			rte_deactivation_class = frappe.get_value("School", school, "rte_deactivation_class")
		
			old_rte_status = frappe.get_value(
				"Program Enrollment",
				filters={"student": student.student, "academic_year": self.academic_year, "docstatus": 1}, 
				fieldname="rte_status"
			) or "Inactive"
		
			if new_program == rte_deactivation_class:
				if old_rte_status == "Active":
					return "Inactivation Pending"
			return old_rte_status
		except Exception as e:
			message = f"Error in finding RTE status of student {student.student}: {str(e)}"
			frappe.log_error(_(message), frappe.get_traceback())