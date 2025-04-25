const NotificationsList = Vue.defineComponent({
    props: [
        'isInitialLoadingNotifications',
        'notifications',
        'hasMoreNotifications',
        'isLoadingMoreNotifications',
        'maxTitleLines',
        'maxSubtitleLines',
        'hideScrollFeedback'
    ],
    emits: ['readNotification', 'loadNotifications'],
    data() {
        return {
            translations: window.translations
        };
    },
    methods: {
        getIconFromNotification(notification) {
            switch (notification?.type?.toLowerCase()) {
                case 'update':
                    return 'mdi-update';
                case 'security':
                    return 'mdi-security';
                default:
                    return 'mdi-bell';
            }
        },
        getDateFromNotification(notification) {
            return dayjs(notification?.created_at).format('MM/DD/YYYY HH:mm');
        },
        getLineClampStyles(lines) {
            if (!lines) return 'white-space: normal;'

            return `overflow: hidden; display: -webkit-box; -webkit-line-clamp: ${lines}; -webkit-box-orient: vertical; white-space: normal;`
        }
    },
    template: `
        <div>
            <v-container v-if="isInitialLoadingNotifications && !notifications" class="text-center">
                <v-progress-circular color="primary" indeterminate></v-progress-circular>
            </v-container>

            <v-container v-else-if="!isInitialLoadingNotifications && !notifications?.length">
                <v-empty-state icon="mdi-bell">
                    <template v-slot:media>
                        <v-icon color="surface-variant"></v-icon>
                    </template>

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
                            :class="['text-body-1', { 'font-weight-bold': !notification.read_status }]" 
                            :style="getLineClampStyles(maxTitleLines ?? 1)"
                            v-html="notification.title"
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
                            :style="getLineClampStyles(maxSubtitleLines ?? 2)"
                            v-html="notification.message"
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

            <template v-if="!hideScrollFeedback">
                <v-btn
                    v-if="notifications?.length && hasMoreNotifications"
                    :loading="isLoadingMoreNotifications"
                    block
                    rounded="0"
                    height="48"
                    variant="text"
                    @click="$emit('loadNotifications')"
                >
                    {{ translations.loadMore_ }}
                </v-btn>

                <v-container v-else-if="!hasMoreNotifications && notifications?.length" class="text-center text-caption py-3">
                    {{ translations.noMoreNotificationsToLoad_ }}
                </v-container>
            </template>
        </div>
    `
});
