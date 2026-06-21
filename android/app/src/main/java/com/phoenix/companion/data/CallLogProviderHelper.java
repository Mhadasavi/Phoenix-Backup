package com.phoenix.companion.data;

import android.Manifest;
import android.content.ContentResolver;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.os.Build;
import android.os.Bundle;
import android.provider.CallLog;
import androidx.core.content.ContextCompat;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Helper class for querying and exporting call history log entries from the CallLog Content Provider.
 * Implements cursor pagination and structured JSON formatting suitable for streaming.
 */
public class CallLogProviderHelper {

    /**
     * Checks if the READ_CALL_LOG permission is granted.
     *
     * @param context the application context
     * @return true if permission is granted, false otherwise
     */
    public boolean hasCallLogPermission(Context context) {
        return ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CALL_LOG) 
                == PackageManager.PERMISSION_GRANTED;
    }

    /**
     * Queries and exports a paginated list of call logs as a structured JSON array.
     *
     * @param context the application context
     * @param limit   the maximum number of records to fetch
     * @param offset  the cursor offset for pagination
     * @return a structured JSON string containing call log lists and pagination metadata
     * @throws SecurityException if READ_CALL_LOG permission is not granted
     * @throws JSONException     if JSON formatting fails
     */
    public String getCallLogsAsJson(Context context, int limit, int offset) 
            throws SecurityException, JSONException {
        
        if (!hasCallLogPermission(context)) {
            throw new SecurityException("Permission READ_CALL_LOG not granted");
        }

        ContentResolver resolver = context.getContentResolver();
        JSONArray callLogsArray = new JSONArray();

        // Projection of target columns
        String[] projection = {
                CallLog.Calls._ID,
                CallLog.Calls.NUMBER,
                CallLog.Calls.DATE,
                CallLog.Calls.DURATION,
                CallLog.Calls.TYPE,
                CallLog.Calls.CACHED_NAME
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
                    queryArgs.putStringArray(ContentResolver.QUERY_ARG_SORT_COLUMNS, new String[]{CallLog.Calls._ID});
                    queryArgs.putInt(ContentResolver.QUERY_ARG_SORT_DIRECTION, ContentResolver.QUERY_SORT_DIRECTION_DESCENDING);

                    cursor = resolver.query(
                            CallLog.Calls.CONTENT_URI,
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
                String sortOrder = CallLog.Calls._ID + " DESC";
                cursor = resolver.query(
                        CallLog.Calls.CONTENT_URI,
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
                    int idIndex = cursor.getColumnIndexOrThrow(CallLog.Calls._ID);
                    int numberIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.NUMBER);
                    int dateIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.DATE);
                    int durationIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.DURATION);
                    int typeIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.TYPE);
                    int nameIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.CACHED_NAME);

                    int count = 0;
                    do {
                        JSONObject callLogObj = new JSONObject();
                        callLogObj.put("id", cursor.getString(idIndex));
                        
                        String number = cursor.getString(numberIndex);
                        callLogObj.put("number", number != null ? number : "Unknown");
                        
                        callLogObj.put("timestamp", cursor.getLong(dateIndex));
                        callLogObj.put("duration", cursor.getLong(durationIndex));
                        
                        int typeCode = cursor.getInt(typeIndex);
                        callLogObj.put("type", getCallTypeString(typeCode));
                        
                        String name = cursor.getString(nameIndex);
                        callLogObj.put("name", name != null ? name : "");

                        callLogsArray.put(callLogObj);
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
        dataObj.put("call_logs", callLogsArray);
        dataObj.put("has_more", callLogsArray.length() == limit);
        
        response.put("data", dataObj);

        return response.toString();
    }

    /**
     * Map call log code to standard human-readable string descriptions.
     */
    private String getCallTypeString(int typeCode) {
        switch (typeCode) {
            case CallLog.Calls.INCOMING_TYPE:
                return "INCOMING";
            case CallLog.Calls.OUTGOING_TYPE:
                return "OUTGOING";
            case CallLog.Calls.MISSED_TYPE:
                return "MISSED";
            case CallLog.Calls.VOICEMAIL_TYPE:
                return "VOICEMAIL";
            case CallLog.Calls.REJECTED_TYPE:
                return "REJECTED";
            case CallLog.Calls.BLOCKED_TYPE:
                return "BLOCKED";
            case CallLog.Calls.ANSWERED_EXTERNALLY_TYPE:
                return "ANSWERED_EXTERNALLY";
            default:
                return "UNKNOWN";
        }
    }
}
