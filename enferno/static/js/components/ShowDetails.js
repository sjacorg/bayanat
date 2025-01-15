const ShowDetails = Vue.defineComponent({
    props: {
        showMoreText: {
            type: String,
            default: 'Show more',
        },
        showLessText: {
            type: String,
            default: 'Show less',
        },
    },
    data() {
        return {
            isCollapsed: true,
        };
    },
    template: `
    <div>
        <v-expand-transition>
            <div v-show="!isCollapsed">
                <slot></slot>
            </div>
        </v-expand-transition>
        <v-btn
            variant="plain"
            :ripple="false"
            class="pa-0"
            height="fit-content"
            color="primary"
            @click="isCollapsed = !isCollapsed"
        >
            {{ isCollapsed ? showMoreText : showLessText }}
        </v-btn>
    </div>
  `,
});
