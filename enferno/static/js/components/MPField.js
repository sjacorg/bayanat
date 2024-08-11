const MPField = Vue.defineComponent({
  props: {
    title: String,
    field: [String, Boolean, Array, Object],
    type: Number,
  },
  data: function () {
    return {
      translations: window.translations,
    };
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
        name && `${this.translations.name_}: ${name}`,
        contact && `${this.translations.contact_}: ${contact}`,
        relationship && `${this.translations.relationship_}: ${relationship}`,
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