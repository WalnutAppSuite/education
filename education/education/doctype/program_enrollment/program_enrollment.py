# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _, msgprint
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe.query_builder.functions import Min
from frappe.utils import comma_and, get_link_to_form, getdate


class ProgramEnrollment(Document):
    def validate(self):
        self.set_student_name()
        self.validate_duplication()
        self.validate_academic_year()
        if self.academic_term:
            self.validate_academic_term()

        # Check if image was uploaded or changed
        if self.image and (not self.get_doc_before_save() or self.image != self.get_doc_before_save().image):
            self.process_and_crop_image()

        if not self.courses:
            self.extend("courses", self.get_courses())

    def process_and_crop_image(self):
        """Process, crop and rename the uploaded image for the Program Enrollment"""
        from education.education.doctype.program_enrollment.program_enrollment import process_enrollment_image
        process_enrollment_image(self.name)

    def set_student_name(self):
        if not self.student_name:
            self.student_name = frappe.db.get_value("Student", self.student, "student_name")

    def on_submit(self):
        self.update_student_joining_date()
        self.make_fee_records()
        self.create_course_enrollments()
        
    def on_trash(self):
        """
        When a Program Enrollment is deleted, delete related Birthday Card and User Permissions
        """
        try:
            self.delete_birthday_card_permissions()
            self.delete_birthday_card()
        except Exception as e:
            frappe.log_error(
                f"Error in birthday card cleanup during Program Enrollment deletion: {str(e)}",
                "Birthday Card Cleanup Error"
            )
            # Continue with deletion process even if birthday card cleanup fails

    def on_cancel(self):
        """
        When a Program Enrollment is cancelled, delete related Birthday Card and User Permissions
        """
        try:
            self.delete_birthday_card_permissions()
            self.delete_birthday_card()
        except Exception as e:
            frappe.log_error(
                f"Error in birthday card cleanup during Program Enrollment cancellation: {str(e)}",
                "Birthday Card Cleanup Error"
            )
            # Continue with cancellation process even if birthday card cleanup fails

    def delete_birthday_card_permissions(self):
        """
        Delete all User Permissions where:
        - allow = "Birthday Card"
        - for_value matches this Program Enrollment's name
        """
        # Find all matching User Permissions
        user_permissions = frappe.get_all(
            "User Permission",
            filters={
                "allow": "Birthday Card",
                "for_value": self.name
            },
            fields=["name"]
        )
        
        # Log the permissions to be deleted
        if user_permissions:
            frappe.log_error(
                f"Deleting {len(user_permissions)} User Permissions for Birthday Card: {self.name}",
                "Birthday Card Cleanup"
            )
        
        # Delete each permission
        for permission in user_permissions:
            try:
                frappe.delete_doc("User Permission", permission.name, force=True)
            except Exception as e:
                frappe.log_error(
                    f"Failed to delete User Permission {permission.name}: {str(e)}",
                    "Birthday Card Cleanup Error"
                )

    def delete_birthday_card(self):
        """
        Delete the Birthday Card document associated with this Program Enrollment
        """
        try:
            # Check if a Birthday Card exists for this Program Enrollment
            birthday_card = frappe.get_all(
                "Birthday Card",
                filters={"program_enrollment": self.name},
                fields=["name"]
            )
            
            if birthday_card:
                # Log the birthday card to be deleted
                frappe.log_error(
                    f"Deleting Birthday Card: {birthday_card[0].name}",
                    "Birthday Card Cleanup"
                )
                
                # Delete the Birthday Card
                frappe.delete_doc("Birthday Card", birthday_card[0].name, force=True)
                frappe.msgprint(f"Birthday Card {birthday_card[0].name} has been deleted.")
        except Exception as e:
            frappe.log_error(
                f"Failed to delete Birthday Card for {self.name}: {str(e)}",
                "Birthday Card Cleanup Error"
            )

    def validate_academic_year(self):
        start_date, end_date = frappe.db.get_value(
            "Academic Year", self.academic_year, ["year_start_date", "year_end_date"]
        )
        if self.enrollment_date:
            if start_date and getdate(self.enrollment_date) < getdate(start_date):
                frappe.throw(
                    _(
                        "Enrollment Date cannot be before the Start Date of the Academic Year {0}"
                    ).format(get_link_to_form("Academic Year", self.academic_year))
                )

            if end_date and getdate(self.enrollment_date) > getdate(end_date):
                frappe.throw(
                    _("Enrollment Date cannot be after the End Date of the Academic Term {0}").format(
                        get_link_to_form("Academic Year", self.academic_year)
                    )
                )

    def validate_academic_term(self):
        start_date, end_date = frappe.db.get_value(
            "Academic Term", self.academic_term, ["term_start_date", "term_end_date"]
        )
        if self.enrollment_date:
            if start_date and getdate(self.enrollment_date) < getdate(start_date):
                frappe.throw(
                    _(
                        "Enrollment Date cannot be before the Start Date of the Academic Term {0}"
                    ).format(get_link_to_form("Academic Term", self.academic_term))
                )

            if end_date and getdate(self.enrollment_date) > getdate(end_date):
                frappe.throw(
                    _("Enrollment Date cannot be after the End Date of the Academic Term {0}").format(
                        get_link_to_form("Academic Term", self.academic_term)
                    )
                )

    def validate_duplication(self):
        enrollment = frappe.db.exists(
            "Program Enrollment", {
                "student": self.student,
                "program": self.program,
                "academic_year": self.academic_year,
                "academic_term": self.academic_term,
                "docstatus": ("<", 2),
                "name": ("!=", self.name),
            })
        if enrollment:
            frappe.throw(_("Student is already enrolled."))

    def update_student_joining_date(self):
        table = frappe.qb.DocType("Program Enrollment")
        date = (
            frappe.qb.from_(table)
            .select(Min(table.enrollment_date).as_("enrollment_date"))
            .where(table.student == self.student)
        ).run(as_dict=True)

        if date:
            frappe.db.set_value("Student", self.student, "joining_date", date[0].enrollment_date)

    def make_fee_records(self):
        from education.education.api import get_fee_components

        fee_list = []
        for d in self.fees:
            fee_components = get_fee_components(d.fee_structure)
            if fee_components:
                fees = frappe.new_doc("Fees")
                fees.update(
                    {
                        "student": self.student,
                        "academic_year": self.academic_year,
                        "academic_term": d.academic_term,
                        "fee_structure": d.fee_structure,
                        "program": self.program,
                        "due_date": d.due_date,
                        "student_name": self.student_name,
                        "program_enrollment": self.name,
                        "components": fee_components,
                    }
                )

                fees.save()
                fees.submit()
                fee_list.append(fees.name)
        if fee_list:
            fee_list = [
                """<a href="/app/Form/Fees/%s" target="_blank">%s</a>""" % (fee, fee)
                for fee in fee_list
            ]
            msgprint(_("Fee Records Created - {0}").format(comma_and(fee_list)))

    @frappe.whitelist()
    def get_courses(self):
        return frappe.db.sql(
            """select course from `tabProgram Course` where parent = %s and required = 1""",
            (self.program),
            as_dict=1,
        )

    def create_course_enrollments(self):
        for course in self.courses:
            filters = {
                "student": self.student,
                "course": course.course,
                "program_enrollment": self.name,
            }
            if not frappe.db.exists("Course Enrollment", filters):
                filters.update(
                    {"doctype": "Course Enrollment", "enrollment_date": self.enrollment_date}
                )
                frappe.get_doc(filters).save()

    def get_all_course_enrollments(self):
        course_enrollment_names = frappe.get_list(
            "Course Enrollment", filters={"program_enrollment": self.name}
        )
        return [
            frappe.get_doc("Course Enrollment", course_enrollment.name)
            for course_enrollment in course_enrollment_names
        ]

    def get_quiz_progress(self):
        student = frappe.get_doc("Student", self.student)
        quiz_progress = frappe._dict()
        progress_list = []
        for course_enrollment in self.get_all_course_enrollments():
            course_progress = course_enrollment.get_progress(student)
            for progress_item in course_progress:
                if progress_item["content_type"] == "Quiz":
                    progress_item["course"] = course_enrollment.course
                    progress_list.append(progress_item)
        if not progress_list:
            return None
        quiz_progress.quiz_attempt = progress_list
        quiz_progress.name = self.program
        quiz_progress.program = self.program
        return quiz_progress


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_program_courses(doctype, txt, searchfield, start, page_len, filters):
    if not filters.get("program"):
        frappe.msgprint(_("Please select a Program first."))
        return []

    return frappe.db.sql(
        """select course, course_name from `tabProgram Course`
        where  parent = %(program)s and course like %(txt)s {match_cond}
        order by
            if(locate(%(_txt)s, course), locate(%(_txt)s, course), 99999),
            idx desc,
            `tabProgram Course`.course asc
        limit {start}, {page_len}""".format(
            match_cond=get_match_cond(doctype), start=start, page_len=page_len
        ),
        {
            "txt": "%{0}%".format(txt),
            "_txt": txt.replace("%", ""),
            "program": filters["program"],
        },
    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_students(doctype, txt, searchfield, start, page_len, filters):
    if not filters.get("academic_term"):
        filters["academic_term"] = frappe.defaults.get_defaults().academic_term

    if not filters.get("academic_year"):
        filters["academic_year"] = frappe.defaults.get_defaults().academic_year

    enrolled_students = frappe.get_list(
        "Program Enrollment",
        filters={
            "academic_term": filters.get("academic_term"),
            "academic_year": filters.get("academic_year"),
        },
        fields=["student"],
    )

    students = [d.student for d in enrolled_students] if enrolled_students else [""]

    return frappe.db.sql(
        """select
            name, student_name from tabStudent
        where
            name not in (%s)
        and
            `%s` LIKE %s
        order by
            idx desc, name
        limit %s, %s"""
        % (", ".join(["%s"] * len(students)), searchfield, "%s", "%s", "%s"),
        tuple(students + ["%%%s%%" % txt, start, page_len]),
    )

@frappe.whitelist()
def process_enrollment_image(docname=None, file_url=None):
    """Process and crop enrollment image for both draft and submitted documents"""
    # When called from FileUploader, docname is not passed directly but file details are in form_dict
    if not docname and hasattr(frappe.form_dict, "docname"):
        docname = frappe.form_dict.docname
    
    # If still no docname but we have a file_url and attachments were made to a specific doc
    if not docname and file_url and frappe.form_dict.get("attached_to_doctype") == "Program Enrollment":
        docname = frappe.form_dict.get("attached_to_name")
    
    if not docname:
        frappe.throw(_("Document name is required"))
    
    doc = frappe.get_doc("Program Enrollment", docname)
    
    # If file_url is provided, update the document's image
    if file_url:
        # For submitted documents, we need to update directly in the database
        if doc.docstatus == 1:
            frappe.db.set_value("Program Enrollment", docname, "image", file_url)
            # Reload the document to get the updated image
            doc = frappe.get_doc("Program Enrollment", docname)
    else:
        # If no file_url provided but we have one in form_dict (from FileUploader)
        if hasattr(frappe.form_dict, "file_url"):
            file_url = frappe.form_dict.file_url
            # For submitted documents, we need to update directly in the database
            if doc.docstatus == 1:
                frappe.db.set_value("Program Enrollment", docname, "image", file_url)
                # Reload the document to get the updated image
                doc = frappe.get_doc("Program Enrollment", docname)
            else:
                doc.db_set("image", file_url)
    
    # If no image, nothing to process
    if not doc.image:
        return False
    
    # Process the image
    try:
        from edu_quality.edu_quality.doctype.student_id_card.student_id_card import bgr_to_rbg
        from edu_quality.api.google_drive_upload import upload_file
        from autocrop import Cropper
        from PIL import Image
        import io
        import numpy as np
        from mimetypes import guess_type
        
        frappe.log_error(f"Processing image for {docname}: {doc.image}")
        
        # Get the file document from the image URL
        file_doc = frappe.get_doc("File", {"file_url": doc.image})
        
        # Read file content
        file_content = file_doc.get_content()
        
        # Process image with autocrop
        cropper = Cropper()
        image = Image.open(io.BytesIO(file_content))
        image_array = bgr_to_rbg(np.asarray(image))
        cropped_array = cropper.crop(image_array)
        
        # Determine image format
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            mode = "RGBA"
        else:
            mode = "RGB"
            
        # Get file extension
        content_type = guess_type(file_doc.file_name)[0]
        image_format = content_type.split("/")[1] if content_type else "jpeg"
        
        # Create new filename in the required format
        student_id = doc.student
        academic_year = doc.academic_year.replace(" ", "-")
        new_filename = f"{student_id}-({academic_year}).{image_format}"
        
        if cropped_array is not None and cropped_array.any():
            # Create cropped image
            cropped_image = Image.fromarray(cropped_array, mode=mode)
            output = io.BytesIO()
            cropped_image.save(output, format=image_format, quality=100)
            optimized_content = output.getvalue()
            
            # Create new file document for the cropped image
            new_file = frappe.new_doc("File")
            new_file.file_name = new_filename
            new_file.content = optimized_content
            new_file.attached_to_doctype = "Program Enrollment"
            new_file.attached_to_name = doc.name
            new_file.attached_to_field = "image"
            new_file.folder = "Home"
            new_file.is_private = file_doc.is_private
            new_file.save()
            
            # Update the image field 
            if doc.docstatus == 1:
                # For submitted docs, update directly in the database
                frappe.db.set_value("Program Enrollment", doc.name, "image", new_file.file_url)
            else:
                # For draft docs, update the doc object
                doc.db_set("image", new_file.file_url)
            
            # Upload to Google Drive
            try:
                google_doc = frappe.get_single("Google Service Account")
                upload_file(new_file.file_url, "Home", google_doc.id_card_folder)
            except Exception as e:
                frappe.log_error(f"Error uploading enrollment image to Google Drive: {str(e)}", frappe.get_traceback())
                frappe.msgprint(_("Warning: Image cropped successfully but could not be uploaded to Google Drive."), 
                               indicator="orange", alert=True)
            
            frappe.msgprint(_("Image processed successfully."), indicator="green", alert=True)
            return new_file.file_url
        else:
            # No face detected in the image
            frappe.msgprint(_("Warning: No face detected in the uploaded image. Using the original image instead."), 
                           indicator="orange", alert=True)
            return False
            
    except Exception as e:
        frappe.log_error(f"Error processing enrollment image: {str(e)}", frappe.get_traceback())
        frappe.msgprint(_("Error processing image. The original image will be used. Please check the error logs for details."), 
                       indicator="red", alert=True)
        return False