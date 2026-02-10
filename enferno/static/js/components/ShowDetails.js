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
        side: {
            type: String,
            default: 'start',
        },
    },
    data() {
        return {
            isCollapsed: true,
        };
    },
    template: `
    <div :class="['d-flex', { 'flex-column': side === 'start', 'flex-column-reverse': side === 'end' }]">
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
            width="fit-content"
            color="primary"
            @click="isCollapsed = !isCollapsed"
        >
            {{ isCollapsed ? showMoreText : showLessText }}
        </v-btn>
    </div>
  `,
});

window.ShowDetails = ShowDetails;
