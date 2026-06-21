package com.phoenix.companion.data;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import android.content.Context;
import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;

import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Instrumented integration tests running inside the Android runtime environment.
 * Asserts device context bindings, permission constraints, and content provider query loops.
 */
@RunWith(AndroidJUnit4.class)
public class ContactsProviderHelperAndroidTest {

    private ContactsProviderHelper helper;
    private Context context;

    @Before
    public void setUp() {
        helper = new ContactsProviderHelper();
        context = ApplicationProvider.getApplicationContext();
    }

    @Test
    public void testContextAndHelperInitialization() {
        assertNotNull(context);
        assertNotNull(helper);
    }

    @Test
    public void testGetContactsAsJson_ExecutionCheck() throws Exception {
        // Since we are running in instrumentation, we check permissions.
        // If permission is not granted, we assert that the SecurityException is thrown.
        // If permission is granted, we assert that the JSON structure queries and outputs correctly.
        if (helper.hasContactPermission(context)) {
            String jsonResult = helper.getContactsAsJson(context, 10, 0);
            assertNotNull(jsonResult);
            
            JSONObject resultObj = new JSONObject(jsonResult);
            assertTrue(resultObj.has("status"));
            assertTrue(resultObj.has("data"));
            
            JSONObject dataObj = resultObj.getJSONObject("data");
            assertTrue(dataObj.has("contacts"));
            assertTrue(dataObj.has("has_more"));
        } else {
            try {
                helper.getContactsAsJson(context, 10, 0);
                fail("Should have thrown SecurityException due to missing runtime permission");
            } catch (SecurityException e) {
                // Expected behavior when permission is not pre-granted via adb pm grant
                assertNotNull(e.getMessage());
            }
        }
    }
}
