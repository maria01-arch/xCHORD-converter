import os
import shutil
import subprocess
from flask import Flask, render_template_string, request, send_file, make_response
from PIL import Image

app = Flask(__name__)
BUILD_DIR = os.path.dirname(os.path.abspath(__file__))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>xChord Converter | xChordlabs LLC</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f172a; color: #f8fafc; display: flex; justify-content: center; padding: 20px; min-height: 100vh; align-items: center; }
        .card { background: #1e293b; padding: 30px; border-radius: 16px; width: 100%; max-width: 500px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h1 { font-size: 1.6rem; margin-bottom: 4px; color: #38bdf8; text-align: center; }
        .subtitle { font-size: 0.8rem; color: #64748b; text-align: center; margin-bottom: 24px; text-transform: uppercase; letter-spacing: 1px; }
        .form-group { margin-bottom: 16px; }
        label { display: block; font-size: 0.85rem; color: #94a3b8; margin-bottom: 6px; }
        input[type="text"], input[type="url"], input[type="color"] { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: #fff; font-size: 0.95rem; }
        input[type="file"] { width: 100%; padding: 8px; background: #0f172a; border-radius: 8px; border: 1px dashed #334155; color: #94a3b8; }
        .color-row { display: flex; gap: 10px; align-items: center; }
        .color-row input[type="color"] { width: 60px; height: 45px; padding: 2px; cursor: pointer; }
        .checkbox-group { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
        .checkbox-group input { width: 18px; height: 18px; cursor: pointer; }
        .checkbox-group label { margin-bottom: 0; cursor: pointer; color: #cbd5e1; }
        button { width: 100%; padding: 14px; background: #2563eb; color: #fff; border: none; border-radius: 8px; font-weight: bold; font-size: 1rem; cursor: pointer; margin-top: 15px; transition: 0.2s; }
        button:hover { background: #1d4ed8; }
        .error-msg { margin-top: 15px; font-size: 0.85rem; color: #ef4444; text-align: center; white-space: pre-wrap; word-break: break-all; }
        footer { margin-top: 20px; font-size: 0.75rem; text-align: center; color: #475569; }
    </style>
</head>
<body>
    <div class="card">
        <h1>xChord Converter</h1>
        <div class="subtitle">By xChordlabs LLC</div>
        
        <form action="/build" method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label>App Name</label>
                <input type="text" name="app_name" placeholder="e.g. My Web App" required>
            </div>
            <div class="form-group">
                <label>Package ID</label>
                <input type="text" name="package_id" placeholder="e.g. com.mycompany.app" required>
            </div>
            <div class="form-group">
                <label>Target URL</label>
                <input type="url" name="app_url" placeholder="https://example.com" required>
            </div>
            <div class="form-group">
                <label>Status Bar Color</label>
                <div class="color-row">
                    <input type="color" id="colorPicker" name="status_bar_color" value="#0f172a">
                    <input type="text" id="colorText" value="#0f172a" readonly>
                </div>
                <div class="checkbox-group">
                    <input type="checkbox" id="autoDark" name="auto_dark_theme" value="true" checked>
                    <label for="autoDark">Auto Dark/Light Theme matching System</label>
                </div>
            </div>
            <div class="form-group">
                <label>App Icon (PNG/JPG)</label>
                <input type="file" name="icon" accept="image/*">
            </div>
            <button type="submit">Generate & Download APK</button>
        </form>
        
        {% if error %}
        <div class="error-msg">Build Failed:<br>{{ error }}</div>
        {% endif %}

        <footer>Powered by xChordlabs LLC</footer>
    </div>

    <script>
        const colorPicker = document.getElementById('colorPicker');
        const colorText = document.getElementById('colorText');
        if (colorPicker && colorText) {
            colorPicker.addEventListener('input', (e) => colorText.value = e.target.value);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    response = make_response(render_template_string(HTML_TEMPLATE))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    return response

@app.route('/build', methods=['POST'])
def build():
    app_name = request.form.get('app_name')
    package_id = request.form.get('package_id')
    app_url = request.form.get('app_url')
    hex_color = request.form.get('status_bar_color', '#ffffff')
    auto_dark = request.form.get('auto_dark_theme') == 'true'
    icon_file = request.files.get('icon')

    src_base = os.path.join(BUILD_DIR, "src")
    if os.path.exists(src_base):
        shutil.rmtree(src_base)
    
    package_path = package_id.replace('.', '/')
    src_dir = os.path.join(src_base, package_path)
    os.makedirs(src_dir, exist_ok=True)

    icon_attr = ""
    if icon_file and icon_file.filename != '':
        res_dir = os.path.join(BUILD_DIR, "res", "mipmap")
        os.makedirs(res_dir, exist_ok=True)
        img = Image.open(icon_file)
        img = img.resize((192, 192))
        img.save(os.path.join(res_dir, "ic_launcher.png"), "PNG")
        icon_attr = 'android:icon="@mipmap/ic_launcher"'
    elif os.path.exists(os.path.join(BUILD_DIR, "res", "mipmap", "ic_launcher.png")):
        icon_attr = 'android:icon="@mipmap/ic_launcher"'

    manifest_content = f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_id}"
    android:versionCode="1"
    android:versionName="1.0">

    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="30" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <application
        android:label="{app_name}"
        {icon_attr}
        android:allowBackup="true"
        android:supportsRtl="true">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>"""
    with open(os.path.join(BUILD_DIR, "AndroidManifest.xml"), "w") as f:
        f.write(manifest_content)

    dark_theme_code = """
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            WebSettings webSettings = webView.getSettings();
            int nightModeFlags = getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK;
            if (nightModeFlags == android.content.res.Configuration.UI_MODE_NIGHT_YES) {
                webSettings.setForceDark(WebSettings.FORCE_DARK_ON);
            } else {
                webSettings.setForceDark(WebSettings.FORCE_DARK_OFF);
            }
        }
    """ if auto_dark else ""

    main_activity_content = f"""package {package_id};

import android.app.Activity;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {{

    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        super.onCreate(savedInstanceState);

        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        window.setStatusBarColor(Color.parseColor("{hex_color}"));

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {{
            window.getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        }}

        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);

        {dark_theme_code}

        webView.setWebViewClient(new WebViewClient());
        webView.loadUrl("{app_url}");
        setContentView(webView);
    }}

    @Override
    public void onBackPressed() {{
        if (webView != null && webView.canGoBack()) {{
            webView.goBack();
        }} else {{
            super.onBackPressed();
        }}
    }}
}}"""
    with open(os.path.join(src_dir, "MainActivity.java"), "w") as f:
        f.write(main_activity_content)

    try:
        subprocess.run(["bash", "build.sh"], capture_output=True, text=True, check=True)
        apk_path = os.path.join(BUILD_DIR, "app-release.apk")
        return send_file(apk_path, as_attachment=True, download_name="app-release.apk")
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr if e.stderr else e.stdout
        return render_template_string(HTML_TEMPLATE, error=err_msg)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
