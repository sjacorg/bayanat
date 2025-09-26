const MixI = Vue.defineComponent({
  props: {
    title: {
      type: String,
      default: '',
    },
    modelValue: {
      type: Object,
      default: () => ({}),
    },
    serverErrors: {
      type: Object,
      default: () => ({}),
    },
    errorKey: {
      type: String,
      default: '',
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
    modelValue: {
      handler(val) {
        if (val) {
            this.mix = val;
        }
      },
      immediate: true,
      deep: true,
    },
    mix: {
      handler: 'refresh',
      deep: true,
    },
  },

  mounted: function () {},

  methods: {
    refresh() {
      this.$emit('update:modelValue', this.mix);
    },
  },
  template: `
<v-card :title="title" class="pa-3">
     

      <v-card-text>
      <div>
      <v-radio-group v-model="mix.opts"  >
      <v-radio value="Yes" :label="translations.yes_"></v-radio>
      <v-radio value="No" :label="translations.no_"></v-radio>
      <v-radio value="Unknown" :label="translations.unknown_"></v-radio>
      
        </v-radio-group>
        </div>
      <div class="flex-grow-1 ml-2">
        <v-textarea rows="1" :label="translations.details_" v-model="mix.details"
          v-bind="$root.serverErrorPropsForField(serverErrors, errorKey)"
        ></v-textarea>
      
        </div>
      
        </v-card-text>
        
    </v-card>

    `,
});
