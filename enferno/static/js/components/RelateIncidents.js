const RelateIncidents = Vue.defineComponent({
  mixins: [relatedSearchMixin],
  data: () => ({
    searchEndpoint: `/admin/api/incidents/?mode=2`,
  }),
  template: /*html*/ `
    <relate-items-template
      v-model:visible="visible"
      :dialog-props="dialogProps"
      :loading="loading"
      :results="results"
      @search="reSearch"
      @load-more="loadMore"
      :has-more="hasMore"
      :multi-relation="$root.incidentRelationMultiple"
      :relation-types="$root.incidentRelationTypes"
      @relate="relateItem"
    >
      <template v-if="$slots.actions" #actions>
        <slot name="actions"></slot>
      </template>
      <template #search-box>
        <incident-search-box 
          v-model="q"
          @search="reSearch"
          :extra-filters="false"
          :show-op="false"
        ></incident-search-box>
      </template>
      <template #results-list>
        <incident-result
          v-for="(item, i) in results"
          :key="i"
          :incident="item"
          :show-hide="true"
        >
          <template #actions>
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  @click="$root.openConfirmRelationDialog(item)"
                  color="primary"
                  variant="elevated"
                  icon="mdi-link-plus"
                  size="small"
                ></v-btn>
              </template>
              {{ translations.addAsRelated_ }}
            </v-tooltip>
          </template>
        </incident-result>
      </template>
    </relate-items-template>
    `,
});
