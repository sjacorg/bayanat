const RelateItemsTemplate = Vue.defineComponent({
    props: ['visible', 'dialogProps', 'loading', 'multiRelation', 'relationTypes', 'results', 'hasMore'],
    emits: ['update:visible', 'search', 'relate', 'loadMore'],
    data: () => {
      return {
        translations: window.translations,
        showSearch: true,
        relation: {
          probability: null,
          related_as: [],
          comment: '',
        }
      };
    },
    watch: {
      '$root.isConfirmRelationDialogOpen'(isOpen) {
        if (!isOpen) {
          this.relation = { probability: null, related_as: [], comment: '' }
          this.$root.relationToConfirm = null
        }
      }
    },
    template: /*html*/ `
      <v-dialog :model-value="visible" @update:model-value="$emit('update:visible', $event)" v-bind="dialogProps">
        <v-card class="d-flex flex-column h-screen pa-0" :loading="loading">
          
          <!-- Top Toolbar -->
          <v-toolbar color="dark-primary">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                  <v-btn v-bind="props" class="ml-6 mr-4" :icon="showSearch ? 'mdi-menu-open' : 'mdi-menu'" @click="showSearch = !this.showSearch"></v-btn>
              </template>
              {{ showSearch ? translations.hideSearch_ : translations.showSearch_ }}
            </v-tooltip>
            <v-btn variant="elevated" @click="$emit('search')" prepend-icon="mdi-magnify">{{ translations.search_ }}</v-btn>
            <v-spacer></v-spacer>
            <slot name="actions"></slot>
            <v-btn icon @click="$emit('update:visible', false)" class="ml-2">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-toolbar>
  
          <!-- Content -->
          <div class="overflow-y-auto">
            <split-view :left-slot-visible="showSearch" :left-width-percent="50">
              <template #left>
                <!-- Left Column: Search -->
                <div class="py-4">
                  <slot name="search-box"></slot>
                </div>
              </template>
              <template #right>
                <!-- Right Column -->
                <div class="py-6 pr-6 pl-3">
                  <v-card-text v-if="loading && !results.length" class="d-flex justify-center align-center pa-5">
                    <v-progress-circular indeterminate color="primary"></v-progress-circular>
                  </v-card-text>
                  <slot name="results-list"></slot>
  
                  <!-- Load More / No Results -->
                  <v-card-actions class="px-4 pb-4">
                    <v-spacer></v-spacer>
                    <v-btn v-if="hasMore" @click="loadMore" color="primary">{{ translations.loadMore_ }}</v-btn>
                    <span v-else class="text-grey">{{ translations.noResults_ }}</span>
                    <v-spacer></v-spacer>
                  </v-card-actions>
                </div>
              </template>
            </split-view>
          </div>
        </v-card>
      </v-dialog>
  
      <v-dialog v-if="visible" max-width="450" v-model="$root.isConfirmRelationDialogOpen">
        <v-card>
          <relation-editor-card
            variant="text"
            v-model:relation="relation"
            :multi-relation="multiRelation"
            :relation-types="relationTypes"
          ></relation-editor-card>
          
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn @click="$root.closeConfirmRelationDialog" variant="text">{{ translations.cancel_ }}</v-btn>
            <v-btn @click="$emit('relate', { item: $root.relationToConfirm, relationData: relation })" color="primary">{{ translations.relate_ }}</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
      `,
  });
  