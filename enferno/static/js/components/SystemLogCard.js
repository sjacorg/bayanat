const SystemLogCard = Vue.defineComponent({
    props: ['log', 'close'],
    data: function () {
        return {
          translations: window.translations,
        };
      },
    computed: {
        formattedStacktrace() {
            return this.log.exception.traceback.replace(/\n/g, '<br>');
        },
        hasException() {
            return this.log.exception && Object.keys(this.log.exception).length > 0;
        },
        hasTrace() {
            return this.log.exception && this.log.exception.traceback && this.log.exception.traceback.length > 0;
        },
        getLevelIcon() {
            switch (this.log?.level?.toLowerCase()) {
                case 'error': return 'mdi-alert-circle';
                case 'warning': return 'mdi-alert';
                case 'info': return 'mdi-information-outline';
                case 'debug': return 'mdi-bug';
                default: return 'mdi-message-bulleted'; // default icon if no match
            }
        },
        getLogColor() {
            switch (this.log?.level?.toLowerCase()) {
                case 'error': return 'red';
                case 'warning': return 'orange';
                case 'info': return 'primary';
                case 'debug': return 'secondary';
                default: return 'grey'; // default color if no match
            }
        }
        
    },
    mounted() { },
    methods: {
        parseMessage() {
            return this.log?.message.split(":");
        },
        getLevelString(){
            // Return the translation of the log level
            return translations.levels[this.log.level?.toLowerCase()].toUpperCase();
        },
    },
    template: `
    <v-card color="grey lighten-3" v-if="log != null">
            <v-toolbar color="white" class="d-flex">
                <!-- Time -->
                <v-tooltip :text="translations.time_">
                    <template v-slot:activator="{ props }">
                        <v-chip prepend-icon="mdi-clock" size="small" class="ml-2 my-1" v-bind="props">
                            {{ log.timestampFmt }}
                        </v-chip>
                    </template>
                </v-tooltip>

                <!-- Log Level Chip -->
                <v-tooltip :text="translations.level_">
                    <template v-slot:activator="{ props }">
                        <v-chip :prepend-icon="getLevelIcon" size="small" :color="getLogColor" class="ml-2 my-1" v-bind="props">
                            {{ getLevelString() }}
                        </v-chip>
                    </template>
                </v-tooltip>

                <!-- Error Type -->
                <v-tooltip :text="translations.errType_">
                    <template v-slot:activator="{ props }">
                        <v-chip v-if="log.exception?.type" prepend-icon="mdi-tag" size="small" color="red" class="ml-2 my-1" v-bind="props">
                            {{ log.exception?.type }}
                        </v-chip>
                    </template>
                </v-tooltip>

                <!-- Logger -->
                <v-tooltip :text="translations.logger_">
                    <template v-slot:activator="{ props }">
                        <v-chip prepend-icon="mdi-tag" size="small" class="ml-2 my-1" v-bind="props">
                            {{ log.logger }}
                        </v-chip>
                    </template>
                </v-tooltip>
                <!-- Error Path -->
                <v-tooltip :text="translations.path_">
                    <template v-slot:activator="{ props }">
                        <v-chip prepend-icon="mdi-file" size="small" class="ml-2 my-1"  v-bind="props">
                            {{ log.pathname }}
                        </v-chip>
                    </template>
                </v-tooltip>
                
                <!-- Error Line No -->
                <v-tooltip :text="translations.lineno_">
                    <template v-slot:activator="{ props }">
                        <v-chip prepend-icon="mdi-timeline-alert" size="small" class="ml-2 my-1"  v-bind="props">
                            {{ log.lineno }}
                        </v-chip>
                    </template>
                </v-tooltip>

                <!-- User ID -->
                <v-tooltip :text="translations.userid_">
                    <template v-slot:activator="{ props }">
                        <v-chip v-if="log.user_id" prepend-icon="mdi-account" size="small" class="ml-2 my-1"  v-bind="props">
                            {{ log.user_id }}
                        </v-chip>
                    </template>
                </v-tooltip>

                <!-- Endpoint -->
                <v-tooltip :text="translations.endpoint_">
                    <template v-slot:activator="{ props }">
                        <v-chip v-if="log.endpoint" prepend-icon="mdi-api" size="small" class="ml-2 my-1"  v-bind="props">
                            {{ log.endpoint }}
                        </v-chip>
                    </template>
                </v-tooltip>

            </v-toolbar>

            <v-card>
                <v-card-text>
                    <v-row>
                        <v-col>
                            <v-list variant="plain" class="mx-2 my-1 pa-2 align-center">
                                <v-list-item :title="translations.message_">
                                    {{ log.message }}
                                </v-list-item>
                                <v-list-item v-if='log.exception?.traceback' :title="translations.stacktrace_">
                                    <div v-html="formattedStacktrace"></div>
                                </v-list-item>
                            </v-list>
                        </v-col>
                    </v-row>
                </v-card-text>
            </v-card>
    </v-card>
    `


})
window.SystemLogCard = SystemLogCard;
