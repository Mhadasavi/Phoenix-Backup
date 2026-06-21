package com.phoenix.companion;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
import android.view.Gravity;
import android.graphics.Color;

/**
 * Launcher activity for the companion app. Displays status information
 * and triggers network permission authorization on OEM devices.
 */
public class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        TextView textView = new TextView(this);
        textView.setText("Phoenix Backup Companion\n\nStatus: Ready & Listening\nConnection: local loopback only (127.0.0.1)");
        textView.setTextSize(18);
        textView.setTextColor(Color.WHITE);
        textView.setGravity(Gravity.CENTER);
        textView.setBackgroundColor(Color.parseColor("#0d1117")); // Match dark aesthetics
        
        setContentView(textView);
    }
}
