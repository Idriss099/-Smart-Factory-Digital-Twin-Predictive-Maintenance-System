from datetime import datetime
import os
import time
import pandas as pd
import snap7
from snap7.util import get_int
import snap7.type as sevtypes

# الاتصال بالـ PLC عبر NetToPLCsim
plc = snap7.client.Client()
plc.connect('127.0.0.1', 0, 2)  # IP, Rack=0, Slot=2

MAX_CYCLES_SORTER1 = 150
MAX_CYCLES_SORTER2 = 150
MAX_CYCLES_SORTER3 = 150

def calculate_health_score(current_cycles, max_limit):
    health = 100 - ((current_cycles / max_limit) * 100)
    return max(0, round(health, 2))

def get_status_msg(health):
    if health > 50:
        return "🟢 NORMAL"
    elif 20 <= health <= 50:
        return "🟡 WARNING"
    else:
        return "🔴 CRITICAL"

if plc.get_connected():
    print("=" * 70)
    print(" 🚀 INDUSTRIAL DIGITAL TWIN & PREDICTIVE MAINTENANCE ENGINE ACTIVE")
    print("=" * 70)
else:
    print("Failed to connect to PLCSIM!")
    exit()

log_filename = "sorting_station_telemetry_tags.csv"
anomaly_filename = "sorting_station_anomalies.csv"

start_time = time.time()

try:
    while True:
        # قراءة العدادات من الـ Outputs (QW30 إلى QW42)
        data_outputs = plc.read_area(sevtypes.Areas.PA, 0, 30, 16)
        
        box_count_1 = get_int(data_outputs, 0)
        box_count_2 = get_int(data_outputs, 4)
        box_count_3 = get_int(data_outputs, 8)
        vfd_speed = get_int(data_outputs, 12)

        # قراءة حساس الرؤية من الـ Inputs (IW30)
        data_inputs = plc.read_area(sevtypes.Areas.PE, 0, 30, 2)
        vision_sensor_val = get_int(data_inputs, 0)

        # حساب مؤشرات الصحة
        s1_health = calculate_health_score(box_count_1, MAX_CYCLES_SORTER1)
        s2_health = calculate_health_score(box_count_2, MAX_CYCLES_SORTER2)
        s3_health = calculate_health_score(box_count_3, MAX_CYCLES_SORTER3)

        s1_status = get_status_msg(s1_health)
        s2_status = get_status_msg(s2_health)
        s3_status = get_status_msg(s3_health)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uptime_sec = int(time.time() - start_time)

        # مسح الشاشة أو طباعة فاصل أنيق لعرض لوحة تحكم حية متجددة
        print(f"\n[⏱️ Uptime: {uptime_sec}s | Timestamp: {timestamp}]")
        print(f"⚙️ VFD Motor Speed: {vfd_speed} Hz  |  👁️ Vision Sensor: {vision_sensor_val}")
        print("-" * 70)
        print(f" > Sorter Station 1: {box_count_1:3d} boxes | Health: {s1_health:5.2f}% | Status: {s1_status}")
        print(f" > Sorter Station 2: {box_count_2:3d} boxes | Health: {s2_health:5.2f}% | Status: {s2_status}")
        print(f" > Sorter Station 3: {box_count_3:3d} boxes | Health: {s3_health:5.2f}% | Status: {s3_status}")
        print("=" * 70)

        # كشف الشذوذ (Anomaly Detection): مثلاً إذا دار المحرك ولم يتم فرز أي صندوق لفترة أو حدثت مشكلة
        if vfd_speed > 0 and s1_status == "🔴 CRITICAL":
            anomaly_row = {"Timestamp": timestamp, "Event": "Sorter 1 Over-cycle Critical Alert"}
            pd.DataFrame([anomaly_row]).to_csv(anomaly_filename, mode="a", header=not os.path.exists(anomaly_filename), index=False)

        # حفظ البيانات في ملف Telemetry CSV الرئيسي
        data_row = {
            "Timestamp": timestamp,
            "Uptime_Sec": uptime_sec,
            "VFD_Speed": vfd_speed,
            "Vision_Sensor": vision_sensor_val,
            "Box_Count_Sorter1": box_count_1,
            "Sorter1_Health": s1_health,
            "Box_Count_Sorter2": box_count_2,
            "Sorter2_Health": s2_health,
            "Box_Count_Sorter3": box_count_3,
            "Sorter3_Health": s3_health,
        }

        df = pd.DataFrame([data_row])
        file_exists = os.path.exists(log_filename)
        df.to_csv(log_filename, mode="a", header=not file_exists, index=False)

        time.sleep(1)

except KeyboardInterrupt:
    plc.disconnect()
    print("\n🛑 Digital Twin system safely disconnected.")
except Exception as e:
    plc.disconnect()
    print(f"\n❌ Error: {e}")