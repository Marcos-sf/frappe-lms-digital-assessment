import json

import frappe

from assessments.assessments import api
from assessments.setup_test_data import ASSESSMENT_TITLE, STUDENT_EMAIL


def run():
	assessment = frappe.db.get_value("Assessment", {"title": ASSESSMENT_TITLE}, "name")
	if not assessment:
		print("Run setup_test_data.run first.")
		return

	frappe.set_user(STUDENT_EMAIL)

	attempt = api.start_assessment(assessment)
	print(f"1. Started attempt: {attempt.name}, stage {attempt.current_stage_idx} ({attempt.stage_progress[0].stage_type})")

	attempt = api.submit_declaration(
		attempt.name, "Test Student", "data:image/png;base64,fake-signature-data", 1
	)
	print(f"2. Declaration submitted, now on stage {attempt.current_stage_idx} ({attempt.stage_progress[attempt.current_stage_idx].stage_type})")

	state = api.get_attempt_state(attempt.name)
	print(f"3. Quiz stage has {len(state['current_stage_questions'])} questions, deadline: {state['stage_deadline']}")

	for q in state["current_stage_questions"]:
		if q["type"] == "Choices":
			correct_option = q["options"][0]["text"]
			answer_value = json.dumps([correct_option])
		else:
			answer_value = "int"
		result = api.save_answer(attempt.name, attempt.current_stage_idx, q["quiz_question"], answer_value)
		print(f"   saved answer for '{q['question'][:40]}...' -> {result['saved']}")

	attempt = api.submit_stage(attempt.name, attempt.current_stage_idx)
	print(f"4. Quiz stage submitted, now on stage {attempt.current_stage_idx} ({attempt.stage_progress[attempt.current_stage_idx].stage_type})")

	quiz_submission_name = attempt.stage_progress[1].quiz_submission
	quiz_submission = frappe.get_doc("LMS Quiz Submission", quiz_submission_name)
	print(f"   LMS Quiz Submission: {quiz_submission.name}, score {quiz_submission.score}/{quiz_submission.score_out_of} ({quiz_submission.percentage}%)")

	attempt = api.submit_stage(attempt.name, attempt.current_stage_idx)
	print(f"5. Final stage submitted. Attempt status: {attempt.status}, submitted_at: {attempt.submitted_at}")

	frappe.set_user("Administrator")
	frappe.db.commit()
