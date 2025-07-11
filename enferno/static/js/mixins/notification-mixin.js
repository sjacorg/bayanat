const notificationMixin = {
  components: {
    'NotificationsList': NotificationsList,
  },
  computed: {
    hasUnreadNotifications() {
      return Boolean(this.notifications.unreadCount)
    },
  },
  data: () => ({
    // New state
    notifications: {
      items: null,
      importantItems: [],
      unreadCount: 0,
      total: 0,
      hasMore: false,
      pagination: {
        page: 1,
        per_page: 10
      },
      intervalId: null,
      status: {
        initialLoading: false,
        loadingMore: false,
        markingImportantAsRead: false,
        loadError: false
      },
      ui: {
        drawerVisible: false,
        dialogVisible: false,
        importantDialogVisible: false,
        dialogFullscreen: false,
        currentTab: 'all'
      }
    },
  }),

  async mounted() {
    this.refetchNotifications(); // Initial fetch
    this.startPolling();
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
  },
  beforeUnmount() {
    this.stopPolling();
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
  },

  methods: {
    handleVisibilityChange() {
        if (document.visibilityState === 'visible') {
            this.refetchNotifications(); // Fetch immediately on becoming visible
            this.startPolling();
        } else {
            this.stopPolling();
        }
    },
    startPolling() {
        if (this.notifications.intervalId) return; // Prevent multiple intervals
        this.notifications.intervalId = setInterval(this.refetchNotifications, 60000);
    },
    stopPolling() {
        clearInterval(this.notifications.intervalId);
        this.notifications.intervalId = null;
    },
    async markAsReadImportantNotifications() {
      try {
        this.notifications.status.markingImportantAsRead = true;
        await Promise.all(this.notifications.importantItems.map(async notification => {
          await this.readNotification(notification)
        }))
      } catch (error) {
        console.error(error);
        this.showSnack(handleRequestError(error))
      } finally {
        this.notifications.status.markingImportantAsRead = false;
        this.notifications.ui.importantDialogVisible = false;
      }
    },
    toggleNotificationsDialog() {
      // Toggle the notifications dialog
      this.notifications.ui.dialogVisible = !this.notifications.ui.dialogVisible;

      // Close the settings dialog if the notifications dialog is open
      if (this.notifications.ui.dialogVisible) {
        this.settingsDrawer = false;
        this.notifications.ui.drawerVisible = false;

        // Load notifications if not already loaded
        if (!this.notifications.items) {
          this.loadNotifications({ page: 1 });
        }
      }
    },
    toggleNotificationsDrawer() {
      // Toggle the notifications drawer
      this.notifications.ui.drawerVisible = !this.notifications.ui.drawerVisible;

      // Close the settings drawer if the notifications drawer is open
      if (this.notifications.ui.drawerVisible) {
        this.settingsDrawer = false;

        // Load notifications if not already loaded
        if (!this.notifications.items) {
          this.loadNotifications({ page: 1 });
        }
      }
    },
    async loadImportantNotifications() {
      try {
        if (this.notifications.ui.importantDialogVisible) return;

        // Construct query parameters
        const response = await axios.get(`/admin/api/notifications?is_urgent=true&status=unread&per_page=30`);

        if (response?.data?.items?.length) {
          this.notifications.importantItems = response.data.items;
          this.notifications.ui.importantDialogVisible = true;
          this.notifications.status.loadError = false;
        }

        return response
      } catch (error) {
        const errorMessage = error?.response?.data?.message || error.message || "Failed to load notifications";
        this.showSnack(errorMessage);
        this.notifications.status.loadError = true;
      }
    },
    async loadNotifications(options) {
      // Prevent concurrent loading or invalid state
      if (this.notifications.status.loadingMore || this.notifications.status.initialLoading) return;

      try {
        // Set appropriate loading state
        if (options?.page === 1) {
          this.notifications.status.initialLoading = true;
          this.notifications.pagination = {
            page: 1,
            per_page: 10,
          };
        } else {
          this.notifications.status.loadingMore = true;
        }

        const nextOptions = { ...this.notifications.pagination, ...options }

        if (this.notifications.ui.currentTab !== 'all') {
          nextOptions.status = this.notifications.ui.currentTab;
        }

        // Construct query parameters
        const queryParams = new URLSearchParams(nextOptions);
        const response = await axios.get(`/admin/api/notifications?${queryParams.toString()}`);

        if (!response?.data) return

        if (options?.page === 1) {
          this.notifications.items = [];
          this.notifications.hasMore = false;
        }

        // Destructure response data
        const { items: nextNotifications = [], total, hasMore, unreadCount = 0, hasUnreadUrgentNotifications = false } = response?.data || {};

        this.notifications.unreadCount = unreadCount
        if (hasUnreadUrgentNotifications) {
          this.loadnotifications.importantItems()
        }

        // Update state
        this.notifications.items = [...(this.notifications.items || []), ...nextNotifications];
        if (this.notifications.ui.currentTab === 'all') {
          this.notifications.total = total || 0;
        }
        this.notifications.hasMore = Boolean(hasMore);

        // Increment page if more notifications are available
        if (this.notifications.hasMore) {
          this.notifications.pagination = {
            ...this.notifications.pagination,
            page: (this.notifications.pagination.page || 1) + 1,
          };
        }

        this.notifications.status.loadError = false;
      } catch (error) {
        console.error(error)
        const errorMessage = error?.response?.data?.message || error.message || "Failed to load notifications";
        this.showSnack(errorMessage);
        this.notifications.status.loadError = true;
      } finally {
        // Reset loading states
        this.notifications.status.initialLoading = false;
        this.notifications.status.loadingMore = false;
      }
    },
    async readNotification(nextNotification) {
      // Validate the notification object and its status
      if (!nextNotification?.id || nextNotification?.read_status) return;

      // Find the matching important notification
      const matchingImportantNotification = this.notifications.importantItems?.find(
        notification => notification.id === nextNotification.id
      );
      // Find the matching notification
      const matchingNotification = this.notifications.items?.find(
        notification => notification.id === nextNotification.id
      );

      // Update the read status if the notification is found
      if (matchingImportantNotification) matchingImportantNotification.read_status = true;
      if (matchingNotification) matchingNotification.read_status = true;

      let notificationsCountCopy = this.notifications.unreadCount
      if (matchingNotification || matchingImportantNotification) {
        this.decrementNotificationsCount()
      }

      try {
        const notificationId = nextNotification.id
        await axios.post(`/admin/api/notifications/${notificationId}/read`)
      } catch (error) {
        console.error(error)
        this.showSnack(handleRequestError(error))

        // Revert the read status if the request failed
        if (matchingImportantNotification) matchingImportantNotification.read_status = false;
        if (matchingNotification) matchingNotification.read_status = false;

        this.notifications.unreadCount = notificationsCountCopy
      }
    },
    async refetchNotifications() {
      this.loadNotifications({ page: 1 });
    },
    decrementNotificationsCount() {
      if (this.notifications.unreadCount > 0) {
        this.notifications.unreadCount -= 1;
      }
    }
  },
  watch: {
    'notifications.ui.currentTab'() {
      this.loadNotifications({ page: 1 });
    }
  },
};
