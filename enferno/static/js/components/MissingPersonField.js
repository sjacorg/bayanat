const MissingPersonField = Vue.defineComponent({
  props: {
    title: String,
    field: [String, Boolean, Array, Object],
    type: Number,
  },
  data: function () {
    return {
      translations: translations,
    };
  },
  computed: {
    output() {
      if (this.type === 1) {
        // type 1 = options + details
        if (!this.field) return '';
        const { opts = '', details = '' } = this.field;
        const optsText = Array.isArray(opts) ? opts.join(', ') : opts;

        if (!optsText) return details;
        if (!details) return optsText;

        return `${optsText}: ${details}`;
      }

      if (this.type === 2) {
        // type 2 = Reporters: list of objects
        return '';
      }

      // final case: simple field
      return this.field;
    },
    show() {
      if (this.type == 2) {
        return Array.isArray(this.field) && this.field.length && Object.keys(this.field[0]).length;
      }
      return !!this.field;      
    },
    reporters() {
      if (this.type !== 2 || !Array.isArray(this.field)) return [];
      return this.field.filter(rep => rep && Object.keys(rep).length);
    },
  },
  template: `
    <v-sheet v-if="show" class="pa-1 pb-2 mb-2" color="transparent">
      <div class="caption grey--text text--darken-1">{{ title }}</div>
      <template v-if="type === 2">
        <div
          v-for="(rep, index) in reporters"
          :key="index"
          class="elevation-1 my-3 pa-2 yellow lighten-5"
        >
          <div v-if="rep.name">{{ translations.name_ }}: {{ rep.name }}</div>
          <div v-if="rep.contact">{{ translations.contact_ }}: {{ rep.contact }}</div>
          <div v-if="rep.relationship">{{ translations.relationship_ }}: {{ rep.relationship }}</div>
        </div>
      </template>
      <span v-else v-text="output"></span>
    </v-sheet>
  `,
});
