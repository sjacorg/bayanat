const MixReportersField = Vue.defineComponent({
  props: {
    title: String,
    modelValue: {
      type: Array,
      default: () => ([]),
    },
    serverErrors: {
      type: Object,
      default: () => ({}),
    },
    items: {
      type: Array,
      default: () => ([]),
    },
    errorKey: {
      type: String,
      default: '',
    },
  },
  emits: ['update:modelValue'],
  data() {
    return {
      translations: window.translations,
      reporters: this.modelValue,
    };
  },
  watch: {
    modelValue: {
      handler(newVal) {
        this.reporters = newVal || [];
      },
      immediate: true,
    },
    reporters: {
      handler() {
        this.$emit('update:modelValue', this.reporters);
      },
      deep: true,
    },
  },
  methods: {
    addReporter() {
      this.reporters.push({});
    },
    removeMe(index) {
      this.reporters.splice(index, 1);
    },
    refresh() {
      this.$emit('update:modelValue', this.reporters);
    },
  },
  template: `
    <v-card class="pa-3">
      <v-toolbar>
        <v-toolbar-title class="d-flex">
        {{ translations.reportingPersons_ }}
        </v-toolbar-title>
        <template #append>
          <v-btn icon="mdi-plus-circle" @click="addReporter" color="primary"></v-btn>
          
        </template>
        
      </v-toolbar>
      <v-card-text>
        <v-card class="my-3"  v-for="(reporter, index) in reporters" :key="index">
          <v-toolbar>
            <template #append>
            <v-btn @click="removeMe(index)"  icon="mdi-close" color="primary"></v-btn>  
            </template>
            
            
          </v-toolbar>
          <v-card-text>
            <v-text-field :label="translations.name_" v-model="reporter.name"
              v-bind="$root.serverErrorPropsForField(serverErrors, errorKey+'.'+index+'.name')"
            ></v-text-field>
            <v-textarea rows="1" :label="translations.contactInfo_" v-model="reporter.contact"
              v-bind="$root.serverErrorPropsForField(serverErrors, errorKey+'.'+index+'.contact')"
            ></v-textarea>
            <v-textarea rows="1" :label="translations.relationship_" v-model="reporter.relationship"
              v-bind="$root.serverErrorPropsForField(serverErrors, errorKey+'.'+index+'.relationship')"
            ></v-textarea>
          </v-card-text>
        </v-card>
      </v-card-text>
    </v-card>
  `,
});
