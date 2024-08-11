const UserCard = Vue.defineComponent({
  props: ['user', 'close'],
  emits: ['close'],
  watch: {
    user: function (val, old) {
      this.resetSessions();
      this.fetchSessions();
    },
  },

  mounted() {
    this.fetchSessions();
  },

  methods: {
    resetSessions() {
      this.sessions = [];
      this.page = 1;
      this.more = true;
    },

    fetchSessions(page = this.page, perPage = this.perPage) {
      if (!this.more) return;

      axios
        .get(`/admin/api/user/${this.user.id}/sessions`, {
          params: {
            page: page,
            per_page: perPage,
          },
        })
        .then((response) => {
          if (response.data.items.length) {
            this.sessions = this.sessions.concat(response.data.items);
            this.page++;
            this.more = response.data.more;
          } else {
            this.more = false;
          }
        })
        .catch((err) => {
          if (err.response && err.response.status === 401) {
            alert(this.translations.loggedOut_);
            window.location.href = '/login'; // Redirect to login page
          } else {
            console.error('Error fetching sessions', err);
          }
        });
    },

    logoutSession(id) {


      axios
        .delete('/admin/api/session/logout', {
          data: {
            sessid: id,
          },
        })
        .then((response) => {
          console.log('Logged out session');
          if (response.data.redirect) {
            // Perform the redirection to the root path
            window.location.href = '/';
          } else {
            this.resetSessions();
            this.fetchSessions();
          }
        })
        .catch((err) => {
          console.error('Error logging out session', err);
        });
    },

    logoutAllSessions(userId) {
      if (window.confirm(this.translations.logoutConfirmation_)) {
        axios
          .delete(`/admin/api/user/${this.user.id}/sessions/logout`)
          .then((response) => {
            console.log('All sessions logged out successfully for user ID:', userId);
            this.$root.showSnack(this.translations.allSessionsLoggedOut_);
            this.resetSessions();
            this.fetchSessions();
          })
          .catch((err) => {
            console.error('Error logging out all sessions for user ID:', userId, err);
          });
      }
    },
  },

  data: function () {
    return {
      translations: window.translations,
      show: false,
      sessions: [],
      page: 1,
      perPage: 5,
      more: true,
    };
  },

  template: `
      <v-card class="mx-auto">
        <v-sheet class="px-6 py-4 d-flex align-center">
          <v-toolbar-title>
            {{ user.name }}

            <v-chip prepend-icon="mdi-identifier" class="mx-1" color="primary">
              {{ user.id }}
            </v-chip>

            <v-chip prepend-icon="mdi-account-circle-outline" class="mx-1" color="primary">
              {{ user.username }}
            </v-chip>

            <v-chip v-if="user.email" prepend-icon="mdi-email" class="mx-1" color="primary">
              {{ user.email }}
            </v-chip>

          </v-toolbar-title>

          <v-spacer></v-spacer>
          <v-btn v-if="close" size="small" variant="flat" icon="mdi-close" @click="$emit('close')"></v-btn>

        </v-sheet>
        <v-divider></v-divider>


        <v-card variant="flat" class="mt-3 pa-3">

          <v-label class="ml-3">
            {{ translations.userPermissions_ }}
          </v-label>
          <v-card-text>

            <v-chip class="ma-2" :color="user.view_usernames ? 'primary' : 'error'"
                    :prepend-icon="user.view_usernames ? 'mdi-checkbox-marked-circle' : 'mdi-close-circle'">
              {{ translations.canViewUsernames_ }}
            </v-chip>

            <v-chip class="ma-2" :color="user.view_simple_history ? 'primary' : 'error'"
                    :prepend-icon="user.view_simple_history ? 'mdi-checkbox-marked-circle' : 'mdi-close-circle'">
              {{ translations.canViewSimpleHistory_ }}
            </v-chip>

            <v-chip class="ma-2" :color="user.view_full_history ? 'primary' : 'error'"
                    :prepend-icon="user.view_full_history ? 'mdi-checkbox-marked-circle' : 'mdi-close-circle'">
              {{ translations.canViewFullHistory_ }}
            </v-chip>

            <v-chip class="ma-2" :color="user.can_edit_locations ? 'primary' : 'error'"
                    :prepend-icon="user.can_edit_locations ? 'mdi-checkbox-marked-circle' : 'mdi-close-circle'">
              {{ translations.canEditLocations_ }}
            </v-chip>

            <v-chip class="ma-2" :color="user.can_export ? 'primary' : 'error'"
                    :prepend-icon="user.can_export ? 'mdi-checkbox-marked-circle' : 'mdi-close-circle'">
              {{ translations.canExport_ }}
            </v-chip>

            <v-chip class="ma-2" :color="user.can_self_assign ? 'primary' : 'error'"
                    :prepend-icon="user.can_self_assign ? 'mdi-checkbox-marked-circle' : 'mdi-close-circle'">
              {{ translations.canSelfAssign_ }}
            </v-chip>


          </v-card-text>
        </v-card>

        <v-divider></v-divider>
        
         <v-card variant="flat" class="mt-3 pa-3">

          <v-label class="ml-3">
            {{ translations.userTwoFactorMethods_ }}
          </v-label>

          <v-card-text class="d-flex ga-3">

            <v-chip
              v-for="device in user.two_factor_devices"
              :key="device.id"
              :prepend-icon="device.type === 'authenticator' ? 'mdi-lock-clock' : 'mdi-usb-flash-drive'"
              color="primary"
            >
              {{ device.name }}
            </v-chip>

            <v-chip
              v-if="user.two_factor_devices.length == 0"
              prepend-icon="mdi-lock-open-alert"
              color="error"
              label
            >
              {{ translations.noTwoFactorMethods_ }}
            </v-chip>


          </v-card-text>
        </v-card>

        <v-divider></v-divider>

        <v-card class="mt-2" variant="flat">

          <v-card-text>
            <v-label class="ml-3">{{ translations.userSessions_ }}</v-label>
            <v-table fluid>

              <thead>
              <tr>
                <th class="text-left">{{ translations.session_ }}</th>
                <th class="text-left">{{ translations.ip_ }}</th>
                <th class="text-left">{{ translations.userAgent_ }}</th>
                <th class="text-left">{{ translations.started_ }}</th>
                <th class="text-left">{{ translations.logOffThisDevice_ }}</th>
              </tr>
              </thead>
              <tbody>
              <tr v-for="session in sessions"
                  
                  :class="session.active ? 'bg-yellow-lighten-5':'' ">
                <td>
                  
                  <v-tooltip v-if="session.details?._fresh">
                    <template #activator="{ props }">
                      <v-icon v-bind="props" color="green">
                        mdi-circle
                      </v-icon>
                    </template>
                    {{ translations.active_ }}
                  </v-tooltip>

                  <v-tooltip v-else>
                    <template #activator="{ props }">
                      <v-icon color="grey-darken-5" v-bind="props">mdi-circle</v-icon>
                    </template>
                    {{ translations.inactive_ }}
                  </v-tooltip>


                </td>
                <td>
                  <v-chip label>{{ session.ip_address }}</v-chip>
                </td>
                <td class="text-caption">
                  {{ session.meta.device }}
                </td>
                <td class="text-caption">{{ session.created_at }}</td>
                <td>
                  <v-btn icon="mdi-logout" variant="plain" v-if="session.details?._fresh"
                         @click.once="logoutSession(session.id)" :disabled="!session.is_active"
                         color="error">

                  </v-btn>
                </td>
              </tr>
              </tbody>
            </v-table>
          </v-card-text>
          <v-card-text class="text-center">
            <v-btn icon="mdi-dots-horizontal" variant="plain" v-if="more" fab small @click="fetchSessions(page, perPage)">
              
            </v-btn>
          </v-card-text>
          <v-divider></v-divider>

          <v-card-actions class="text-center justify-center pa-5">
            <v-btn variant="elevated" prepend-icon="mdi-logout" @click.stop="logoutAllSessions" color="error">
              {{ translations.logoutAllSessions_ }}
            </v-btn>

          </v-card-actions>
        </v-card>
      </v-card>
    `,
});
