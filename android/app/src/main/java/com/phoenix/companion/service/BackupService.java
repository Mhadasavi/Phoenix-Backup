package com.phoenix.companion.service;

import android.app.Notification;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.util.Log;

import androidx.core.app.NotificationCompat;

import com.phoenix.companion.PhoenixCompanionApp;
import com.phoenix.companion.data.CallLogProviderHelper;
import com.phoenix.companion.data.ContactsProviderHelper;
import com.phoenix.companion.data.SmsProviderHelper;
import com.phoenix.companion.network.SecureTransportServer;

import org.json.JSONObject;

/**
 * Foreground Service coordinating background backups. Locks WakeLock,
 * initializes secure transport server, and dispatches JSON commands.
 */
public class BackupService extends Service implements SecureTransportServer.CommandHandler {

    private static final String TAG = "PhoenixBackupService";
    private static final int PORT = 58988;

    private PowerManager.WakeLock wakeLock;
    private SecureTransportServer transportServer;

    private ContactsProviderHelper contactsHelper;
    private SmsProviderHelper smsHelper;
    private CallLogProviderHelper callLogHelper;

    @Override
    public void onCreate() {
        super.onCreate();
        contactsHelper = new ContactsProviderHelper();
        smsHelper = new SmsProviderHelper();
        callLogHelper = new CallLogProviderHelper();
        Log.i(TAG, "Service created.");
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.i(TAG, "Service starting...");
        
        // 1. Resolve Auth Token from Intent
        String token = "sprint2_integrated_salt"; // fallback/default test token
        if (intent != null && intent.hasExtra("token")) {
            token = intent.getStringExtra("token");
        }

        // 2. Start Foreground Notification (API 34 DataSync Compliant)
        Notification notification = new NotificationCompat.Builder(this, PhoenixCompanionApp.CHANNEL_ID)
                .setContentTitle("Phoenix Backup Agent Active")
                .setContentText("Connected locally via ADB loopback...")
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .build();

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        } else {
            startForeground(1, notification);
        }

        // 3. Acquire partial CPU WakeLock to prevent device sleep mid-transfer
        PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
        if (pm != null) {
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "PhoenixCompanion::WakeLock");
            wakeLock.acquire(30 * 60 * 1000L); // 30 minutes execution limit
            Log.d(TAG, "CPU WakeLock acquired.");
        }

        // 4. Initialize Secure Transport Server if not already active
        if (transportServer == null) {
            transportServer = new SecureTransportServer(PORT, token, this);
            transportServer.start();
        } else {
            Log.i(TAG, "SecureTransportServer already active, skipping initialization.");
        }

        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        Log.i(TAG, "Service destroying...");
        
        if (transportServer != null) {
            transportServer.stop();
            transportServer = null;
        }

        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
            Log.d(TAG, "CPU WakeLock released.");
        }

        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null; // Headless service does not support IPC binding, executes via startup intents
    }

    /**
     * Maps incoming validated JSON requests to the corresponding extraction helpers.
     */
    @Override
    public String handleCommand(String command, JSONObject requestJson) {
        try {
            int limit = requestJson.optInt("limit", 100);
            int offset = requestJson.optInt("offset", 0);

            switch (command) {
                case "GET_SYSTEM_INFO":
                    JSONObject sysInfo = new JSONObject();
                    sysInfo.put("manufacturer", Build.MANUFACTURER);
                    sysInfo.put("model", Build.MODEL);
                    sysInfo.put("api_level", Build.VERSION.SDK_INT);
                    sysInfo.put("android_version", Build.VERSION.RELEASE);
                    
                    JSONObject response = new JSONObject();
                    response.put("status", "SUCCESS");
                    response.put("data", sysInfo);
                    return response.toString();

                case "GET_CONTACTS":
                    try {
                        return contactsHelper.getContactsAsJson(this, limit, offset);
                    } catch (SecurityException e) {
                        return buildPermissionDeniedResponse("READ_CONTACTS");
                    }

                case "GET_SMS":
                    try {
                        return smsHelper.getSmsAsJson(this, limit, offset);
                    } catch (SecurityException e) {
                        return buildPermissionDeniedResponse("READ_SMS");
                    }

                case "GET_CALL_LOGS":
                    try {
                        return callLogHelper.getCallLogsAsJson(this, limit, offset);
                    } catch (SecurityException e) {
                        return buildPermissionDeniedResponse("READ_CALL_LOG");
                    }

                default:
                    JSONObject err = new JSONObject();
                    err.put("status", "ERROR");
                    err.put("message", "Unknown command: " + command);
                    return err.toString();
            }
        } catch (Exception e) {
            try {
                JSONObject err = new JSONObject();
                err.put("status", "ERROR");
                err.put("message", "Exception running command: " + e.getMessage());
                return err.toString();
            } catch (Exception ignored) {
                return "{\"status\":\"ERROR\",\"message\":\"Fatal error in dispatcher\"}";
            }
        }
    }

    private String buildPermissionDeniedResponse(String permissionName) {
        return "{\"status\":\"PERMISSION_DENIED\",\"message\":\"Permission " + permissionName + " not granted\"}";
    }
}
