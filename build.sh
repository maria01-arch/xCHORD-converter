#!/bin/bash
set -e

if [ ! -f "android.jar" ]; then
    echo "=== Downloading valid android.jar ==="
    curl -L "https://raw.githubusercontent.com/Sable/android-platforms/master/android-30/android.jar" -o android.jar
fi

ANDROID_JAR="./android.jar"

echo "=== 1. Compiling Resources with AAPT2 ==="
aapt2 compile --dir res/ -o compiled_res.zip 2>/dev/null || true
if [ -f "compiled_res.zip" ]; then
    aapt2 link -I "$ANDROID_JAR" \
        --min-sdk-version 21 \
        --target-sdk-version 30 \
        compiled_res.zip \
        --manifest AndroidManifest.xml \
        -o unaligned.apk
else
    aapt2 link -I "$ANDROID_JAR" \
        --min-sdk-version 21 \
        --target-sdk-version 30 \
        --manifest AndroidManifest.xml \
        -o unaligned.apk
fi

echo "=== 2. Compiling Java Source Files ==="
JAVA_FILES=$(find src -name "*.java")
javac -source 8 -target 8 -Xlint:-options -cp "$ANDROID_JAR" $JAVA_FILES

echo "=== 3. Converting Bytecode to DEX ==="
if [ ! -f "r8.jar" ]; then
    curl -L "https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.2.42/r8-8.2.42.jar" -o r8.jar
fi

CLASS_FILES=$(find src -name "*.class")
java -cp r8.jar com.android.tools.r8.D8 --lib "$ANDROID_JAR" --min-api 21 --output . $CLASS_FILES

echo "=== 4. Packaging DEX into APK ==="
zip -0 -j unaligned.apk classes.dex

echo "=== 5. Aligning APK Offsets ==="
python3 -c '
import zipfile, struct

infile = "unaligned.apk"
outfile = "aligned.apk"

with zipfile.ZipFile(infile, "r") as zin, zipfile.ZipFile(outfile, "w") as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        zinfo = zipfile.ZipInfo(item.filename)
        zinfo.compress_type = item.compress_type
        
        if item.compress_type == zipfile.ZIP_STORED:
            pos = zout.fp.tell()
            filename_bytes = item.filename.encode("utf-8")
            base_header_len = 30 + len(filename_bytes)
            target_rem = (pos + base_header_len + 4) % 4
            padding_len = (4 - target_rem) % 4
            
            zinfo.extra = struct.pack("<HH", 0xD909, padding_len) + (b"\x00" * padding_len)
        
        zout.writestr(zinfo, data)
'

echo "=== 6. Signing APK ==="
apksigner sign \
    --ks release.jks \
    --ks-key-alias mykey \
    --ks-pass pass:123456 \
    --min-sdk-version 21 \
    --out app-release.apk \
    aligned.apk

echo "=== 7. Copying Output ==="
mkdir -p /sdcard/Download
cp app-release.apk /sdcard/Download/app-release.apk

echo "=== BUILD SUCCESSFUL ==="
