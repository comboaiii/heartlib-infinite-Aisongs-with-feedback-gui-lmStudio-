import socket
import struct
import cv2
import numpy as np
import threading
import concurrent.futures
import pyvirtualcam
from pyvirtualcam import PixelFormat
import time
import sys

# ================= CONFIG =================
WIDTH = 1920
HEIGHT = 1080
FPS = 30
VIDEO_PORT = 6000
PREVIEW_SCALE = 0.5  # Smaller preview for Windows desktop

# Network scanning
# Common Windows subnets
SEARCH_SUBNETS = ["192.168.1.", "192.168.0.", "192.168.8.", "10.0.0."]
MANUAL_IPS = []  # Add static IPs here if needed


# ================= STATE MANAGEMENT =================
class MultiStreamState:
    def __init__(self):
        self.frames = {}  # ip -> frame
        self.rotations = {}  # ip -> rotation angle
        self.discovered_ips = set(MANUAL_IPS)
        self.active_ips = []  # Currently online IPs
        self.layout_mode = 0  # 0=auto, 1=cam1 only, 2=cam2 only
        self.mirror = False
        self.selected_cam = 0  # For rotation control
        self.show_ui = True
        self.lock = threading.Lock()

    def add_ip(self, ip):
        with self.lock:
            if ip not in self.discovered_ips:
                self.discovered_ips.add(ip)
                self.rotations[ip] = 0
                print(f"✨ NEW PHONE FOUND: {ip}")
                return True
        return False

    def update_frame(self, ip, frame):
        with self.lock:
            self.frames[ip] = frame
            if ip not in self.active_ips:
                self.active_ips.append(ip)

    def remove_ip(self, ip):
        with self.lock:
            if ip in self.frames:
                del self.frames[ip]
            if ip in self.active_ips:
                self.active_ips.remove(ip)

    def rotate_selected(self):
        with self.lock:
            if self.selected_cam < len(self.active_ips):
                ip = self.active_ips[self.selected_cam]
                self.rotations[ip] = (self.rotations.get(ip, 0) + 90) % 360
                print(f"🔄 Camera {self.selected_cam + 1} rotated to {self.rotations[ip]}°")


state = MultiStreamState()


# ================= NETWORK SCANNING =================
def verify_camera_port(ip, retries=1):
    for _ in range(retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex((ip, VIDEO_PORT))
            sock.close()
            if result == 0:
                return True
        except:
            pass
    return False


def continuous_network_scanner():
    print(f"🔍 Starting network scanner...")
    while True:
        try:
            all_ips = []
            for subnet in SEARCH_SUBNETS:
                all_ips.extend([f"{subnet}{i}" for i in range(1, 255)])

            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                results = executor.map(lambda ip: (ip, verify_camera_port(ip)), all_ips)

                for ip, is_camera in results:
                    if is_camera:
                        if state.add_ip(ip):
                            threading.Thread(target=receiver_thread, args=(ip,), daemon=True).start()
            time.sleep(15)
        except Exception as e:
            print(f"⚠️ Scanner error: {e}")
            time.sleep(5)


# ================= CAMERA RECEIVER =================
def receiver_thread(ip):
    retry_delay = 2
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5)
            client.connect((ip, VIDEO_PORT))
            connection = client.makefile('rb')
            print(f"✅ Connected: {ip}")
            retry_delay = 2

            while True:
                # Read size
                size_data = connection.read(4)
                if not size_data: break
                size = struct.unpack('>I', size_data)[0]

                # Read extra data (rotation placeholder)
                connection.read(4)

                # Read image data
                data = b''
                while len(data) < size:
                    packet = connection.read(size - len(data))
                    if not packet: break
                    data += packet

                if len(data) != size: break

                # Decode
                frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    state.update_frame(ip, frame)

        except:
            pass  # Silent fail to keep console clean
        finally:
            try:
                client.close()
            except:
                pass
            state.remove_ip(ip)
            time.sleep(retry_delay)


# ================= FRAME PROCESSING =================
def create_output_frame():
    """Build the final image sent to Virtual Camera"""
    with state.lock:
        online_ips = list(state.active_ips)

    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

    if not online_ips:
        return canvas

    # --- LAYOUT LOGIC ---
    if state.layout_mode == 0:  # Auto
        if len(online_ips) == 1:
            canvas = process_camera_frame_for_output(state.frames.get(online_ips[0]), online_ips[0], WIDTH, HEIGHT)
        elif len(online_ips) >= 2:
            # Split screen
            frame1 = process_camera_frame_for_output(state.frames.get(online_ips[0]), online_ips[0], WIDTH // 2, HEIGHT)
            frame2 = process_camera_frame_for_output(state.frames.get(online_ips[1]), online_ips[1], WIDTH // 2, HEIGHT)
            canvas[:, :WIDTH // 2] = frame1
            canvas[:, WIDTH // 2:] = frame2

    elif state.layout_mode == 1 and len(online_ips) > 0:  # Cam 1 Only
        canvas = process_camera_frame_for_output(state.frames.get(online_ips[0]), online_ips[0], WIDTH, HEIGHT)

    elif state.layout_mode == 2 and len(online_ips) > 1:  # Cam 2 Only
        canvas = process_camera_frame_for_output(state.frames.get(online_ips[1]), online_ips[1], WIDTH, HEIGHT)

    # --- MIRROR ---
    if state.mirror:
        canvas = cv2.flip(canvas, 1)

    return canvas


def process_camera_frame_for_output(img, ip, target_w, target_h):
    """Handle rotation and resizing"""
    if img is None:
        return np.zeros((target_h, target_w, 3), dtype=np.uint8)

    # Apply Rotation
    rot = state.rotations.get(ip, 0)
    if rot == 90:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif rot == 180:
        img = cv2.rotate(img, cv2.ROTATE_180)
    elif rot == 270:
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

    # Resize keeping aspect ratio
    h, w = img.shape[:2]
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h))

    # Center on black background
    final = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    final[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

    return final


def create_ui_display():
    """Create the Control Panel UI"""
    ui = np.zeros((300, 800, 3), dtype=np.uint8)
    ui.fill(40)  # Dark gray bg

    # Text Settings
    font = cv2.FONT_HERSHEY_SIMPLEX
    white = (255, 255, 255)
    green = (100, 255, 100)

    with state.lock:
        online_ips = list(state.active_ips)

    cv2.putText(ui, "WINDOWS MULTI-CAM CONTROLLER", (20, 40), font, 1.0, (0, 200, 255), 2)

    # Status
    cv2.putText(ui, f"Active Cams: {len(online_ips)}", (20, 80), font, 0.8, green if online_ips else (100, 100, 100), 2)

    # Settings
    modes = ["AUTO (Split/Full)", "CAM 1 ONLY", "CAM 2 ONLY"]
    cv2.putText(ui, f"Layout [L]: {modes[state.layout_mode]}", (20, 120), font, 0.7, white, 2)
    cv2.putText(ui, f"Mirror [M]: {'ON' if state.mirror else 'OFF'}", (20, 150), font, 0.7, white, 2)

    sel_idx = state.selected_cam
    sel_name = online_ips[sel_idx] if sel_idx < len(online_ips) else "None"
    cv2.putText(ui, f"Selected [1/2]: Cam {sel_idx + 1} ({sel_name})", (20, 180), font, 0.7, (0, 255, 255), 2)

    # Instructions
    cv2.putText(ui, "CONTROLS:", (500, 80), font, 0.7, (255, 200, 0), 2)
    cv2.putText(ui, "R = Rotate Selected", (500, 110), font, 0.6, white, 1)
    cv2.putText(ui, "L = Change Layout", (500, 135), font, 0.6, white, 1)
    cv2.putText(ui, "M = Mirror", (500, 160), font, 0.6, white, 1)
    cv2.putText(ui, "1/2 = Select Cam", (500, 185), font, 0.6, white, 1)
    cv2.putText(ui, "H = Toggle UI", (500, 210), font, 0.6, white, 1)
    cv2.putText(ui, "Q = Quit", (500, 235), font, 0.6, white, 1)

    return ui


# ================= MAIN =================
def main():
    print("=" * 50)
    print("  WINDOWS MULTI-PHONE CAMERA (With Controls)")
    print("=" * 50)

    # 1. Start Network Scanner
    threading.Thread(target=continuous_network_scanner, daemon=True).start()

    # 2. Start Virtual Camera
    try:
        # Windows: Automatically finds 'OBS Virtual Camera' or similar
        print("🎥 initializing Virtual Camera...")

        # NOTE: We use PixelFormat.RGB because that's what pyvirtualcam expects generally.
        # We will convert BGR -> RGB before sending.
        with pyvirtualcam.Camera(width=WIDTH, height=HEIGHT, fps=FPS, fmt=PixelFormat.RGB) as vcam:
            print(f"✅ Virtual Camera Started: {vcam.device}")
            print(f"👉 Select '{vcam.device}' in Zoom/Discord/Teams")

            # Create Windows
            cv2.namedWindow("Preview", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Preview", int(WIDTH * PREVIEW_SCALE), int(HEIGHT * PREVIEW_SCALE))

            if state.show_ui:
                cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)

            while True:
                # A. Prepare Frame
                final_bgr = create_output_frame()

                # B. Send to Virtual Camera (Convert to RGB)
                final_rgb = cv2.cvtColor(final_bgr, cv2.COLOR_BGR2RGB)
                vcam.send(final_rgb)

                # C. Local Display (Preview)
                preview = cv2.resize(final_bgr, (int(WIDTH * PREVIEW_SCALE), int(HEIGHT * PREVIEW_SCALE)))
                cv2.imshow("Preview", preview)

                # D. Local Display (UI)
                if state.show_ui:
                    ui_frame = create_ui_display()
                    cv2.imshow("Controls", ui_frame)
                else:
                    try:
                        cv2.destroyWindow("Controls")
                    except:
                        pass

                # E. Handle Controls
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q'):
                    break
                elif key == ord('l'):  # Layout
                    state.layout_mode = (state.layout_mode + 1) % 3
                elif key == ord('m'):  # Mirror
                    state.mirror = not state.mirror
                elif key == ord('r'):  # Rotate
                    state.rotate_selected()
                elif key == ord('1'):  # Select Cam 1
                    state.selected_cam = 0
                elif key == ord('2'):  # Select Cam 2
                    state.selected_cam = 1
                elif key == ord('h'):  # Hide UI
                    state.show_ui = not state.show_ui
                    if state.show_ui: cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)

                vcam.sleep_until_next_frame()

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("💡 Make sure OBS Studio is installed and restarted.")
        print("💡 pip install pyvirtualcam")

    cv2.destroyAllWindows()
    print("👋 Done.")


if __name__ == "__main__":
    main()