<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-base px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs
			:items="[
				{ label: __('Assessments'), route: { name: 'AssessmentDashboard' } },
				{ label: assessmentTitle },
			]"
		/>
	</header>

	<div class="md:w-7/12 md:mx-auto mx-4 py-10">
		<div v-if="starting || attemptState.loading" class="flex justify-center py-12">
			<LoadingIndicator class="size-5 text-ink-gray-5" />
		</div>

		<div v-else-if="attemptState.data">
			<StageStepper
				:stages="attemptState.data.attempt.stage_progress"
				:current-idx="attemptState.data.attempt.current_stage_idx"
			/>

			<AssessmentTimer
				v-if="attemptState.data.stage_deadline"
				:deadline="attemptState.data.stage_deadline"
				:key="attemptState.data.stage_deadline"
				@expired="onTimerExpired"
			/>

			<ReviewSummary
				v-if="attemptState.data.attempt.status === 'Submitted'"
				:attempt="attemptState.data.attempt"
				read-only
			/>

			<template v-else>
				<DeclarationStage
					v-if="currentStageType === 'Declaration'"
					:attempt="attemptState.data.attempt"
					@advance="attemptState.reload()"
				/>
				<QuizStage
					v-else-if="currentStageType === 'Quiz'"
					:attempt="attemptState.data.attempt"
					:questions="attemptState.data.current_stage_questions"
					:answers="attemptState.data.answers"
					@advance="attemptState.reload()"
				/>
				<ReviewSummary
					v-else-if="currentStageType === 'Review'"
					:attempt="attemptState.data.attempt"
					@advance="attemptState.reload()"
				/>
			</template>
		</div>
	</div>
</template>
<script setup>
import { Breadcrumbs, call, createResource, LoadingIndicator, usePageMeta } from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'
import { sessionStore } from '@/stores/session'
import AssessmentTimer from '@/components/AssessmentTimer.vue'
import StageStepper from '@/components/Assessments/StageStepper.vue'
import DeclarationStage from '@/components/Assessments/DeclarationStage.vue'
import QuizStage from '@/components/Assessments/QuizStage.vue'
import ReviewSummary from '@/components/Assessments/ReviewSummary.vue'

const { brand } = sessionStore()

const props = defineProps({
	assessmentID: {
		type: String,
		required: true,
	},
})

const starting = ref(true)
const assessmentTitle = ref(props.assessmentID)
const attemptName = ref(null)

const attemptState = createResource({
	url: 'assessments.assessments.api.get_attempt_state',
	makeParams: () => ({ attempt: attemptName.value }),
})

onMounted(async () => {
	try {
		const attempt = await call('assessments.assessments.api.start_assessment', {
			assessment: props.assessmentID,
		})
		attemptName.value = attempt.name
		assessmentTitle.value = attempt.assessment
		await attemptState.reload()
	} finally {
		starting.value = false
	}
})

const currentStageType = computed(() => {
	const attempt = attemptState.data?.attempt
	if (!attempt) return null
	return attempt.stage_progress[attempt.current_stage_idx]?.stage_type
})

const onTimerExpired = () => {
	attemptState.reload()
}

usePageMeta(() => ({
	title: assessmentTitle.value,
	icon: brand.favicon,
}))
</script>
