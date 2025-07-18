const NotificationsList = Vue.defineComponent({
    props: {
        initialLoading: { type: Boolean, default: false },
        notifications: { type: [Array, null], required: true },
        hasMore: { type: Boolean, default: false },
        loadingMore: { type: Boolean, default: false },
        loadError: { type: Boolean, default: false },
        config: {
            type: Object,
            default: () => ({
                maxTitleLines: 1,
                maxSubtitleLines: 2,
                hideScrollFeedback: false
            })
        }
    },
    emits: ['readNotification', 'loadNotifications'],
    data() {
        return {
            translations: window.translations
        };
    },
    methods: {
        getIconFromNotification(notification) {
            const type = (notification?.type || '').toLowerCase();

            switch (type) {
                case 'update':
                    return 'mdi-update';
                case 'security':
                    return 'mdi-security';
                default:
                    return 'mdi-bell';
            }
        },
        getDateFromNotification(notification) {
            const date = dayjs(notification?.created_at);
            return date.isValid() ? date.format('MM/DD/YYYY HH:mm') : '-';
        },
        getLineClampStyles(lines) {
            if (!lines) return 'white-space: normal;'

            return `overflow: hidden; display: -webkit-box; -webkit-line-clamp: ${lines}; -webkit-box-orient: vertical; white-space: normal;`
        }
    },
    template: `
        <div>
            <v-container v-if="initialLoading && !notifications" class="text-center">
                <v-progress-circular color="primary" indeterminate></v-progress-circular>
            </v-container>

            <v-container v-else-if="!initialLoading && !notifications?.length && !loadError">
                <v-empty-state icon="mdi-bell">
                    <template v-slot:headline>
                        <div class="text-h5">
                            {{ translations.noNotificationsYet_ }}
                        </div>
                    </template>

                    <template v-slot:text>
                        <div class="text-medium-emphasis text-caption">
                            {{ translations.noNotificationsYetDescription_ }}
                        </div>
                    </template>
                </v-empty-state>
            </v-container>

            <v-container v-else-if="loadError && !notifications?.length">
                <v-empty-state icon="mdi-bell-off">
                    <template v-slot:headline>
                        <div class="text-h5">
                            {{ translations.notificationsCouldNotBeLoaded_ }}
                        </div>
                    </template>

                    <template v-slot:text>
                        <div class="text-medium-emphasis text-caption">
                            {{ translations.weAreHavingTroubleFetchingNotifications_ }}
                        </div>
                    </template>

                    <template v-slot:actions>
                        <v-btn
                            color="primary"
                            @click="$emit('loadNotifications')"
                            :loading="initialLoading"
                        >
                            {{ translations.retry_ }}
                        </v-btn>
                    </template>
                </v-empty-state>
            </v-container>

            <v-container v-else class="pa-0">
                <v-card
                    v-for="(notification, index) in notifications"
                    :key="index"
                    density="compact"
                    :variant="notification?.read_status ? 'flat' : 'tonal'"
                    :color="notification?.read_status ? '' : 'primary'"
                    class="mb-2"
                    :rounded="0"
                    @click="$emit('readNotification', notification)"
                >
                    <v-card-title class="pb-1 d-flex justify-space-between align-center">
                        <div 
                            :class="['text-body-1', { 'font-weight-bold': !notification?.read_status }]" 
                            :style="getLineClampStyles(config.maxTitleLines)"
                            v-html="notification?.title"
                        ></div>
                        <v-tooltip location="bottom">
                            <template v-slot:activator="{ props }">
                                <v-icon v-bind="props" class="ml-2" size="x-small">{{ getIconFromNotification(notification) }}</v-icon>
                            </template>
                            {{ notification?.type }}
                        </v-tooltip>
                    </v-card-title>
                    <v-card-subtitle>
                        <div 
                            :style="getLineClampStyles(config.maxSubtitleLines)"
                            v-html="notification?.message"
                        ></div>
                        <div class="d-flex justify-space-between align-center my-2">
                            <span class="text-caption">{{ getDateFromNotification(notification) }}</span>
                            <v-chip 
                                v-if="notification?.is_urgent" 
                                color="error" 
                                size="x-small" 
                                density="compact" 
                                variant="flat"
                            >
                                {{ translations.URGENT_ }}
                            </v-chip>
                        </div>
                    </v-card-subtitle>
                </v-card>
            </v-container>

            <v-alert
                v-if="loadError && notifications?.length"
                type="error"
                class="ma-2"
                :title="translations.oops_"
                :text="translations.couldNotLoadMoreNotifications_"
                density="compact"
            ></v-alert>

            <template v-if="!config.hideScrollFeedback">
                <v-btn
                    v-if="notifications?.length && hasMore"
                    :loading="loadingMore"
                    block
                    rounded="0"
                    height="48"
                    variant="text"
                    @click="$emit('loadNotifications')"
                >
                    {{ translations.loadMore_ }}
                </v-btn>

                <v-container v-else-if="!hasMore && notifications?.length" class="text-center text-caption py-3">
                    {{ translations.noMoreNotificationsToLoad_ }}
                </v-container>
            </template>
        </div>
    `
});
