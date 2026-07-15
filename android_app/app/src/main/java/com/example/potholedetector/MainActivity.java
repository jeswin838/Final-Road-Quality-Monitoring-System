package com.example.potholedetector;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.pm.PackageManager;
import android.app.AlertDialog;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.location.Location;
import android.location.LocationManager;
import android.provider.Settings;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageCapture;
import androidx.camera.core.ImageCaptureException;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationCallback;
import com.google.android.gms.location.LocationRequest;
import com.google.android.gms.location.LocationResult;
import com.google.android.gms.location.LocationServices;
import com.google.android.gms.location.Priority;
import com.google.android.material.floatingactionbutton.ExtendedFloatingActionButton;
import com.google.common.util.concurrent.ListenableFuture;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

public class MainActivity extends AppCompatActivity {

    private static final String TAG = "PotholeDetector";
    private static final String BASE_URL = "http://10.27.99.180:5000";
    private static final int PERMISSION_REQUEST_CODE = 1001;

    // Capture configuration
    private static final int  BURST_COUNT        = 3;     // Number of frames per trigger
    private static final int  BURST_INTERVAL_MS  = 150;   // Gap between burst frames (ms)
    private static final int  TRIGGER_DELAY_MS   = 300;   // Delay from trigger to first capture
    private static final int  POLLING_INTERVAL   = 3000;  // Poll /check every 3 seconds
    private static final int  COOLDOWN_PERIOD    = 8000;  // Lock after a successful event

    private PreviewView viewFinder;
    private TextView logTextView;
    private ProgressBar progressBar;
    private TextView locationTextView;
    private ExtendedFloatingActionButton fabReport;

    private ImageCapture imageCapture;
    private ExecutorService cameraExecutor;
    private FusedLocationProviderClient fusedLocationClient;
    private LocationCallback locationCallback;
    private Location currentLocation;
    private boolean isTrackingLocation = false;
    private boolean isGpsReady = false;
    private static final float REQUIRED_ACCURACY_METERS = 10.0f;

    private volatile boolean isCapturing = false;
    private final Handler pollingHandler  = new Handler(Looper.getMainLooper());
    private final Handler captureHandler  = new Handler(Looper.getMainLooper());

    private final BroadcastReceiver gpsReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (LocationManager.PROVIDERS_CHANGED_ACTION.equals(intent.getAction())) {
                if (isGpsProviderEnabled()) {
                    Log.d(TAG, "GPS Enabled");
                    if (!isTrackingLocation && !isCapturing) {
                        startLocationUpdates();
                    }
                } else {
                    Log.d(TAG, "GPS Disabled");
                    Log.d(TAG, "GPS Lost");
                    invalidateGpsState();
                }
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        viewFinder     = findViewById(R.id.viewFinder);
        logTextView    = findViewById(R.id.logTextView);
        progressBar    = findViewById(R.id.uploadProgress);
        locationTextView = findViewById(R.id.locationTextView);
        fabReport      = findViewById(R.id.fabReport);

        cameraExecutor       = Executors.newSingleThreadExecutor();
        fusedLocationClient  = LocationServices.getFusedLocationProviderClient(this);

        fabReport.setEnabled(false);
        locationTextView.setText("Waiting for GPS...");
        fabReport.setOnClickListener(v -> handleManualReport());

        registerReceiver(gpsReceiver, new IntentFilter(LocationManager.PROVIDERS_CHANGED_ACTION));

        if (allPermissionsGranted()) {
            startCamera();
            startPolling();
            startLocationUpdates();
        } else {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.CAMERA, Manifest.permission.ACCESS_FINE_LOCATION},
                    PERMISSION_REQUEST_CODE);
        }
    }

    private boolean allPermissionsGranted() {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
            && ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (allPermissionsGranted()) {
                startCamera();
                startPolling();
                startLocationUpdates();
            } else {
                fabReport.setEnabled(false);
                if (locationTextView != null) {
                    locationTextView.setText("Location permission required.");
                }

                boolean shouldShowRationale = ActivityCompat.shouldShowRequestPermissionRationale(this, Manifest.permission.ACCESS_FINE_LOCATION);
                
                if (shouldShowRationale) {
                    new AlertDialog.Builder(this)
                            .setMessage("Location permission required.")
                            .setCancelable(false)
                            .setPositiveButton("Grant Permission Again", (dialog, which) -> {
                                ActivityCompat.requestPermissions(MainActivity.this,
                                        new String[]{Manifest.permission.CAMERA, Manifest.permission.ACCESS_FINE_LOCATION},
                                        PERMISSION_REQUEST_CODE);
                            })
                            .setNegativeButton("Back", (dialog, which) -> {
                                finish();
                            })
                            .show();
                } else {
                    new AlertDialog.Builder(this)
                            .setMessage("Location permission is required to detect potholes.")
                            .setCancelable(false)
                            .setPositiveButton("Open Settings", (dialog, which) -> {
                                Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                                android.net.Uri uri = android.net.Uri.fromParts("package", getPackageName(), null);
                                intent.setData(uri);
                                startActivity(intent);
                            })
                            .setNegativeButton("Back", (dialog, which) -> {
                                finish();
                            })
                            .show();
                }
            }
        }
    }

    private void startCamera() {
        ListenableFuture<ProcessCameraProvider> cameraProviderFuture =
                ProcessCameraProvider.getInstance(this);

        cameraProviderFuture.addListener(() -> {
            try {
                ProcessCameraProvider cameraProvider = cameraProviderFuture.get();

                Preview preview = new Preview.Builder().build();
                preview.setSurfaceProvider(viewFinder.getSurfaceProvider());

                imageCapture = new ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                        .build();

                CameraSelector cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA;

                cameraProvider.unbindAll();
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageCapture);

                addLog("✨ System Ready. Monitoring live...");
            } catch (ExecutionException | InterruptedException e) {
                Log.e(TAG, "Camera binding failed", e);
            }
        }, ContextCompat.getMainExecutor(this));
    }

    // ── Polling ──────────────────────────────────────────────
    private void startPolling() {
        pollingHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                if (!isCapturing) {
                    checkServerTrigger();
                }
                pollingHandler.postDelayed(this, POLLING_INTERVAL);
            }
        }, POLLING_INTERVAL);
    }

    @SuppressLint("MissingPermission")
    private void startLocationUpdates() {
        if (!checkGPSEnabled()) return;
        if (isTrackingLocation) return;
        
        isGpsReady = false;
        runOnUiThread(() -> {
            fabReport.setEnabled(false);
            if (locationTextView != null && !locationTextView.getText().toString().contains("Acc:")) {
                locationTextView.setText("Acquiring accurate location...");
            }
        });
        
        if (locationCallback == null) {
            locationCallback = new LocationCallback() {
                @Override
                public void onLocationResult(@NonNull LocationResult locationResult) {
                    if (locationResult == null) return;
                    Location location = locationResult.getLastLocation();
                    if (location != null) {
                        Log.d(TAG, "New Location Received");
                        long age = System.currentTimeMillis() - location.getTime();
                        if (age > 15000) return; // skip old cached locations
                        
                        currentLocation = location;
                        float acc = location.getAccuracy();
                        if (acc <= REQUIRED_ACCURACY_METERS && location.getLatitude() != 0 && location.getLongitude() != 0) {
                            if (!isGpsReady) Log.d(TAG, "GPS Ready");
                            isGpsReady = true;
                            fabReport.setEnabled(true);
                            locationTextView.setText(String.format(Locale.US,
                                    "%.4f, %.4f (Acc: %.1fm) - GPS Ready", 
                                    location.getLatitude(), location.getLongitude(), acc));
                        } else {
                            isGpsReady = false;
                            fabReport.setEnabled(false);
                            locationTextView.setText(String.format(Locale.US,
                                    "Waiting for accurate GPS... (Acc: %.1fm)", acc));
                        }
                    }
                }
            };
        }

        LocationRequest locationRequest = new LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 2000)
                .setMinUpdateDistanceMeters(2.0f)
                .build();

        fusedLocationClient.requestLocationUpdates(locationRequest,
                locationCallback,
                Looper.getMainLooper());
                
        isTrackingLocation = true;
    }

    private void stopLocationUpdates() {
        if (fusedLocationClient != null && locationCallback != null) {
            fusedLocationClient.removeLocationUpdates(locationCallback);
            isTrackingLocation = false;
        }
    }

    private void invalidateGpsState() {
        currentLocation = null;
        isGpsReady = false;
        runOnUiThread(() -> {
            fabReport.setEnabled(false);
            if (locationTextView != null) {
                locationTextView.setText("Enable GPS to continue.");
            }
        });
    }

    private boolean isGpsProviderEnabled() {
        LocationManager locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        return locationManager != null && locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER);
    }

    private boolean checkGPSEnabled() {
        if (!isGpsProviderEnabled()) {
            invalidateGpsState();
            new AlertDialog.Builder(this)
                    .setMessage("Enable GPS to continue.")
                    .setCancelable(false)
                    .setPositiveButton("Enable GPS", (dialog, which) -> {
                        startActivity(new Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS));
                    })
                    .setNegativeButton("Cancel", null)
                    .show();
            return false;
        }
        return true;
    }

    private void checkServerTrigger() {
        new Thread(() -> {
            try {
                URL url = new URL(BASE_URL + "/check");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(3000);
                conn.setReadTimeout(3000);

                if (conn.getResponseCode() == 200) {
                    BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = in.readLine()) != null) sb.append(line);
                    in.close();

                    JSONObject json = new JSONObject(sb.toString());
                    if (json.optBoolean("capture", false)) {
                        runOnUiThread(() -> {
                            addLog("🚨 TRIGGER: Pothole detected ahead!");
                            // Delay capture by TRIGGER_DELAY_MS for better camera positioning
                            captureHandler.postDelayed(() -> startBurstCapture(false), TRIGGER_DELAY_MS);
                        });
                    }
                }
            } catch (Exception e) {
                Log.e(TAG, "Polling error: " + e.getMessage());
            }
        }).start();
    }

    // ── Manual Report ────────────────────────────────────────
    private void handleManualReport() {
        if (!isGpsReady) {
            Toast.makeText(this, "Waiting for accurate GPS...", Toast.LENGTH_SHORT).show();
            return;
        }
        if (isCapturing) {
            Toast.makeText(this, "System busy...", Toast.LENGTH_SHORT).show();
            return;
        }
        addLog("📝 USER REPORT: Initiating manual capture...");
        captureAndUploadSingle(true);
    }

    // ── Burst Capture ────────────────────────────────────────
    /**
     * Captures BURST_COUNT frames with BURST_INTERVAL_MS gap between each.
     * Collects all frames, then uploads them together to /analyze.
     */
    private void startBurstCapture(boolean isManual) {
        if (isCapturing || imageCapture == null) return;
        if (!isGpsReady && !isManual) {
            addLog("⚠️ Trigger ignored: GPS not ready");
            return;
        }
        isCapturing = true;
        stopLocationUpdates();

        addLog("📸 Burst capture starting (" + BURST_COUNT + " frames)...");

        List<File> capturedFiles = new ArrayList<>();
        AtomicInteger remaining  = new AtomicInteger(BURST_COUNT);

        for (int i = 0; i < BURST_COUNT; i++) {
            final int frameIndex = i;
            captureHandler.postDelayed(() -> {
                String tag = new SimpleDateFormat("HHmmss_SSS", Locale.US).format(new Date());
                File photoFile = new File(getExternalFilesDir(null),
                        "BURST_" + frameIndex + "_" + tag + ".jpg");

                ImageCapture.OutputFileOptions opts =
                        new ImageCapture.OutputFileOptions.Builder(photoFile).build();

                imageCapture.takePicture(opts, ContextCompat.getMainExecutor(this),
                        new ImageCapture.OnImageSavedCallback() {
                            @Override
                            public void onImageSaved(@NonNull ImageCapture.OutputFileResults r) {
                                synchronized (capturedFiles) {
                                    capturedFiles.add(photoFile);
                                }
                                if (remaining.decrementAndGet() == 0) {
                                    // All frames captured — upload best frames
                                    addLog("✅ Burst done — uploading " + capturedFiles.size() + " frames");
                                    fetchLocationAndUploadBurst(capturedFiles);
                                }
                            }

                            @Override
                            public void onError(@NonNull ImageCaptureException e) {
                                addLog("❌ Frame " + frameIndex + " failed: " + e.getMessage());
                                if (remaining.decrementAndGet() == 0 && !capturedFiles.isEmpty()) {
                                    fetchLocationAndUploadBurst(capturedFiles);
                                } else if (remaining.get() == 0) {
                                    releaseCooldown();
                                }
                            }
                        });
            }, (long) i * BURST_INTERVAL_MS);
        }
    }

    private void fetchLocationAndUploadBurst(List<File> files) {
        if (!isGpsProviderEnabled() || currentLocation == null || !isGpsReady) {
            Log.d(TAG, "Upload Cancelled (GPS unavailable)");
            runOnUiThread(() -> {
                locationTextView.setText("Enable GPS to continue.");
                addLog("❌ Upload Cancelled (GPS unavailable)");
            });
            releaseCooldown();
            return;
        }
        double lat = currentLocation.getLatitude();
        double lon = currentLocation.getLongitude();
        Log.d(TAG, "Frozen GPS:\nLatitude=" + lat + "\nLongitude=" + lon + "\nAccuracy=" + currentLocation.getAccuracy());
        uploadBurst(files, lat, lon);
    }

    /**
     * Uploads all burst frames to /analyze as a multipart form-data request.
     * The Flask backend selects the best frame automatically.
     */
    private void uploadBurst(List<File> files, double lat, double lon) {
        runOnUiThread(() -> progressBar.setVisibility(View.VISIBLE));

        new Thread(() -> {
            boolean success = false;
            int retryCount  = 0;

            while (!success && retryCount < 3) {
                try {
                    String boundary = "----Burst" + System.currentTimeMillis();
                    URL url = new URL(BASE_URL + "/analyze");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setDoOutput(true);
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
                    conn.setConnectTimeout(10000);
                    conn.setReadTimeout(15000);

                    DataOutputStream dos = new DataOutputStream(conn.getOutputStream());

                    // Lat / Lon fields
                    writeFormField(dos, "lat", String.valueOf(lat), boundary);
                    writeFormField(dos, "lon", String.valueOf(lon), boundary);

                    // All frames as "image" fields
                    for (File f : files) {
                        writeFileField(dos, "image", f, boundary);
                    }

                    dos.writeBytes("--" + boundary + "--\r\n");
                    dos.flush();
                    dos.close();

                    int code = conn.getResponseCode();
                    if (code == 200 || code == 201) {
                        // Read response for logging
                        BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                        StringBuilder sb = new StringBuilder();
                        String line;
                        while ((line = br.readLine()) != null) sb.append(line);
                        br.close();

                        String responseBody = sb.toString();
                        Log.d(TAG, "Analyze response: " + responseBody);
                        success = true;
                        runOnUiThread(() -> addLog("✅ UPLOAD SUCCESS: " + responseBody));
                    } else {
                        retryCount++;
                        Thread.sleep(1500);
                    }

                } catch (Exception e) {
                    Log.e(TAG, "Upload error: " + e.getMessage());
                    retryCount++;
                    try { Thread.sleep(1500); } catch (InterruptedException ignored) {}
                }
            }

            if (!success) {
                runOnUiThread(() -> addLog("❌ UPLOAD FAILED after retries"));
            }
            releaseCooldown();
        }).start();
    }

    // ── Single capture (manual report) ───────────────────────
    private void captureAndUploadSingle(boolean isManual) {
        if (isCapturing || imageCapture == null) return;
        isCapturing = true;
        stopLocationUpdates();

        File photoFile = new File(getExternalFilesDir(null),
                "USER_" + new SimpleDateFormat("HHmmss", Locale.US).format(new Date()) + ".jpg");

        ImageCapture.OutputFileOptions opts =
                new ImageCapture.OutputFileOptions.Builder(photoFile).build();

        imageCapture.takePicture(opts, ContextCompat.getMainExecutor(this),
                new ImageCapture.OnImageSavedCallback() {
                    @Override
                    public void onImageSaved(@NonNull ImageCapture.OutputFileResults r) {
                        fetchLocationAndUploadSingle(photoFile);
                    }

                    @Override
                    public void onError(@NonNull ImageCaptureException e) {
                        addLog("❌ CAPTURE FAILED: " + e.getMessage());
                        releaseCooldown();
                    }
                });
    }

    private void fetchLocationAndUploadSingle(File photoFile) {
        if (!isGpsProviderEnabled() || currentLocation == null || !isGpsReady) {
            Log.d(TAG, "Upload Cancelled (GPS unavailable)");
            runOnUiThread(() -> {
                locationTextView.setText("Enable GPS to continue.");
                addLog("❌ Upload Cancelled (GPS unavailable)");
            });
            releaseCooldown();
            return;
        }
        double lat = currentLocation.getLatitude();
        double lon = currentLocation.getLongitude();
        Log.d(TAG, "Frozen GPS:\nLatitude=" + lat + "\nLongitude=" + lon + "\nAccuracy=" + currentLocation.getAccuracy());
        uploadSingle(photoFile, lat, lon);
    }

    private void uploadSingle(File photoFile, double lat, double lon) {
        runOnUiThread(() -> progressBar.setVisibility(View.VISIBLE));

        new Thread(() -> {
            boolean success = false;
            int retryCount  = 0;

            while (!success && retryCount < 3) {
                try {
                    String boundary = "----Single" + System.currentTimeMillis();
                    URL url = new URL(BASE_URL + "/user-report");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setDoOutput(true);
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
                    conn.setConnectTimeout(10000);
                    conn.setReadTimeout(15000);

                    DataOutputStream dos = new DataOutputStream(conn.getOutputStream());
                    writeFormField(dos, "lat", String.valueOf(lat), boundary);
                    writeFormField(dos, "lon", String.valueOf(lon), boundary);
                    writeFileField(dos, "image", photoFile, boundary);
                    dos.writeBytes("--" + boundary + "--\r\n");
                    dos.flush();
                    dos.close();

                    int code = conn.getResponseCode();
                    if (code == 200 || code == 201) {
                        success = true;
                        runOnUiThread(() -> addLog("✅ REPORT SUBMITTED"));
                    } else {
                        retryCount++;
                        Thread.sleep(1500);
                    }
                } catch (Exception e) {
                    retryCount++;
                    try { Thread.sleep(1500); } catch (InterruptedException ignored) {}
                }
            }
            releaseCooldown();
        }).start();
    }

    // ── Cooldown Release ─────────────────────────────────────
    private void releaseCooldown() {
        runOnUiThread(() -> {
            progressBar.setVisibility(View.GONE);
            addLog("⏳ Cooldown active...");
            new Handler(Looper.getMainLooper()).postDelayed(() -> {
                isCapturing = false;
                addLog("✨ Ready for next detection.");
                startLocationUpdates();
            }, COOLDOWN_PERIOD);
        });
    }

    // ── Multipart Helpers ─────────────────────────────────────
    private void writeFormField(DataOutputStream dos, String name, String value, String boundary) throws Exception {
        dos.writeBytes("--" + boundary + "\r\n");
        dos.writeBytes("Content-Disposition: form-data; name=\"" + name + "\"\r\n\r\n");
        dos.writeBytes(value + "\r\n");
    }

    private void writeFileField(DataOutputStream dos, String name, File file, String boundary) throws Exception {
        dos.writeBytes("--" + boundary + "\r\n");
        dos.writeBytes("Content-Disposition: form-data; name=\"" + name + "\"; filename=\"" + file.getName() + "\"\r\n");
        dos.writeBytes("Content-Type: image/jpeg\r\n\r\n");
        FileInputStream fis = new FileInputStream(file);
        byte[] buffer = new byte[4096];
        int read;
        while ((read = fis.read(buffer)) != -1) dos.write(buffer, 0, read);
        dos.writeBytes("\r\n");
        fis.close();
    }

    // ── Logging ──────────────────────────────────────────────
    private void addLog(String message) {
        String timestamp = new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date());
        logTextView.append("\n[" + timestamp + "] " + message);
        View scrollView = findViewById(R.id.logScrollView);
        if (scrollView != null) {
            scrollView.post(() -> ((android.widget.ScrollView) scrollView).fullScroll(View.FOCUS_DOWN));
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        try {
            unregisterReceiver(gpsReceiver);
        } catch (IllegalArgumentException e) {
            // ignored
        }
        stopLocationUpdates();
        cameraExecutor.shutdown();
        pollingHandler.removeCallbacksAndMessages(null);
        captureHandler.removeCallbacksAndMessages(null);
    }
}
