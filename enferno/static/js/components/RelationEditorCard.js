const RelationEditorCard = Vue.defineComponent({
  props: {
    relation: {
      type: Object,
      required: true,
      default: () => ({
        probability: null,
        related_as: [],
        comment: '',
      }),
    },
    multiRelation: {
      type: Boolean,
      required: true,
    },
    relationTypes: {
      type: Array,
      required: true,
      default: () => [],
    },
  },
  emits: ['update:relation'],
  data: () => {
    return {
      translations: window.translations,
    };
  },
  template: `
    <v-card>
      <v-card-item>
        <v-card-title>{{ translations.relation_ }} <v-chip v-if="$root.relationToConfirm?.id" prepend-icon="mdi-identifier" class="ml-1">{{ $root.relationToConfirm?.id }}</v-chip></v-card-title>
      </v-card-item>
      <v-card-text>
        <v-list-item :title="translations.probability_">
          <v-list-item-subtitle>
            <v-chip-group
              v-model="relation.probability"
              column
              selected-class="bg-primary"
            >
              <v-chip filter v-for="item in translations.probs"
                      size="small">{{ item.tr }}
              </v-chip>
            </v-chip-group>
          </v-list-item-subtitle>

        </v-list-item>

        <v-list-item :title="translations.relatedAs_">
          <v-list-item-subtitle>
            <v-chip-group
              v-model="relation.related_as"
              column
              filter
              selected-class="bg-primary"
              :multiple="multiRelation"
            >
              <v-chip v-for="rel in relationTypes"
                      :value="rel.id"
                      :key="rel.id" size="small"> {{ rel.title }}
              </v-chip>
            </v-chip-group>
          </v-list-item-subtitle>
        </v-list-item>


        <v-list-item :title="translations.comments_">
          <v-list-item-subtitle>
            <v-text-field class="mt-2"
                          v-model="relation.comment"
                          variant="outlined"
                          rows="1"
                          clearable
            ></v-text-field>
          </v-list-item-subtitle>
        </v-list-item>
      </v-card-text>
    </v-card>
  `,
});
