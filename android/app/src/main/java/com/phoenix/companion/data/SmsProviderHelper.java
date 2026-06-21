package com.phoenix.companion.data;

import android.Manifest;
import android.content.ContentResolver;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import androidx.core.content.ContextCompat;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Helper class for querying and exporting SMS message logs from the SMS Content Provider.
 * Implements cursor pagination and structured JSON formatting suitable for streaming.
 */
public class SmsProviderHelper {

    private static final Uri SMS_URI = Uri.parse("content://sms");

    /**
     * Checks if the READ_SMS permission is granted.
     *
     * @param context the application context
     * @return true if permission is granted, false otherwise
     */
    public boolean hasSmsPermission(Context context) {
        return ContextCompat.checkSelfPermission(context, Manifest.permission.READ_SMS) 
                == PackageManager.PERMISSION_GRANTED;
    }

    /**
     * Queries and exports a paginated list of SMS messages as a structured JSON array.
     *
     * @param context the application context
     * @param limit   the maximum number of records to fetch
     * @param offset  the cursor offset for pagination
     * @return a structured JSON string containing SMS message list and pagination metadata
     * @throws SecurityException if READ_SMS permission is not granted
     * @throws JSONException     if JSON formatting fails
     */
    public String getSmsAsJson(Context context, int limit, int offset) 
            throws SecurityException, JSONException {
        
        if (!hasSmsPermission(context)) {
            throw new SecurityException("Permission READ_SMS not granted");
        }

        ContentResolver resolver = context.getContentResolver();
        JSONArray smsArray = new JSONArray();

        // Projection of target columns
        String[] projection = {
                "_id",
                "address",
                "body",
                "date",
                "type"
        };

        Cursor cursor = null;
        boolean isInMemoryPaginated = false;

        try {
            // Android 11+ (API 30) query pagination using Bundle arguments
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    Bundle queryArgs = new Bundle();
                    queryArgs.putInt(ContentResolver.QUERY_ARG_LIMIT, limit);
                    queryArgs.putInt(ContentResolver.QUERY_ARG_OFFSET, offset);
                    queryArgs.putStringArray(ContentResolver.QUERY_ARG_SORT_COLUMNS, new String[]{"_id"});
                    queryArgs.putInt(ContentResolver.QUERY_ARG_SORT_DIRECTION, ContentResolver.QUERY_SORT_DIRECTION_DESCENDING);

                    cursor = resolver.query(
                            SMS_URI,
                            projection,
                            queryArgs,
                            null
                    );
                }
            } catch (Exception e) {
                // Fallback to traditional or in-memory pagination if API 30 query args fail
                cursor = null;
            }

            if (cursor == null) {
                // Fallback query formatting using traditional sortOrder without LIMIT/OFFSET
                String sortOrder = "_id DESC";
                cursor = resolver.query(
                        SMS_URI,
                        projection,
                        null,
                        null,
                        sortOrder
                );
                isInMemoryPaginated = true;
            }

            if (cursor != null) {
                boolean hasRow = isInMemoryPaginated ? cursor.moveToPosition(offset) : cursor.moveToFirst();
                if (hasRow) {
                    int idIndex = cursor.getColumnIndexOrThrow("_id");
                    int addressIndex = cursor.getColumnIndexOrThrow("address");
                    int bodyIndex = cursor.getColumnIndexOrThrow("body");
                    int dateIndex = cursor.getColumnIndexOrThrow("date");
                    int typeIndex = cursor.getColumnIndexOrThrow("type");

                    int count = 0;
                    do {
                        JSONObject smsObj = new JSONObject();
                        smsObj.put("id", cursor.getString(idIndex));
                        
                        String address = cursor.getString(addressIndex);
                        smsObj.put("address", address != null ? address : "Unknown");
                        
                        String body = cursor.getString(bodyIndex);
                        smsObj.put("body", body != null ? body : "");
                        
                        smsObj.put("timestamp", cursor.getLong(dateIndex));
                        
                        int typeCode = cursor.getInt(typeIndex);
                        smsObj.put("type", getSmsTypeString(typeCode));

                        smsArray.put(smsObj);
                        count++;
                    } while ((!isInMemoryPaginated || count < limit) && cursor.moveToNext());
                }
            }
        } finally {
            if (cursor != null) {
                cursor.close();
            }
        }

        // Compile paginated response
        JSONObject response = new JSONObject();
        response.put("status", "SUCCESS");
        
        JSONObject dataObj = new JSONObject();
        dataObj.put("sms", smsArray);
        dataObj.put("has_more", smsArray.length() == limit);
        
        response.put("data", dataObj);

        return response.toString();
    }

    /**
     * Map SMS type codes to standard human-readable descriptions.
     */
    private String getSmsTypeString(int typeCode) {
        switch (typeCode) {
            case 1: // MESSAGE_TYPE_INBOX
                return "INBOX";
            case 2: // MESSAGE_TYPE_SENT
                return "SENT";
            case 3: // MESSAGE_TYPE_DRAFT
                return "DRAFT";
            case 4: // MESSAGE_TYPE_OUTBOX
                return "OUTBOX";
            case 5: // MESSAGE_TYPE_FAILED
                return "FAILED";
            case 6: // MESSAGE_TYPE_QUEUED
                return "QUEUED";
            default:
                return "UNKNOWN";
        }
    }
}
