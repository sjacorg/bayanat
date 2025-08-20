const FieldListItem = Vue.defineComponent({
  props: ['field', 'componentProps'],
  emits: ['edit', 'delete', 'toggle-visibility'],
  template: /*html*/ `
      <div v-if="componentProps" class="d-flex ga-2 justify-center">
        <v-icon class="drag-handle cursor-grab mt-4" size="large">mdi-drag</v-icon>
                
        <div class="w-100">
            <component :is="componentProps.component" v-bind="componentProps" />
        </div>

        <div v-if="!componentProps?.readonly" class="flex-shrink-0 mt-2">
            <v-btn :disabled="field.core" icon @click="$emit('edit', { field, componentProps })" size="small"><v-icon>mdi-pencil</v-icon></v-btn>
            <v-menu>
                <template v-slot:activator="{ props }">
                    <v-btn v-bind="props" icon="mdi-dots-vertical" size="small"></v-btn>
                </template>
                <v-list>
                    <v-list-item @click="$emit('toggle-visibility', { field, componentProps })">
                        <v-list-item-title><v-icon class="mr-2">{{ componentProps.disabled ? 'mdi-eye' : 'mdi-eye-off' }}</v-icon> {{ componentProps.disabled ? 'Show' : 'Hide' }}</v-list-item-title>
                    </v-list-item>
                    <v-list-item v-if="field.active" @click="$emit('delete', { field, componentProps })" :disabled="field.core">
                        <v-list-item-title>
                            <v-icon class="mr-2" color="red">mdi-trash-can-outline</v-icon> 
                            <span class="red--text">Delete</span>
                        </v-list-item-title>
                    </v-list-item>
                </v-list>
            </v-menu>
        </div>
      </div>
      <div v-else>Field data not provided</div>
    `,
});
