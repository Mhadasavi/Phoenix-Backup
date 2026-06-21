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
import android.provider.ContactsContract;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;

/**
 * Local unit tests for ContactsProviderHelper utilizing Mockito to mock Android content resolver channels.
 */
public class ContactsProviderHelperTest {

    private ContactsProviderHelper helper;
    private Context mockContext;
    private ContentResolver mockResolver;

    @Before
    public void setUp() {
        helper = new ContactsProviderHelper();
        mockContext = mock(Context.class);
        mockResolver = mock(ContentResolver.class);
        when(mockContext.getContentResolver()).thenReturn(mockResolver);
    }

    @Test
    public void testHasContactPermission_Granted() {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_CONTACTS), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_GRANTED);

        assertTrue(helper.hasContactPermission(mockContext));
    }

    @Test
    public void testHasContactPermission_Denied() {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_CONTACTS), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_DENIED);

        assertFalse(helper.hasContactPermission(mockContext));
    }

    @Test
    public void testGetContactsAsJson_PermissionDenied_ThrowsSecurityException() {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_CONTACTS), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_DENIED);

        try {
            helper.getContactsAsJson(mockContext, 10, 0);
            fail("Should have thrown SecurityException due to missing permission");
        } catch (SecurityException e) {
            assertEquals("Permission READ_CONTACTS not granted", e.getMessage());
        } catch (Exception e) {
            fail("Expected SecurityException, but caught: " + e.getClass().getSimpleName());
        }
    }

    @Test
    public void testGetContactsAsJson_EmptyCursor_ReturnsSuccessWithEmptyList() throws Exception {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_CONTACTS), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_GRANTED);

        // Mock empty cursor response
        Cursor mockCursor = mock(Cursor.class);
        when(mockCursor.moveToFirst()).thenReturn(false);
        
        when(mockResolver.query(any(), any(), any(), any(), any()))
                .thenReturn(mockCursor);
        when(mockResolver.query(any(), any(), any(Bundle.class), any()))
                .thenReturn(mockCursor);

        String jsonResult = helper.getContactsAsJson(mockContext, 10, 0);
        JSONObject resultObj = new JSONObject(jsonResult);

        assertEquals("SUCCESS", resultObj.getString("status"));
        JSONObject dataObj = resultObj.getJSONObject("data");
        JSONArray contactsArray = dataObj.getJSONArray("contacts");
        assertEquals(0, contactsArray.length());
        assertFalse(dataObj.getBoolean("has_more"));
    }

    @Test
    public void testGetContactsAsJson_WithRecords_ReturnsPopulatedJson() throws Exception {
        when(mockContext.checkPermission(eq(Manifest.permission.READ_CONTACTS), anyInt(), anyInt()))
                .thenReturn(PackageManager.PERMISSION_GRANTED);

        // Mock Contacts Query Cursor
        Cursor mockCursor = mock(Cursor.class);
        when(mockCursor.moveToFirst()).thenReturn(true);
        when(mockCursor.moveToPosition(anyInt())).thenReturn(true);
        when(mockCursor.moveToNext()).thenReturn(false); // Only 1 contact

        int colIdIndex = 0;
        int colNameIndex = 1;
        when(mockCursor.getColumnIndexOrThrow(ContactsContract.Contacts._ID)).thenReturn(colIdIndex);
        when(mockCursor.getColumnIndexOrThrow(ContactsContract.Contacts.DISPLAY_NAME_PRIMARY)).thenReturn(colNameIndex);

        when(mockCursor.getString(colIdIndex)).thenReturn("123");
        when(mockCursor.getString(colNameIndex)).thenReturn("Jane Doe");

        // Mock Phone Query Cursor
        Cursor phoneCursor = mock(Cursor.class);
        when(phoneCursor.moveToFirst()).thenReturn(true);
        when(phoneCursor.moveToNext()).thenReturn(false);
        when(phoneCursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.CONTACT_ID)).thenReturn(0);
        when(phoneCursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.NUMBER)).thenReturn(1);
        when(phoneCursor.getString(0)).thenReturn("123");
        when(phoneCursor.getString(1)).thenReturn("+15550199");

        // Mock Email Query Cursor
        Cursor emailCursor = mock(Cursor.class);
        when(emailCursor.moveToFirst()).thenReturn(true);
        when(emailCursor.moveToNext()).thenReturn(false);
        when(emailCursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Email.CONTACT_ID)).thenReturn(0);
        when(emailCursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Email.ADDRESS)).thenReturn(1);
        when(emailCursor.getString(0)).thenReturn("123");
        when(emailCursor.getString(1)).thenReturn("jane.doe@example.com");

        // Sequential stubbing to handle null Uri stubs in JVM unit tests:
        // 1st call: Contacts query -> mockCursor
        // 2nd call: Phone query -> phoneCursor
        // 3rd call: Email query -> emailCursor
        when(mockResolver.query(any(), any(), any(), any(), any()))
                .thenReturn(mockCursor)
                .thenReturn(phoneCursor)
                .thenReturn(emailCursor);

        when(mockResolver.query(any(), any(), any(Bundle.class), any()))
                .thenReturn(mockCursor)
                .thenReturn(phoneCursor)
                .thenReturn(emailCursor);

        String jsonResult = helper.getContactsAsJson(mockContext, 1, 0);
        JSONObject resultObj = new JSONObject(jsonResult);

        assertEquals("SUCCESS", resultObj.getString("status"));
        JSONObject dataObj = resultObj.getJSONObject("data");
        JSONArray contactsArray = dataObj.getJSONArray("contacts");
        assertEquals(1, contactsArray.length());

        JSONObject contact = contactsArray.getJSONObject(0);
        assertEquals("Jane Doe", contact.getString("name"));
        assertEquals("+15550199", contact.getJSONArray("phones").getString(0));
        assertEquals("jane.doe@example.com", contact.getJSONArray("emails").getString(0));
        assertTrue(dataObj.getBoolean("has_more")); // returns true because contacts.length == limit (1)
    }
}
