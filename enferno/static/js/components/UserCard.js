const actionSections = {
  suspend: {
    title: (name) => `You're about to suspend the account for user \"${name}\"`,
    confirmationText: (name) => `By entering your password, you will confirm the suspend action for user \"${name}\"`,
    acceptButtonText: "Suspend Account",
    acceptButtonColor: "warning",
    blocks: [
      { icon: "mdi-account-circle", title: "Intended for", description: "Temporary suspensions, such as during internal investigations or when the user is on leave." },
      { icon: "mdi-account-key", title: "Roles and Access Removal", bullets: ["The user will no longer be able to log in to Bayanat.", "Their system roles, access permissions, and assigned items will remain unchanged."] },
    ],
  },
  reactivate: {
    title: (name) => `You're about to reactivate user \"${name}\"`,
    confirmationText: (name) => `By entering your password, you will confirm the reactivation for user \"${name}\"`,
    acceptButtonText: "Reactivate Account",
    acceptButtonColor: "success",
    blocks: [
      { icon: "mdi-account", title: "Roles and Access Restoration", bullets: ["Previous system roles and access permissions will be restored.", "User can log in to Bayanat and perform actions allowed by their roles."] },
      { icon: "mdi-key", title: "Profile and Contributions", bullets: ["The user will be able to view and edit items they previously had access to."] },
    ],
  },
  disable: {
    title: (name) => `You're about to disable the account for user \"${name}\"`,
    confirmationText: (name) => `By entering your password, you will confirm the disable action for user \"${name}\"`,
    acceptButtonText: "Disable Account",
    acceptButtonColor: "error",
    blocks: [
      { icon: "mdi-account-circle", title: "Intended for", description: "Permanently ending a user's access to Bayanat, such as when they leave the organization." },
      { icon: "mdi-account-key", title: "Roles and Access Removal", bullets: ["The user will no longer be able to log in to Bayanat.", "All system roles and access permissions will be removed.", "Items assigned to the user will be unassigned and available for reassignment."] },
      { icon: "mdi-briefcase-clock-outline", title: "Profile and Contributions", bullets: ["The user's profile will be retained for archival purposes.", "Items created or updated by the user will remain in Bayanat.", "Activity history will continue to reflect the user's contributions."] },
    ],
  },
  enable: {
    title: (name) => `You're about to enable the account for user \"${name}\"`,
    confirmationText: (name) => `By entering your password, you will confirm enabling the account for user \"${name}\"`,
    acceptButtonText: "Enable Account",
    acceptButtonColor: "success",
    blocks: [
      { icon: "mdi-account", title: "Roles and Access Restoration", bullets: ["The user will be able to log in once a system role is assigned.", "User can use their existing password to access Bayanat."] },
      { icon: "mdi-key", title: "Profile and Contributions", bullets: ["The user's previous profile and contributions remain intact."] },
    ],
  },
}

const UserCard = Vue.defineComponent({
  props: ['user', 'closable'],
  emits: ['close', 'edit', 'resetPassword', 'revoke2fa', 'logoutAll', 'changePassword'],
  components: { ConfirmDialog },
  data() {
    return {
      translations: window.translations,
      show: false,
      sessions: [],
      page: 1,
      perPage: 5,
      more: true,
      actionSections,
    };
  },
  computed: {
    isUserSuspended() {
      return !this.user.active && !this.user?.deleted;
    },
    isUserDisabled() {
      return !this.user.active && this.user?.deleted;
    },
    isUserEnabled() {
      return !this.user?.deleted;
    },
    permissions() {
      // [permissionKey, translationIfAllowed, translationIfDenied]
      const rows = [
        ['view_usernames', 'canViewUsernames_', 'cannotViewUsernames_'],
        ['view_simple_history', 'canViewSimpleHistory_', 'cannotViewSimpleHistory_'],
        ['view_full_history', 'canViewFullHistory_', 'cannotViewFullHistory_'],
        ['can_edit_locations', 'canEditLocations_', 'cannotEditLocations_'],
        ['can_export', 'canExport_', 'cannotExport_'],
        ['can_self_assign', 'canSelfAssign_', 'cannotSelfAssign_'],
      ];

      return rows.map(([key, yes, no]) => ({
        value: this.user[key],
        label: this.user[key] ? this.translations[yes] : this.translations[no],
      }));
    }
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

    openLogoutSessionDialog(id) {
      this.$root.$confirm({
        title: translations.youreAboutToEndThisSession_,
        message: `${translations.afterThisActionTheUserWillBeSignedOut_}\r\n\r\n${translations.doYouWantToContinue_}`,
        acceptProps: { text: translations.endSession_, color: 'error' },
        dialogProps: { width: 780 },
        onAccept: () => {
          axios
            .delete('/admin/api/session/logout', {
              data: { sessid: id },
            })
            .then((response) => {
              console.log('Logged out session');
              if (response.data.redirect) {
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
      });
    },
    getTwoFactorDeviceMeta(device) {
      return { icon: device.type === 'authenticator' ? 'mdi-lock-clock' : 'mdi-usb-flash-drive', color: 'success', text: device.name };
    },
    openAccountDialog(mode) {
      this.$refs.accountActionDialog.show({
        dialogProps: { width: 691 },
        data: { mode },
        acceptProps: { text: actionSections[mode].acceptButtonText, color: actionSections[mode].acceptButtonColor },
        onAccept: async () => {
          console.log(`${mode} account...`)
        }
      })
    },

    suspendAccount() {
      this.openAccountDialog("suspend");
    },
    disableAccount() {
      this.openAccountDialog("disable");
    },
    reactivateAccount() {
      this.openAccountDialog("reactivate");
    },
    enableAccount() {
      this.openAccountDialog("enable");
    },
  },
  watch: {
    user(val, old) {
      this.resetSessions();
      this.fetchSessions();
    },
  },
  template: `
      <confirm-dialog ref="accountActionDialog">
        <template #title="{ data }">
          {{ actionSections[data.mode].title(user.name) }}
        </template>
        <template #default="{ data }">
          <div class="text-body-2 mb-6 mt-3">What you should know</div>
          <div class="d-flex flex-column ga-6">
            <div v-for="(block, index) in actionSections[data.mode].blocks" :key="index" class="d-flex">
              <v-avatar color="white">
                <v-icon color="primary" size="x-large">{{ block.icon }}</v-icon>
              </v-avatar>
    
              <div class="ml-3">
                <h4 class="text-primary">{{ block.title }}</h4>
                <div v-if="block?.description" class="text-body-2">{{ block.description }}</div>
                <ul v-if="block?.bullets" class="text-body-2 pl-5">
                  <li v-for="(bullet, index) in block.bullets" :key="index">{{ bullet }}</li>
                </ul>
              </div>
            </div>
          </div>
          <div class="text-body-2 mt-6">
            {{ actionSections[data.mode].confirmationText(user.name) }}
            <v-text-field variant="filled" class="mt-3"></v-text-field>
          </div>
        </template>
      </confirm-dialog>

      <v-card class="mx-auto">
        <v-sheet class="px-6 py-5 d-flex align-center">
          <v-toolbar-title>
            <div class="d-flex justify-space-between ga-2 align-center">
              <div class="d-flex flex-column">
                <div class="d-flex align-center ga-2">
                  {{ user.name }}
      
                  <v-chip color="primary">
                    <v-icon size="x-large">mdi-identifier</v-icon>
                    {{ user.id }}
                  </v-chip>
  
                  <v-chip :color="$root.getUserStatusMeta(user)?.color">
                    <v-icon class="mr-1" size="x-large">{{ $root.getUserStatusMeta(user)?.icon }}</v-icon>
                    {{ $root.getUserStatusMeta(user)?.text }}
                  </v-chip>
                </div>
    
                <div>
                  <v-chip prepend-icon="mdi-account-circle-outline" variant="plain" class="text-body-2">
                    {{ user.username }}
                  </v-chip>
      
                  <v-chip v-if="user.email" prepend-icon="mdi-email-outline" variant="plain" class="text-body-2">
                    {{ user.email }}
                  </v-chip>
                </div>
              </div>

              <v-chip
                v-if="user.force_reset && isUserEnabled"
                color="error"
                variant="text"
                class="font-weight-medium"
              >
                <v-icon size="x-large">mdi-exclamation</v-icon>
                {{ translations.passwordResetRequested_ }}
              </v-chip>
  
              <div class="d-flex justify-space-between ga-2 align-center">
                <template v-if="isUserEnabled">
                  <v-tooltip
                    location="bottom"
                    :text="user.force_reset ? translations.passwordResetAlreadyRequested_ : translations.forcePasswordReset_"
                  >
                    <template #activator="{props}">
                      <div v-bind="props">
                        <v-btn
                          :disabled="user.force_reset != null"
                          color="error"
                          density="comfortable"
                          icon="mdi-lock-reset"
                          @click="$emit('resetPassword', user)"
                        ></v-btn>
                      </div>
                    </template>
                  </v-tooltip>

                  <v-tooltip
                    location="bottom"
                    :text="translations.changePassword_"
                  >
                    <template #activator="{props}">
                      <div v-bind="props">
                        <v-btn
                          :disabled="user.force_reset != null"
                          color="warning"
                          density="comfortable"
                          icon="mdi-form-textbox-password"
                          @click="$emit('changePassword', user)"
                        ></v-btn>
                      </div>
                    </template>
                  </v-tooltip>

                  <v-tooltip
                    v-if="user.two_factor_devices && user.two_factor_devices.length > 0"
                    location="bottom"
                    :text="translations.revoke2fa_"
                  >
                    <template #activator="{props}">
                      <div v-bind="props">
                        <v-btn
                          
                          @click.stop="$emit('revoke2fa', user.id)"
                          variant="outlined"
                          color="warning"
                          density="comfortable"
                          icon="mdi-lock-remove"
                        ></v-btn>
                      </div>
                    </template>
                  </v-tooltip>

                  <v-tooltip
                    location="bottom"
                    :text="translations.editUser_"
                  >
                    <template #activator="{props}">
                      <div v-bind="props">
                        <v-btn
                          variant="outlined"
                          density="comfortable"
                          icon="mdi-pencil"
                          @click="$emit('edit', user)"
                        ></v-btn>
                      </div>
                    </template>
                  </v-tooltip>
                </template>

                <v-btn v-if="closable" size="small" variant="flat" icon="mdi-close" @click="$emit('close')"></v-btn>
              </div>
            </div>
          </v-toolbar-title>
        </v-sheet>
        <v-divider></v-divider>

        <v-card v-if="isUserEnabled" variant="flat">
          <v-card-text class="px-6">
            <v-row>
              <v-col cols="12" sm="6" md="4">
                <div class="mb-3 text-body-1">{{ translations.systemRole_ }}</div>
                <div class="d-flex flex-wrap ga-3">
                  <template v-if="user.roles.length">
                    <toggle-button
                      v-for="(role, index) in user.roles"
                      :key="index"
                      read-only
                      hide-left-icon
                      :model-value="true"
                    >
                      {{ $root.systemRoles.find(r => r.value === role.name.toLowerCase())?.name ?? role.name }}
                    </toggle-button>
                  </template>
                  <template v-else>
                    <toggle-button
                      read-only
                      hide-left-icon
                      :model-value="true"
                    >
                      {{ translations.view_ }}
                    </toggle-button>
                  </template>
                </div>
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <div class="mb-3 text-body-1">{{ translations.accessRole_ }}</div>
                <div class="d-flex flex-wrap ga-3">
                  <template v-if="user?.access_roles?.length">
                    <toggle-button
                      v-for="(role, index) in user.access_roles"
                      :key="index"
                      read-only
                      hide-left-icon
                      :model-value="true"
                    >
                      {{ role.name }}
                    </toggle-button>
                  </template>
                </div>
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <div class="mb-3 text-body-1">{{ translations.twoFactorAuthentication_ }}</div>
                <div class="d-flex flex-wrap ga-3">
                  <div
                    v-if="user?.two_factor_devices?.length > 0"
                    class="d-flex flex-column ga-2 font-weight-medium text-success"
                  >
                    <v-chip v-for="device in user.two_factor_devices" :key="device.id" :color="getTwoFactorDeviceMeta(device)?.color" variant="text" class="font-weight-medium">
                      <v-icon start size="large">{{ getTwoFactorDeviceMeta(device)?.icon }}</v-icon>
                      {{ getTwoFactorDeviceMeta(device)?.text }}
                    </v-chip>
                  </div>

                  <v-chip
                    v-else
                    color="warning"
                    variant="text"
                    class="font-weight-medium"
                  >
                    <v-icon start size="large">mdi-lock-open-alert</v-icon>
                    {{ translations.twoFaInactive_ }}
                  </v-chip>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <v-card v-if="isUserEnabled" variant="flat">
          <v-card-text class="px-6">
            <div class="mb-3 text-body-1">{{ translations.userPermissions_ }}</div>
            <div class="d-flex flex-wrap ga-3">
              <toggle-button
                v-for="(permission, index) in permissions"
                :key="index"
                read-only
                :model-value="permission.value"
              >
                {{ permission.label }}
              </toggle-button>
            </div>
          </v-card-text>
        </v-card>

        <v-card variant="flat">
          <v-card-text class="px-6">
            <div class="mb-3 text-body-1">{{ translations.manageAccount_ }}</div>
            <div class="d-flex flex-wrap ga-3">
              <v-btn v-if="isUserSuspended" @click="reactivateAccount()" variant="outlined" color="success" prepend-icon="mdi-play-circle">{{ translations.reactivateAccount_ }}</v-btn>
              <v-btn v-if="!isUserSuspended" @click="suspendAccount()" variant="outlined" color="warning" prepend-icon="mdi-pause-circle">{{ translations.suspendAccount_ }}</v-btn>
              <v-btn v-if="isUserDisabled" @click="enableAccount()" variant="outlined" color="success" prepend-icon="mdi-arrow-down-thin-circle-outline">{{ translations.enableAccount_ }}</v-btn>
              <v-btn v-if="!isUserDisabled" @click="disableAccount()" variant="outlined" color="error" prepend-icon="mdi-minus-circle">{{ translations.disableAccount_ }}</v-btn>
            </div>
          </v-card-text>
        </v-card>

        <v-card v-if="isUserEnabled" class="mt-2" variant="flat">
          <v-card-text class="px-6">
            <div class="d-flex justify-space-between align-center mb-2">
              <div class="text-body-1">{{ translations.userSessions_ }}</div>
              <v-btn
                v-if="sessions.length"
                @click.stop="$emit('logoutAll', user.id)"
                variant="outlined"
                prepend-icon="mdi-logout"
                color="error"
              >
                {{ translations.logoutAll_ }}
              </v-btn>
            </div>

            <v-table fluid>
              <thead>
              <tr>
                <th class="text-left">{{ translations.session_ }}</th>
                <th class="text-left">{{ translations.device_ }}</th>
                <th class="text-left">{{ translations.browser_ }}</th>
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
                  {{ session.meta.os }}
                </td>
                <td class="text-caption">
                  {{ session.meta.browser }}
                </td>
                <td class="text-caption">{{ $root.formatDate(session.created_at, $root.dateFormats.standardDatetime, $root.dateOptions.local) }}</td>
                <td>
                  <v-btn
                    icon="mdi-logout"
                    variant="plain" v-if="session.details?._fresh"
                    @click="openLogoutSessionDialog(session.id)" :disabled="!session.is_active"
                    color="error"
                  ></v-btn>
                </td>
              </tr>
              </tbody>
            </v-table>
          </v-card-text>
          <v-card-text class="text-center">
            <v-btn variant="outlined" v-if="more" @click="fetchSessions(page, perPage)">{{ translations.loadMore_ }}</v-btn>
          </v-card-text>
        </v-card>
      </v-card>
    `,
});
