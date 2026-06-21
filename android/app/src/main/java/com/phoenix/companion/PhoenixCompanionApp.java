package com.phoenix.companion;

import android.app.Application;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.os.Build;

/**
 * Main application class. Initializes persistent notification channels
 * for foreground synchronization services on API 26+.
 */
public class PhoenixCompanionApp extends Application {

    public static final String CHANNEL_ID = "phoenix_backup_sync_channel";

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            CharSequence name = "Phoenix Sync Service";
            String description = "Background synchronization log transport channel";
            int importance = NotificationManager.IMPORTANCE_LOW; // low importance to prevent alert sounds on startup

            NotificationChannel channel = new NotificationChannel(CHANNEL_ID, name, importance);
            channel.setDescription(description);

            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }
}
