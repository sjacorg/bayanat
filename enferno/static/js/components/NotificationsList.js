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
                hideScrollFeedback: false,
                hideMarkAsReadButton: false
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
                    return 'mdi-information-outline';
                case 'security':
                    return 'mdi-security';
                case 'announcement':
                    return 'mdi-bullhorn';
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
        },
        getListItemColorProps(notification) {
            if (!notification) return
            const urgentUnreadProps = { variant: "flat", 'base-color': "error", class: 'text-white' }
            const urgentReadProps = { variant: "tonal", 'base-color': "error" }
            const unreadProps = { variant: "tonal", 'base-color': "primary" }
            const readProps = {}
            
            if (notification.is_urgent) {
                if (notification.read_status) {
                    return urgentReadProps
                }
                return urgentUnreadProps
            }

            if (notification.read_status) {
                return readProps
            }
            return unreadProps
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

            <v-list v-else density="default" lines="three" class="py-0">
                <v-list-item
                    v-for="(notification, index) in notifications"
                    :key="index"
                    class="py-3 mb-2 rounded-0"
                    slim
                    v-bind="getListItemColorProps(notification)"
                >
                    <template #prepend>
                        <v-icon size="small">
                            {{ getIconFromNotification(notification) }}
                        </v-icon>
                    </template>

                    <v-list-item-content>
                        <v-list-item-title
                            :class="{ 'font-weight-bold': !notification?.read_status }"
                            class="text-body-1"
                            :style="getLineClampStyles(config.maxTitleLines)"
                            v-html="notification?.title"
                        />
                        <v-list-item-subtitle class="mt-1">
                            <div
                            class="text-caption"
                            :style="getLineClampStyles(config.maxSubtitleLines)"
                            v-html="notification?.message"
                            />
                            <div class="d-flex justify-space-between align-center mt-2">
                                <span class="text-caption">{{ getDateFromNotification(notification) }}</span>
                            </div>
                        </v-list-item-subtitle>
                    </v-list-item-content>

                    <template v-if="!notification?.read_status && !config.hideMarkAsReadButton" #append>
                        <div class="d-flex align-center ga-2">
                            <v-tooltip location="bottom">
                                <template #activator="{ props }">
                                    <v-btn
                                        v-bind="props"
                                        icon
                                        variant="text"
                                        size="small"
                                        @click="$emit('readNotification', notification)"
                                    >
                                        <v-icon size="16">mdi-email-open-outline</v-icon>
                                    </v-btn>
                                </template>
                                {{ translations.markAsRead_ }}
                            </v-tooltip>
                        </div>
                    </template>
                </v-list-item>
            </v-list>

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
