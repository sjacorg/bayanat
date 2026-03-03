const DocxViewer = Vue.defineComponent({
  props: ['media'],
  computed: {
    extractedText() {
      return this.media?.extraction?.text;
    },
  },
  template: `
    <div class="w-100 h-100 d-flex align-center justify-center bg-grey-lighten-3">

      <!-- No text yet: styled placeholder -->
      <div v-if="!extractedText" class="d-flex flex-column align-center justify-center ga-3 text-medium-emphasis" style="height:100%;">
        <v-icon icon="mdi-file-word-outline" color="blue" size="96"></v-icon>
        <div class="text-body-2 text-truncate px-4" style="max-width: 280px;">{{ media?.filename }}</div>
        <div class="text-caption">Run extraction to preview content</div>
      </div>

      <!-- Text extracted: blurred preview -->
      <div v-else class="w-100 h-100 position-relative overflow-hidden pa-6" style="cursor: default;">
        <div
          style="white-space: pre-wrap; line-height: 1.8; filter: blur(3px); user-select: none; font-size: 13px;"
          class="text-body-2"
        >{{ extractedText }}</div>

        <!-- Gradient fade at bottom -->
        <div class="position-absolute w-100" style="bottom:0; left:0; height:120px; background: linear-gradient(to bottom, transparent, rgb(var(--v-theme-surface-variant)));"></div>

        <!-- Centered overlay label -->
        <div class="position-absolute d-flex flex-column align-center justify-center ga-2" style="inset:0;">
          <v-icon icon="mdi-file-word-outline" color="blue" size="48"></v-icon>
          <v-chip color="blue" variant="tonal" size="small" prepend-icon="mdi-text">
            {{ media?.extraction?.word_count }} words extracted
          </v-chip>
        </div>
      </div>

    </div>
  `,
});
