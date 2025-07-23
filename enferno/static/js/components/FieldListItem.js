const FieldListItem = Vue.defineComponent({
  props: ['field'],
  emits: ['edit', 'delete', 'toggle-visibility'],
  template: /*html*/ `
      <div v-if="field" class="d-flex ga-2 justify-center">
        <v-icon class="drag-handle cursor-grab mt-4" size="large">mdi-drag</v-icon>
                
        <div class="w-100">
            <component :is="field.component" v-bind="field.props" />
        </div>

        <div v-if="!field?.readonly" class="flex-shrink-0 mt-2">
          <v-btn icon @click="$emit('edit', field)" size="small"><v-icon>mdi-pencil</v-icon></v-btn>
          <v-btn icon @click="$emit('delete', field)" size="small"><v-icon>mdi-delete</v-icon></v-btn>
          <v-btn icon @click="$emit('toggle-visibility', field)" size="small">
            <v-icon>{{ field.active ? 'mdi-eye' : 'mdi-eye-off' }}</v-icon>
          </v-btn>
        </div>
      </div>
      <div v-else>Field data not provided</div>
    `,
});
