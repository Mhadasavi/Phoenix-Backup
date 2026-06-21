package com.phoenix.companion.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import android.Manifest;
import android.content.ContentResolver;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.os.Bundle;
import android.provider.CallLog;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;

/**
 * Local unit tests for CallLogProviderHelper utilizing Mockito to assert provider queries.
 */
public class CallLogProviderHelperTest {

    private CallLogProviderHelper helper;
    private Context mockContext;
    private ContentResolver mockResolver;

    @Before
    public void setUp() {
        helper = new CallLogProviderHelper();
        mockContext = mock(Context.class);
        mockResolver = mock(ContentResolver.class);
        when(mockContext.getContentResolver()).thenReturn(mockResolver);
    }

    @Test
    public void testHasCallLogPermission_Granted() {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_CALL_LOG), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_GRANTED);

        assertTrue(helper.hasCallLogPermission(mockContext));
    }

    @Test
    public void testHasCallLogPermission_Denied() {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_CALL_LOG), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_DENIED);

        assertFalse(helper.hasCallLogPermission(mockContext));
    }

    @Test
    public void testGetCallLogsAsJson_PermissionDenied_ThrowsSecurityException() {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_CALL_LOG), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_DENIED);

        try {
            helper.getCallLogsAsJson(mockContext, 10, 0);
            fail("Should have thrown SecurityException due to missing permission");
        } catch (SecurityException e) {
            assertEquals("Permission READ_CALL_LOG not granted", e.getMessage());
        } catch (Exception e) {
            fail("Expected SecurityException, but caught: " + e.getClass().getSimpleName());
        }
    }

    @Test
    public void testGetCallLogsAsJson_EmptyCursor_ReturnsSuccessWithEmptyList() throws Exception {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_CALL_LOG), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_GRANTED);

        Cursor mockCursor = mock(Cursor.class);
        when(mockCursor.moveToFirst()).thenReturn(false);

        when(mockResolver.query(eq(CallLog.Calls.CONTENT_URI), any(), any(Bundle.class), any()))
                .thenReturn(mockCursor);
        when(mockResolver.query(eq(CallLog.Calls.CONTENT_URI), any(), any(), any(), any()))
                .thenReturn(mockCursor);

        String jsonResult = helper.getCallLogsAsJson(mockContext, 10, 0);
        JSONObject resultObj = new JSONObject(jsonResult);

        assertEquals("SUCCESS", resultObj.getString("status"));
        JSONObject dataObj = resultObj.getJSONObject("data");
        JSONArray logsArray = dataObj.getJSONArray("call_logs");
        assertEquals(0, logsArray.length());
        assertFalse(dataObj.getBoolean("has_more"));
    }

    @Test
    public void testGetCallLogsAsJson_WithRecords_ReturnsPopulatedJson() throws Exception {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_CALL_LOG), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_GRANTED);

        Cursor mockCursor = mock(Cursor.class);
        when(mockCursor.moveToFirst()).thenReturn(true);
        when(mockCursor.moveToPosition(anyInt())).thenReturn(true);
        when(mockCursor.moveToNext()).thenReturn(false); // Only 1 record

        // Projection mapping indices
        int idIdx = 0;
        int numIdx = 1;
        int dateIdx = 2;
        int durIdx = 3;
        int typeIdx = 4;
        int nameIdx = 5;

        when(mockCursor.getColumnIndexOrThrow(CallLog.Calls._ID)).thenReturn(idIdx);
        when(mockCursor.getColumnIndexOrThrow(CallLog.Calls.NUMBER)).thenReturn(numIdx);
        when(mockCursor.getColumnIndexOrThrow(CallLog.Calls.DATE)).thenReturn(dateIdx);
        when(mockCursor.getColumnIndexOrThrow(CallLog.Calls.DURATION)).thenReturn(durIdx);
        when(mockCursor.getColumnIndexOrThrow(CallLog.Calls.TYPE)).thenReturn(typeIdx);
        when(mockCursor.getColumnIndexOrThrow(CallLog.Calls.CACHED_NAME)).thenReturn(nameIdx);

        when(mockCursor.getString(idIdx)).thenReturn("1");
        when(mockCursor.getString(numIdx)).thenReturn("+15550199");
        when(mockCursor.getLong(dateIdx)).thenReturn(1781446700000L);
        when(mockCursor.getLong(durIdx)).thenReturn(120L);
        when(mockCursor.getInt(typeIdx)).thenReturn(CallLog.Calls.INCOMING_TYPE);
        when(mockCursor.getString(nameIdx)).thenReturn("Jane Doe");

        when(mockResolver.query(eq(CallLog.Calls.CONTENT_URI), any(), any(Bundle.class), any()))
                .thenReturn(mockCursor);
        when(mockResolver.query(eq(CallLog.Calls.CONTENT_URI), any(), any(), any(), any()))
                .thenReturn(mockCursor);

        String jsonResult = helper.getCallLogsAsJson(mockContext, 1, 0);
        JSONObject resultObj = new JSONObject(jsonResult);

        assertEquals("SUCCESS", resultObj.getString("status"));
        JSONObject dataObj = resultObj.getJSONObject("data");
        JSONArray logsArray = dataObj.getJSONArray("call_logs");
        assertEquals(1, logsArray.length());

        JSONObject log = logsArray.getJSONObject(0);
        assertEquals("1", log.getString("id"));
        assertEquals("+15550199", log.getString("number"));
        assertEquals(1781446700000L, log.getLong("timestamp"));
        assertEquals(120L, log.getLong("duration"));
        assertEquals("INCOMING", log.getString("type"));
        assertEquals("Jane Doe", log.getString("name"));
        assertTrue(dataObj.getBoolean("has_more"));
    }
}
