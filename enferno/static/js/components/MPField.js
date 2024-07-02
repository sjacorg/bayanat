const MPField = Vue.defineComponent({
  props: {
    title: String,
    field: [String, Boolean, Array, Object],
    type: Number,
    i18n: Object,
  },
  computed: {
    output() {
      if (this.type === 1) {
        // type 1 = options + details
        if (!this.field) return '';
        const { opts = '', details = '-' } = this.field;
        return `${opts}: ${details}`;
      }

      if (this.type === 2) {
        // type 2 = Reporters: list of objects
        if (!Array.isArray(this.field) || !this.field.length) return '-';
        return this.field.map(this.formatReporter).join('');
      }

      // final case: simple field
      return this.field;
    },
    show() {
      if (this.type === 1) {
        return !!this.field;
      }
      return Array.isArray(this.field) && this.field.length && Object.keys(this.field[0]).length;
    },
  },
  methods: {
    formatReporter(rep) {
      const { name, contact, relationship } = rep;
      const output = [
        name && `${this.i18n.name_}: ${name}`,
        contact && `${this.i18n.contact_}: ${contact}`,
        relationship && `${this.i18n.relationship_}: ${relationship}`,
      ]
        .filter(Boolean)
        .join('<br>');

      return output ? `<div class="elevation-1 my-3 pa-2 yellow lighten-5">${output}</div>` : '';
    },
  },
  template: `
    <v-sheet v-if="show" class="pa-1 pb-2 mb-2" color="transparent">
      <div class="caption grey--text text--darken-1">{{ title }}</div>
      <span v-html="output"></span>
    </v-sheet>
  `,
});