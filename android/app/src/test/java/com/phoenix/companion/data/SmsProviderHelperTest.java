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
import android.net.Uri;
import android.os.Bundle;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;

/**
 * Local unit tests for SmsProviderHelper utilizing Mockito to assert provider queries.
 */
public class SmsProviderHelperTest {

    private SmsProviderHelper helper;
    private Context mockContext;
    private ContentResolver mockResolver;
    private static final Uri SMS_URI = Uri.parse("content://sms");

    @Before
    public void setUp() {
        helper = new SmsProviderHelper();
        mockContext = mock(Context.class);
        mockResolver = mock(ContentResolver.class);
        when(mockContext.getContentResolver()).thenReturn(mockResolver);
    }

    @Test
    public void testHasSmsPermission_Granted() {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_SMS), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_GRANTED);

        assertTrue(helper.hasSmsPermission(mockContext));
    }

    @Test
    public void testHasSmsPermission_Denied() {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_SMS), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_DENIED);

        assertFalse(helper.hasSmsPermission(mockContext));
    }

    @Test
    public void testGetSmsAsJson_PermissionDenied_ThrowsSecurityException() {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_SMS), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_DENIED);

        try {
            helper.getSmsAsJson(mockContext, 10, 0);
            fail("Should have thrown SecurityException due to missing permission");
        } catch (SecurityException e) {
            assertEquals("Permission READ_SMS not granted", e.getMessage());
        } catch (Exception e) {
            fail("Expected SecurityException, but caught: " + e.getClass().getSimpleName());
        }
    }

    @Test
    public void testGetSmsAsJson_EmptyCursor_ReturnsSuccessWithEmptyList() throws Exception {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_SMS), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_GRANTED);

        Cursor mockCursor = mock(Cursor.class);
        when(mockCursor.moveToFirst()).thenReturn(false);

        // Mock resolver query for both API 30 Bundle query and older query
        when(mockResolver.query(eq(SMS_URI), any(), any(Bundle.class), any()))
                .thenReturn(mockCursor);
        when(mockResolver.query(eq(SMS_URI), any(), any(), any(), any()))
                .thenReturn(mockCursor);

        String jsonResult = helper.getSmsAsJson(mockContext, 10, 0);
        JSONObject resultObj = new JSONObject(jsonResult);

        assertEquals("SUCCESS", resultObj.getString("status"));
        JSONObject dataObj = resultObj.getJSONObject("data");
        JSONArray smsArray = dataObj.getJSONArray("sms");
        assertEquals(0, smsArray.length());
        assertFalse(dataObj.getBoolean("has_more"));
    }

    @Test
    public void testGetSmsAsJson_WithRecords_ReturnsPopulatedJson() throws Exception {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_SMS), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_GRANTED);

        Cursor mockCursor = mock(Cursor.class);
        when(mockCursor.moveToFirst()).thenReturn(true);
        when(mockCursor.moveToPosition(anyInt())).thenReturn(true);
        when(mockCursor.moveToNext()).thenReturn(false); // Only 1 record

        // Projection mapping indices
        int idIdx = 0;
        int addrIdx = 1;
        int bodyIdx = 2;
        int dateIdx = 3;
        int typeIdx = 4;

        when(mockCursor.getColumnIndexOrThrow("_id")).thenReturn(idIdx);
        when(mockCursor.getColumnIndexOrThrow("address")).thenReturn(addrIdx);
        when(mockCursor.getColumnIndexOrThrow("body")).thenReturn(bodyIdx);
        when(mockCursor.getColumnIndexOrThrow("date")).thenReturn(dateIdx);
        when(mockCursor.getColumnIndexOrThrow("type")).thenReturn(typeIdx);

        when(mockCursor.getString(idIdx)).thenReturn("1001");
        when(mockCursor.getString(addrIdx)).thenReturn("+15550199");
        when(mockCursor.getString(bodyIdx)).thenReturn("Hello from Phoenix Companion!");
        when(mockCursor.getLong(dateIdx)).thenReturn(1781446700000L);
        when(mockCursor.getInt(typeIdx)).thenReturn(1); // MESSAGE_TYPE_INBOX

        when(mockResolver.query(eq(SMS_URI), any(), any(Bundle.class), any()))
                .thenReturn(mockCursor);
        when(mockResolver.query(eq(SMS_URI), any(), any(), any(), any()))
                .thenReturn(mockCursor);

        String jsonResult = helper.getSmsAsJson(mockContext, 1, 0);
        JSONObject resultObj = new JSONObject(jsonResult);

        assertEquals("SUCCESS", resultObj.getString("status"));
        JSONObject dataObj = resultObj.getJSONObject("data");
        JSONArray smsArray = dataObj.getJSONArray("sms");
        assertEquals(1, smsArray.length());

        JSONObject sms = smsArray.getJSONObject(0);
        assertEquals("1001", sms.getString("id"));
        assertEquals("+15550199", sms.getString("address"));
        assertEquals("Hello from Phoenix Companion!", sms.getString("body"));
        assertEquals(1781446700000L, sms.getLong("timestamp"));
        assertEquals("INBOX", sms.getString("type"));
        assertTrue(dataObj.getBoolean("has_more")); // returns true because sms.length == limit (1)
    }
}
