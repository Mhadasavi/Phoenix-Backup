package com.phoenix.companion.data;

import android.Manifest;
import android.content.ContentResolver;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.os.Build;
import android.os.Bundle;
import android.provider.ContactsContract;
import androidx.core.content.ContextCompat;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/**
 * Helper class for querying and exporting contacts using the Android ContactsContract Content Provider.
 * Implements cursor pagination and structured JSON formatting suitable for streaming.
 */
public class ContactsProviderHelper {

    /**
     * Checks if the READ_CONTACTS permission is granted.
     *
     * @param context the application context
     * @return true if permission is granted, false otherwise
     */
    public boolean hasContactPermission(Context context) {
        return ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CONTACTS) 
                == PackageManager.PERMISSION_GRANTED;
    }

    /**
     * Queries and exports a paginated list of contacts as a structured JSON array.
     *
     * @param context the application context
     * @param limit   the maximum number of contacts to fetch
     * @param offset  the cursor offset for pagination
     * @return a structured JSON string containing contacts list and pagination metadata
     * @throws SecurityException if READ_CONTACTS permission is not granted
     * @throws JSONException     if JSON formatting fails
     */
    private static class ContactTemp {
        String id;
        String name;
        List<String> phones = new ArrayList<>();
        List<String> emails = new ArrayList<>();

        ContactTemp(String id, String name) {
            this.id = id;
            this.name = name;
        }
    }

    public String getContactsAsJson(Context context, int limit, int offset) 
            throws SecurityException, JSONException {
        
        if (!hasContactPermission(context)) {
            throw new SecurityException("Permission READ_CONTACTS not granted");
        }

        ContentResolver resolver = context.getContentResolver();
        JSONArray contactsArray = new JSONArray();

        // 1. Projection of columns from ContactsContract.Contacts
        String[] projection = {
                ContactsContract.Contacts._ID,
                ContactsContract.Contacts.DISPLAY_NAME_PRIMARY
        };

        Cursor cursor = null;
        List<ContactTemp> contactsList = new ArrayList<>();
        int count = 0;
        boolean hasMore = false;
        boolean isInMemoryPaginated = false;

        try {
            // Android 11+ (API 30) query pagination using Bundle arguments
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    Bundle queryArgs = new Bundle();
                    queryArgs.putInt(ContentResolver.QUERY_ARG_LIMIT, limit);
                    queryArgs.putInt(ContentResolver.QUERY_ARG_OFFSET, offset);
                    queryArgs.putStringArray(ContentResolver.QUERY_ARG_SORT_COLUMNS, new String[]{ContactsContract.Contacts._ID});
                    queryArgs.putInt(ContentResolver.QUERY_ARG_SORT_DIRECTION, ContentResolver.QUERY_SORT_DIRECTION_ASCENDING);

                    cursor = resolver.query(
                            ContactsContract.Contacts.CONTENT_URI,
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
                // Fallback query formatting for older Android versions or custom OS providers
                cursor = resolver.query(
                        ContactsContract.Contacts.CONTENT_URI,
                        projection,
                        null,
                        null,
                        ContactsContract.Contacts._ID + " ASC"
                );
                isInMemoryPaginated = true;
            }

            if (cursor != null) {
                boolean hasRow = isInMemoryPaginated ? cursor.moveToPosition(offset) : cursor.moveToFirst();
                if (hasRow) {
                    int idIndex = cursor.getColumnIndexOrThrow(ContactsContract.Contacts._ID);
                    int nameIndex = cursor.getColumnIndexOrThrow(ContactsContract.Contacts.DISPLAY_NAME_PRIMARY);

                    do {
                        String contactId = cursor.getString(idIndex);
                        String name = cursor.getString(nameIndex);
                        contactsList.add(new ContactTemp(contactId, name != null ? name : "Unknown"));
                        count++;
                    } while ((!isInMemoryPaginated || count < limit) && cursor.moveToNext());
                }
            }

            if (!contactsList.isEmpty()) {
                bulkFetchPhoneNumbers(resolver, contactsList);
                bulkFetchEmails(resolver, contactsList);
            }

            for (ContactTemp contact : contactsList) {
                JSONObject contactObj = new JSONObject();
                contactObj.put("name", contact.name);
                contactObj.put("phones", new JSONArray(contact.phones));
                contactObj.put("emails", new JSONArray(contact.emails));
                contactsArray.put(contactObj);
            }

            hasMore = contactsList.size() == limit;

        } finally {
            if (cursor != null) {
                cursor.close();
            }
        }

        // 3. Compile paginated response
        JSONObject response = new JSONObject();
        response.put("status", "SUCCESS");
        
        JSONObject dataObj = new JSONObject();
        dataObj.put("contacts", contactsArray);
        dataObj.put("has_more", hasMore);
        
        response.put("data", dataObj);

        return response.toString();
    }

    /**
     * Queries phone numbers associated with a batch of contact IDs.
     */
    private void bulkFetchPhoneNumbers(ContentResolver resolver, List<ContactTemp> contacts) {
        if (contacts.isEmpty()) return;

        StringBuilder selection = new StringBuilder();
        selection.append(ContactsContract.CommonDataKinds.Phone.CONTACT_ID).append(" IN (");
        String[] selectionArgs = new String[contacts.size()];
        for (int i = 0; i < contacts.size(); i++) {
            selection.append("?");
            if (i < contacts.size() - 1) {
                selection.append(",");
            }
            selectionArgs[i] = contacts.get(i).id;
        }
        selection.append(")");

        String[] projection = {
                ContactsContract.CommonDataKinds.Phone.CONTACT_ID,
                ContactsContract.CommonDataKinds.Phone.NUMBER
        };

        try (Cursor cursor = resolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                projection,
                selection.toString(),
                selectionArgs,
                null
        )) {
            if (cursor != null && cursor.moveToFirst()) {
                int idIndex = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.CONTACT_ID);
                int numberIndex = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.NUMBER);
                do {
                    String contactId = cursor.getString(idIndex);
                    String number = cursor.getString(numberIndex);
                    if (number != null && !number.trim().isEmpty()) {
                        for (ContactTemp contact : contacts) {
                            if (contact.id.equals(contactId)) {
                                contact.phones.add(number);
                                break;
                            }
                        }
                    }
                } while (cursor.moveToNext());
            }
        } catch (Exception e) {
            // Gracefully ignore failures for secondary fields
        }
    }

    /**
     * Queries emails associated with a batch of contact IDs.
     */
    private void bulkFetchEmails(ContentResolver resolver, List<ContactTemp> contacts) {
        if (contacts.isEmpty()) return;

        StringBuilder selection = new StringBuilder();
        selection.append(ContactsContract.CommonDataKinds.Email.CONTACT_ID).append(" IN (");
        String[] selectionArgs = new String[contacts.size()];
        for (int i = 0; i < contacts.size(); i++) {
            selection.append("?");
            if (i < contacts.size() - 1) {
                selection.append(",");
            }
            selectionArgs[i] = contacts.get(i).id;
        }
        selection.append(")");

        String[] projection = {
                ContactsContract.CommonDataKinds.Email.CONTACT_ID,
                ContactsContract.CommonDataKinds.Email.ADDRESS
        };

        try (Cursor cursor = resolver.query(
                ContactsContract.CommonDataKinds.Email.CONTENT_URI,
                projection,
                selection.toString(),
                selectionArgs,
                null
        )) {
            if (cursor != null && cursor.moveToFirst()) {
                int idIndex = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Email.CONTACT_ID);
                int emailIndex = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Email.ADDRESS);
                do {
                    String contactId = cursor.getString(idIndex);
                    String email = cursor.getString(emailIndex);
                    if (email != null && !email.trim().isEmpty()) {
                        for (ContactTemp contact : contacts) {
                            if (contact.id.equals(contactId)) {
                                contact.emails.add(email);
                                break;
                            }
                        }
                    }
                } while (cursor.moveToNext());
            }
        } catch (Exception e) {
            // Gracefully ignore failures for secondary fields
        }
    }
}
