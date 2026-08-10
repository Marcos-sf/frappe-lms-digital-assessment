<template>
	<div>
		<canvas
			ref="canvasRef"
			class="w-full border rounded-md bg-surface-white cursor-crosshair touch-none"
			style="height: 160px"
			@pointerdown="startStroke"
			@pointermove="drawStroke"
			@pointerup="endStroke"
			@pointerleave="endStroke"
		/>
		<div class="flex items-center justify-between mt-2">
			<div class="text-xs text-ink-gray-6">
				{{ __('Draw your signature above') }}
			</div>
			<Button variant="ghost" size="sm" @click="clear">
				{{ __('Clear') }}
			</Button>
		</div>
	</div>
</template>
<script setup>
import { Button } from 'frappe-ui'
import { onMounted, ref } from 'vue'

const emit = defineEmits(['change'])
const canvasRef = ref(null)
let ctx = null
let drawing = false
let hasDrawn = false

onMounted(() => {
	const canvas = canvasRef.value
	// Backing store must match the CSS size 1:1, or drawing coordinates drift
	// from the pointer position on high-DPI screens.
	const ratio = window.devicePixelRatio || 1
	canvas.width = canvas.clientWidth * ratio
	canvas.height = canvas.clientHeight * ratio
	ctx = canvas.getContext('2d')
	ctx.scale(ratio, ratio)
	ctx.lineWidth = 2
	ctx.lineCap = 'round'
	ctx.strokeStyle = '#1f2937'
})

const pointerPosition = (event) => {
	const rect = canvasRef.value.getBoundingClientRect()
	return { x: event.clientX - rect.left, y: event.clientY - rect.top }
}

const startStroke = (event) => {
	drawing = true
	const { x, y } = pointerPosition(event)
	ctx.beginPath()
	ctx.moveTo(x, y)
}

const drawStroke = (event) => {
	if (!drawing) return
	const { x, y } = pointerPosition(event)
	ctx.lineTo(x, y)
	ctx.stroke()
	hasDrawn = true
}

const endStroke = () => {
	if (!drawing) return
	drawing = false
	if (hasDrawn) emit('change', canvasRef.value.toDataURL('image/png'))
}

const clear = () => {
	ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
	hasDrawn = false
	emit('change', '')
}

defineExpose({ clear })
</script>
