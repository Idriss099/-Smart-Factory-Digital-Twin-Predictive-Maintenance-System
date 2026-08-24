from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import pandas as pd
import time
import os
import snap7
from snap7.util import set_bool
from snap7.type import Area

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

log_filename = "sorting_station_telemetry_tags.csv"

def telemetry_background_thread():
    """
    مهمة خلفية لقراءة أحدث البيانات وحساب RUL وإرسالها عبر WebSocket
    """
    while True:
        try:
            if os.path.exists(log_filename):
                df = pd.read_csv(log_filename)
                if not df.empty:
                    latest = df.iloc[-1]
                    
                    # استخراج قيم الصحة من CSV
                    s1_health = float(latest.get('Sorter1_Health', 100))
                    s2_health = float(latest.get('Sorter2_Health', 100))
                    s3_health = float(latest.get('Sorter3_Health', 100))
                    
                    # حساب الـ RUL
                    rul_1 = max(0.0, round((s1_health - 80) * 12.5, 1))
                    rul_2 = max(0.0, round((s2_health - 80) * 12.5, 1))
                    rul_3 = max(0.0, round((s3_health - 80) * 12.5, 1))

                    data_packet = {
                        'Timestamp': time.strftime('%H:%M:%S'),
                        'VFD_Speed': float(latest.get('VFD_Speed', 0)),
                        'S1_Health': s1_health, 'S1_RUL': rul_1,
                        'S2_Health': s2_health, 'S2_RUL': rul_2,
                        'S3_Health': s3_health, 'S3_RUL': rul_3
                    }
                    
                    socketio.emit('live_telemetry', data_packet)
        except Exception as e:
            pass
        
        time.sleep(0.1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/control', methods=['POST'])
def control_system():
    command = request.json.get('command')
    try:
        # الاتصال بـ PLC
        plc_control = snap7.client.Client()
        plc_control.connect('127.0.0.1', 0, 2) 
        
        data = bytearray(1)
        
        if command == 'emergency_stop':
            set_bool(data, 0, 0, True) # M10.0
            plc_control.write_area(Area.MK, 0, 10, data)
            msg = "Emergency Stop Activated!"
            
        elif command == 'reduce_speed':
            set_bool(data, 0, 1, True) # M10.1
            plc_control.write_area(Area.MK, 0, 10, data)
            msg = "Speed Reduced Successfully!"
            
        elif command == 'reset_speed':
            set_bool(data, 0, 2, True) # M10.2
            plc_control.write_area(Area.MK, 0, 10, data)
            msg = "System Restored to Full Speed!"
            
        else:
            plc_control.disconnect()
            return jsonify({"status": "error", "msg": "Unknown Command"}), 400
            
        plc_control.disconnect()
        return jsonify({"status": "success", "msg": msg})
        
    except Exception as e:
        return jsonify({"status": "error", "msg": f"PLC Error: {str(e)}"}), 500

if __name__ == '__main__':
    print("🚀 Starting Smart Factory Digital Twin Server on http://localhost:5000")
    socketio.start_background_task(telemetry_background_thread)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)