const FieldListItem = Vue.defineComponent({
  props: ['field'],
  emits: ['edit', 'delete', 'toggle-visibility'],
  template: /*html*/ `
      <div v-if="field" class="d-flex ga-2 justify-center">
        <v-icon class="drag-handle cursor-grab mt-4" size="large">mdi-drag</v-icon>
                
        <div class="w-100">
            <component :is="field.component" v-bind="field" />
        </div>

        <div v-if="!field?.readonly" class="flex-shrink-0 mt-2">
            <v-btn icon @click="$emit('edit', field)" size="small"><v-icon>mdi-pencil</v-icon></v-btn>
            <v-menu>
                <template v-slot:activator="{ props }">
                    <v-btn v-bind="props" icon="mdi-dots-vertical" size="small"></v-btn>
                </template>
                <v-list>
                    <v-list-item @click="$emit('toggle-visibility', field)">
                        <v-list-item-title><v-icon class="mr-2">{{ field.disabled ? 'mdi-eye' : 'mdi-eye-off' }}</v-icon> {{ field.disabled ? 'Show' : 'Hide' }}</v-list-item-title>
                    </v-list-item>
                    <v-list-item @click="$emit('delete', field)" disabled>
                        <v-list-item-title><v-icon class="mr-2">mdi-delete</v-icon> Delete</v-list-item-title>
                    </v-list-item>
                </v-list>
            </v-menu>
        </div>
      </div>
      <div v-else>Field data not provided</div>
    `,
});
