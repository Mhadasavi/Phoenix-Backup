package com.phoenix.companion.service;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;

/**
 * Local JVM unit tests for BackupService's command handler routing.
 */
public class BackupServiceTest {

    private BackupService service;

    @Before
    public void setUp() {
        service = new BackupService();
        service.onCreate();
    }

    @Test
    public void testHandleCommand_GetSystemInfo() throws Exception {
        JSONObject request = new JSONObject();
        String result = service.handleCommand("GET_SYSTEM_INFO", request);
        JSONObject response = new JSONObject(result);

        assertEquals("SUCCESS", response.getString("status"));
        JSONObject data = response.getJSONObject("data");
        assertNotNull(data);
        
        // Under local JVM test with returnDefaultValues=true, Build.MANUFACTURER, Build.MODEL, 
        // and Build.VERSION.RELEASE evaluate to null and are not added by JSONObject.put. 
        // Build.VERSION.SDK_INT evaluates to 0 (primitive int default) and is successfully put.
        assertTrue(data.has("api_level"));
    }

    @Test
    public void testHandleCommand_UnknownCommand() throws Exception {
        JSONObject request = new JSONObject();
        String result = service.handleCommand("UNKNOWN_CMD", request);
        JSONObject response = new JSONObject(result);

        assertEquals("ERROR", response.getString("status"));
        assertTrue(response.getString("message").contains("Unknown command"));
    }

    @Test
    public void testHandleCommand_GetSms_NoPermission_ReturnsError() throws Exception {
        JSONObject request = new JSONObject();
        String result = service.handleCommand("GET_SMS", request);
        JSONObject response = new JSONObject(result);

        assertEquals("ERROR", response.getString("status"));
    }

    @Test
    public void testHandleCommand_GetContacts_NoPermission_ReturnsError() throws Exception {
        JSONObject request = new JSONObject();
        String result = service.handleCommand("GET_CONTACTS", request);
        JSONObject response = new JSONObject(result);

        assertEquals("ERROR", response.getString("status"));
    }

    @Test
    public void testHandleCommand_GetCallLogs_NoPermission_ReturnsError() throws Exception {
        JSONObject request = new JSONObject();
        String result = service.handleCommand("GET_CALL_LOGS", request);
        JSONObject response = new JSONObject(result);

        assertEquals("ERROR", response.getString("status"));
    }
}
