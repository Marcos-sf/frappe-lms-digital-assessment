<template>
	<div class="border rounded-lg p-6">
		<div class="text-lg-semibold text-ink-gray-9 mb-1">
			{{ __('Digital Declaration') }}
		</div>
		<div class="text-sm text-ink-gray-6 mb-5">
			{{
				__(
					'Please confirm your identity and accept the declaration before proceeding.'
				)
			}}
		</div>

		<div class="space-y-4">
			<FormControl
				:label="__('Candidate Name')"
				type="text"
				v-model="candidateName"
				:placeholder="__('Enter your full name')"
			/>

			<div>
				<div class="text-sm text-ink-gray-7 mb-1">
					{{ __('Date & Time') }}
				</div>
				<div class="text-sm text-ink-gray-9">{{ now }}</div>
			</div>

			<div>
				<div class="text-sm text-ink-gray-7 mb-1">
					{{ __('Digital Signature') }}
				</div>
				<SignaturePad @change="(value) => (signature = value)" />
			</div>

			<Checkbox
				v-model="accepted"
				:label="
					__(
						'I declare that the information provided is accurate and I agree to abide by the assessment rules.'
					)
				"
			/>

			<Button
				variant="solid"
				:disabled="!canSubmit"
				:loading="submitting"
				@click="submit"
			>
				{{ __('Continue') }}
			</Button>
		</div>
	</div>
</template>
<script setup>
import { Button, Checkbox, FormControl, call, toast } from 'frappe-ui'
import { computed, ref } from 'vue'
import SignaturePad from '@/components/SignaturePad.vue'

const props = defineProps({
	attempt: {
		type: Object,
		required: true,
	},
})

const emit = defineEmits(['advance'])

const candidateName = ref(props.attempt.candidate_name || '')
const signature = ref('')
const accepted = ref(false)
const submitting = ref(false)
const now = new Date().toLocaleString()

const canSubmit = computed(
	() => candidateName.value.trim() && signature.value && accepted.value
)

const submit = async () => {
	submitting.value = true
	try {
		await call('assessments.assessments.api.submit_declaration', {
			attempt: props.attempt.name,
			candidate_name: candidateName.value,
			signature: signature.value,
			declaration_accepted: 1,
		})
		emit('advance')
	} catch (err) {
		toast.error(err.messages?.[0] || err.message)
	} finally {
		submitting.value = false
	}
}
</script>
