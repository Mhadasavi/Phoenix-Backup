package com.phoenix.companion.data;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import android.content.Context;
import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Instrumented integration tests running inside the Android runtime environment.
 * Asserts device context bindings and CallLog queries behavior.
 */
@RunWith(AndroidJUnit4.class)
public class CallLogProviderHelperAndroidTest {

    private CallLogProviderHelper helper;
    private Context context;

    @Before
    public void setUp() {
        helper = new CallLogProviderHelper();
        context = ApplicationProvider.getApplicationContext();
    }

    @Test
    public void testContextAndHelperInitialization() {
        assertNotNull(context);
        assertNotNull(helper);
    }

    @Test
    public void testGetCallLogsAsJson_ExecutionCheck() throws Exception {
        if (helper.hasCallLogPermission(context)) {
            String jsonResult = helper.getCallLogsAsJson(context, 10, 0);
            assertNotNull(jsonResult);
            
            JSONObject resultObj = new JSONObject(jsonResult);
            assertTrue(resultObj.has("status"));
            assertTrue(resultObj.has("data"));
            
            JSONObject dataObj = resultObj.getJSONObject("data");
            assertTrue(dataObj.has("call_logs"));
            assertTrue(dataObj.has("has_more"));
        } else {
            try {
                helper.getCallLogsAsJson(context, 10, 0);
                fail("Should have thrown SecurityException due to missing runtime permission");
            } catch (SecurityException e) {
                assertNotNull(e.getMessage());
            }
        }
    }
}
