const MixII = Vue.defineComponent({
  props: {
    title: {
      type: String,
      default: '',
    },
    multiple: {
      type: Boolean,
      default: false,
    },
    modelValue: {
      type: Object,
      default: () => ({}),
    },
    items: {
      type: Array,
      default: () => [],
    },
  },
  emits: ['update:modelValue'],
  data: function () {
    return {
      translations: window.translations,
      mix: {},
    };
  },

  watch: {
    modelValue: function (val) {
      if (val) {
        this.mix = val;
      }
    },
    mix: {
      handler: 'refresh',
      deep: true,
    },
  },

  mounted: function () {
    if (this.modelValue) {
      this.mix = this.modelValue;
    }
  },

  methods: {
    refresh() {
      this.$emit('update:modelValue', this.mix);
    },
  },
  template: `
      <v-card :title="title" class="pa-3">
        <v-card-text>
          <div>
            <v-select v-model="mix.opts"
                      item-title="tr"
                      item-value="en"
                      :items="items" 
                      :multiple="this.multiple">
            </v-select>
          </div>
          <div class="flex-grow-1 ml-2">
            <v-textarea rows="2" :label="translations.details_" v-model="mix.details"></v-textarea>

          </div>

        </v-card-text>

      </v-card>

    `,
});
