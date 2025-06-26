const IdNumberDynamicField = Vue.defineComponent({
  props: {
    modelValue: {
      type: [String, Array],
      required: true,
      default: () => [{ type: '', number: '', id: generateRandomId() }],
    },
  },
  emits: ['update:modelValue'],
  data: () => {
    return {
      translations: window.translations,
    };
  },
  methods: {
    updateRowType(nextType, row) {
      // this.modelValue.find(item => item.)

      this.$emit('update:modelValue', this.modelValue)
    }
  },
  template: /*html*/ `
    <div>
      <template v-if="Array.isArray(modelValue)">
        <v-card>
          <v-card-item>
            <v-card-title>{{ translations.idNumber_ }}</v-card-title>
          </v-card-item>
          <v-card-text>
            <div v-for="(row) in modelValue" :key="row.id">
              <v-text-field
                :modelValue="row.type"
                @update:modelValue="updateRowType($event, row)"
                :label="translations.type_"
              ></v-text-field>
              <v-text-field
                :modelValue="row.number"
                @update:modelValue="$emit('update:modelValue', $event)"
                :label="translations.type_"
              ></v-text-field>
            </div>
          </v-card-text>
        </v-card>
      </template>
      <template v-else>
        <v-text-field
            :modelValue="modelValue"
            @update:modelValue="$emit('update:modelValue', $event)"
            :label="translations.idNumber_"
        ></v-text-field>
      </template>
    </div>
  `,
});
