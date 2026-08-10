import frappe

STUDENT_EMAIL = "student@example.com"
COURSE_TITLE = "Intro to Python (Test Course)"
QUIZ_TITLE = "Python Basics Quiz (Test)"
ASSESSMENT_TITLE = "Python Basics - Final Assessment (Test)"


def run():
	course = _get_or_create_course()
	student = _get_or_create_student()
	_enroll_student(student, course)
	questions = _get_or_create_questions()
	quiz = _get_or_create_quiz(questions)
	assessment = _get_or_create_assessment(course, quiz)

	frappe.db.commit()

	print("Created/verified test data:")
	print(f"  Student:    {student}")
	print(f"  Course:     {course}")
	print(f"  Quiz:       {quiz}")
	print(f"  Assessment: {assessment}")


def _get_or_create_course():
	existing = frappe.db.get_value("LMS Course", {"title": COURSE_TITLE}, "name")
	if existing:
		return existing

	course = frappe.get_doc(
		{
			"doctype": "LMS Course",
			"title": COURSE_TITLE,
			"short_introduction": "A test course created for assessment workflow development.",
			"description": "A test course created for assessment workflow development.",
			"instructors": [{"instructor": "Administrator"}],
			"published": 1,
		}
	)
	course.insert(ignore_permissions=True)
	return course.name


def _get_or_create_student():
	if frappe.db.exists("User", STUDENT_EMAIL):
		return STUDENT_EMAIL

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": STUDENT_EMAIL,
			"first_name": "Test",
			"last_name": "Student",
			"send_welcome_email": 0,
			"roles": [{"role": "LMS Student"}],
		}
	)
	user.insert(ignore_permissions=True)
	return user.name


def _enroll_student(student, course):
	if frappe.db.exists("LMS Enrollment", {"member": student, "course": course}):
		return

	frappe.get_doc(
		{
			"doctype": "LMS Enrollment",
			"member": student,
			"course": course,
		}
	).insert(ignore_permissions=True)


def _get_or_create_questions():
	names = []

	q1 = frappe.db.get_value("LMS Question", {"question": "What is the output of print(2 + 3)?"}, "name")
	if not q1:
		q1 = frappe.get_doc(
			{
				"doctype": "LMS Question",
				"question": "What is the output of print(2 + 3)?",
				"type": "Choices",
				"option_1": "5",
				"is_correct_1": 1,
				"option_2": "23",
				"option_3": "Error",
			}
		)
		q1.insert(ignore_permissions=True)
		q1 = q1.name
	names.append(q1)

	q2 = frappe.db.get_value(
		"LMS Question", {"question": "Which keyword is used to define a function in Python?"}, "name"
	)
	if not q2:
		q2 = frappe.get_doc(
			{
				"doctype": "LMS Question",
				"question": "Which keyword is used to define a function in Python?",
				"type": "Choices",
				"option_1": "func",
				"option_2": "def",
				"is_correct_2": 1,
				"option_3": "function",
			}
		)
		q2.insert(ignore_permissions=True)
		q2 = q2.name
	names.append(q2)

	q3 = frappe.db.get_value(
		"LMS Question", {"question": "What data type is returned by the len() function?"}, "name"
	)
	if not q3:
		q3 = frappe.get_doc(
			{
				"doctype": "LMS Question",
				"question": "What data type is returned by the len() function?",
				"type": "User Input",
				"possibility_1": "int",
				"possibility_2": "integer",
			}
		)
		q3.insert(ignore_permissions=True)
		q3 = q3.name
	names.append(q3)

	return names


def _get_or_create_quiz(question_names):
	existing = frappe.db.get_value("LMS Quiz", {"title": QUIZ_TITLE}, "name")
	if existing:
		return existing

	quiz = frappe.get_doc(
		{
			"doctype": "LMS Quiz",
			"title": QUIZ_TITLE,
			"duration": "10",
			"passing_percentage": 60,
			"questions": [{"question": q, "marks": 1} for q in question_names],
		}
	)
	quiz.insert(ignore_permissions=True)
	return quiz.name


def _get_or_create_assessment(course, quiz):
	existing = frappe.db.get_value("Assessment", {"title": ASSESSMENT_TITLE}, "name")
	if existing:
		return existing

	assessment = frappe.get_doc(
		{
			"doctype": "Assessment",
			"title": ASSESSMENT_TITLE,
			"course": course,
			"assessment_type": "Evaluation",
			"is_published": 1,
			"stages": [
				{"stage_type": "Declaration", "title": "Digital Declaration"},
				{
					"stage_type": "Quiz",
					"title": "MCQ Assessment",
					"quiz": quiz,
					"duration_minutes": 10,
				},
				{"stage_type": "Review", "title": "Final Review"},
			],
		}
	)
	assessment.insert(ignore_permissions=True)
	return assessment.name
