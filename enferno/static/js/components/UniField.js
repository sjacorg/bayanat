const UniField = Vue.defineComponent({
  props: {
    caption: String,
    english: {
      type: [String, Number],
      default: '',
    },
    arabic: {
      type: [String, Number],
      default: '',
    },
    disableSpacing: Boolean
  },
  data() {
    return {
      showEnglish: textUtils.hasText(this.english),
    };
  },
  computed: {
    hasEnglish() {
      return textUtils.hasText(this.english);
    },
    hasArabic() {
      return textUtils.hasText(this.arabic);
    },
  },
  methods: {
    displayText(value) {
      return textUtils.normalizeDisplayText(value);
    },
  },
  template: `
    <v-list v-if="hasEnglish || hasArabic"  variant="plain" :class="['d-flex align-center flex-grow-1', { 'mx-2 my-1 pa-2': !disableSpacing }]">
      <template v-if="hasEnglish && hasArabic">
        <v-list-item :title="caption" density="compact" :class="{ 'px-0': disableSpacing }">
          <v-sheet class="text-body-2">{{ displayText(showEnglish ? english : arabic) }}</v-sheet>
          <template #append>
              <v-btn variant="text" size="x-small" icon="mdi-web" @click.stop="showEnglish = !showEnglish"></v-btn>
          </template>
        </v-list-item>
      </template>

      <template v-else>
        <v-list-item :title="caption" density="compact" :class="{ 'px-0': disableSpacing }">
          <v-sheet class="text-body-2">{{ displayText(hasEnglish ? english : arabic) }}</v-sheet>
        </v-list-item>
      </template>
    </v-list>
  `,
});
