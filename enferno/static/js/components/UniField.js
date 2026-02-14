const UniField = Vue.defineComponent({
  props: {
    caption: String,
    english: String | Number,
    arabic: String | Number,
    disableSpacing: Boolean,
  },
  data() {
    return {
      sw: !!this.english,
      fading: false,
    };
  },
  methods: {
    toggle() {
      this.fading = true;
      setTimeout(() => {
        this.sw = !this.sw;
        this.fading = false;
      }, 120);
    },
  },
  template: `
    <div v-if="english || arabic" class="uni-field" :class="{ 'uni-field--spaced': !disableSpacing }">
      <div v-if="caption" class="uni-field__caption">{{ caption }}</div>
      <div class="uni-field__body">
        <div class="uni-field__text" :class="{ 'uni-field__text--fade': fading, 'uni-field__text--rtl': !sw && arabic }">{{ sw ? english : (arabic || english) }}</div>
        <button v-if="english && arabic" class="uni-field__toggle" @click="toggle" :title="sw ? 'عربي' : 'English'">
          {{ sw ? 'ع' : 'EN' }}
        </button>
      </div>
    </div>
  `,
});
