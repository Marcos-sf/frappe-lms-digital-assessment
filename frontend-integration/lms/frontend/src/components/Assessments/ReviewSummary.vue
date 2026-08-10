<template>
	<div class="border rounded-lg p-6 space-y-5">
		<div class="text-lg-semibold text-ink-gray-9">
			{{ readOnly ? __('Assessment Summary') : __('Final Review') }}
		</div>

		<div class="grid sm:grid-cols-2 gap-4">
			<div>
				<div class="text-sm text-ink-gray-6">{{ __('Candidate Name') }}</div>
				<div class="text-ink-gray-9">{{ attempt.candidate_name }}</div>
			</div>
			<div>
				<div class="text-sm text-ink-gray-6">{{ __('Declared On') }}</div>
				<div class="text-ink-gray-9">{{ attempt.declaration_datetime }}</div>
			</div>
			<div v-if="quizSubmission.data">
				<div class="text-sm text-ink-gray-6">{{ __('Score') }}</div>
				<div class="text-ink-gray-9">
					{{ quizSubmission.data.score }} / {{ quizSubmission.data.score_out_of }}
					({{ Math.round(quizSubmission.data.percentage) }}%)
				</div>
			</div>
			<div v-if="quizSubmission.data">
				<div class="text-sm text-ink-gray-6">{{ __('Result') }}</div>
				<Badge :theme="passed ? 'green' : 'red'">
					{{ passed ? __('Pass') : __('Fail') }}
				</Badge>
			</div>
			<div v-if="readOnly">
				<div class="text-sm text-ink-gray-6">{{ __('Submission Time') }}</div>
				<div class="text-ink-gray-9">{{ attempt.submitted_at }}</div>
			</div>
			<div v-if="readOnly">
				<div class="text-sm text-ink-gray-6">{{ __('Final Status') }}</div>
				<Badge theme="green">{{ __('Submitted') }}</Badge>
			</div>
		</div>

		<div>
			<div class="text-sm text-ink-gray-6 mb-1">{{ __('Candidate Signature') }}</div>
			<img
				v-if="attempt.signature"
				:src="attempt.signature"
				class="border rounded-md h-24 bg-surface-white"
			/>
		</div>

		<Button v-if="!readOnly" variant="solid" :loading="submitting" @click="submitFinal">
			{{ __('Submit Assessment') }}
		</Button>
	</div>
</template>
<script setup>
import { Badge, Button, call, createResource, toast } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
	attempt: {
		type: Object,
		required: true,
	},
	readOnly: {
		type: Boolean,
		default: false,
	},
})

const emit = defineEmits(['advance'])
const submitting = ref(false)

const quizSubmissionName = computed(() => {
	const quizStage = props.attempt.stage_progress?.find((s) => s.stage_type === 'Quiz')
	return quizStage?.quiz_submission
})

const quizSubmission = createResource({
	url: 'frappe.client.get',
	makeParams: () => ({
		doctype: 'LMS Quiz Submission',
		name: quizSubmissionName.value,
	}),
	auto: !!quizSubmissionName.value,
})

const passed = computed(() => {
	if (!quizSubmission.data) return false
	return quizSubmission.data.percentage >= quizSubmission.data.passing_percentage
})

const submitFinal = async () => {
	submitting.value = true
	try {
		await call('assessments.assessments.api.submit_stage', {
			attempt: props.attempt.name,
			stage_idx: props.attempt.current_stage_idx,
		})
		emit('advance')
	} catch (err) {
		toast.error(err.messages?.[0] || err.message)
	} finally {
		submitting.value = false
	}
}
</script>
