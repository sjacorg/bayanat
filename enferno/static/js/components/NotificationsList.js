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
            const category = (notification?.category || '').toLowerCase();

            switch (category) {
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
            const urgentNotificationProps = { variant: "tonal", 'base-color': "error", class: 'text-white' }
            const unreadProps = { variant: "tonal", 'base-color': "primary" }
            const readProps = {}
            
            if (notification.is_urgent) {
                return urgentNotificationProps
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
                <v-divider :thickness="2" class="border-opacity-25"></v-divider>
                <v-hover v-for="(notification, index) in notifications" :key="index">
                    <template v-slot:default="{ isHovering, props: hoverProps }">
                        <v-list-item
                            class="py-3 rounded-0"
                            slim
                            v-bind="{ ...getListItemColorProps(notification), ...hoverProps }"
                        >
                            <template #prepend>
                                <v-icon size="small">
                                    {{ getIconFromNotification(notification) }}
                                </v-icon>
                            </template>

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

                            <template v-if="!notification?.read_status && !config.hideMarkAsReadButton && isHovering" #append>
                                <div class="d-flex align-center ga-2">
                                    <v-tooltip location="bottom" :style="{ zIndex: 3002 }">
                                        <template #activator="{ props }">
                                            <v-btn
                                                v-bind="props"
                                                icon="mdi-email-open-outline"
                                                variant="tonal"
                                                density="comfortable"
                                                @click="$emit('readNotification', notification)"
                                                rounded="full"
                                            ></v-btn>
                                        </template>
                                        {{ translations.markAsRead_ }}
                                    </v-tooltip>
                                </div>
                            </template>
                        </v-list-item>
                        <v-divider :thickness="2" class="border-opacity-25"></v-divider>
                    </template>
                </v-hover>
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
                    variant="text"
                    class="font-weight-medium"
                    block
                    tile
                    size="x-large"
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
