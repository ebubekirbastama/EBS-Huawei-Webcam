import customtkinter as ctk
import subprocess
import threading
import queue
import os
import time
import re
import socket
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, filedialog

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    import pyvirtualcam
except ImportError:
    pyvirtualcam = None


APP_NAME = "EBS Camera Receiver PRO"
VIDEO_PORT = 27183
CONTROL_PORT = 27184
WIDTH = 1920
HEIGHT = 1080
FPS = 30


class EBSReceiver(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1380x900")
        self.minsize(1120, 760)

        ctk.set_appearance_mode("dark")

        self.adb_path = r"C:\adb\adb.exe"
        self.ffmpeg_path = r"C:\ffmpeg.exe"

        self.frame_queue = queue.Queue(maxsize=2)
        self.record_queue = queue.Queue(maxsize=4)

        self.decoder_process = None
        self.running_stream = False
        self.supervisor_running = False
        self.manual_stop = False

        self.cached_wifi_ip = ""
        self.active_transport = "YOK"

        self.control_socket = None
        self.control_lock = threading.Lock()
        self.control_stop = threading.Event()

        self.phone_orientation = "LANDSCAPE"
        self.zoom_value = 1.0
        self.max_zoom = 1.0

        self.virtual_cam = None
        self.virtual_cam_enabled = False

        self.record_process = None
        self.recording = False
        self.recording_audio = False
        self.record_thread = None
        self.record_file = ""

        self.current_photo = None

        # Performans modu: sadece Virtual Camera çıkışı.
        self.virtual_only_mode = False

        self.build_ui()
        self.after(20, self.ui_frame_loop)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ============================================================
    # UI
    # ============================================================
    def build_ui(self):
        header = ctk.CTkFrame(self, corner_radius=16)
        header.pack(fill="x", padx=18, pady=(18, 10))

        ctk.CTkLabel(
            header,
            text="EBS CAMERA RECEIVER PRO",
            font=("Roboto", 28, "bold")
        ).pack(pady=(14, 2))

        ctk.CTkLabel(
            header,
            text="USB / Wi-Fi • Otomatik yön • Zoom • Sesli/Sessiz kayıt",
            font=("Roboto", 14)
        ).pack(pady=(0, 14))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=8)

        left = ctk.CTkScrollableFrame(body, width=390, corner_radius=14)
        left.pack(side="left", fill="y", padx=(0, 10))

        right = ctk.CTkFrame(body, corner_radius=14)
        right.pack(side="left", fill="both", expand=True)

        self.status_label = ctk.CTkLabel(
            left,
            text="Durum: Hazır",
            font=("Roboto", 15, "bold")
        )
        self.status_label.pack(pady=(14, 4), padx=12)

        self.transport_label = ctk.CTkLabel(
            left,
            text="Bağlantı: YOK",
            font=("Consolas", 12, "bold")
        )
        self.transport_label.pack(pady=2, padx=12)

        self.orientation_label = ctk.CTkLabel(
            left,
            text="Kamera yönü: YATAY",
            font=("Roboto", 14, "bold")
        )
        self.orientation_label.pack(pady=2, padx=12)

        self.wifi_label = ctk.CTkLabel(
            left,
            text="Telefon Wi-Fi IP: öğrenilmedi",
            font=("Consolas", 11)
        )
        self.wifi_label.pack(pady=(2, 10), padx=12)

        self.adb_entry = self.row(left, "ADB", self.adb_path)
        self.ffmpeg_entry = self.row(left, "FFmpeg", self.ffmpeg_path)
        self.video_port_entry = self.row(left, "Video Port", str(VIDEO_PORT))
        self.control_port_entry = self.row(left, "Kontrol Port", str(CONTROL_PORT))
        self.width_entry = self.row(left, "Genişlik", str(WIDTH))
        self.height_entry = self.row(left, "Yükseklik", str(HEIGHT))
        self.fps_entry = self.row(left, "FPS", str(FPS))

        ctk.CTkLabel(
            left,
            text="BAĞLANTI",
            font=("Roboto", 13, "bold")
        ).pack(pady=(16, 4))

        self.prepare_btn = ctk.CTkButton(
            left,
            text="1. BAĞLANTIYI HAZIRLA",
            command=self.prepare_connection
        )
        self.prepare_btn.pack(fill="x", padx=16, pady=5)

        self.start_btn = ctk.CTkButton(
            left,
            text="2. AUTO RECEIVER BAŞLAT",
            command=self.start_receiver
        )
        self.start_btn.pack(fill="x", padx=16, pady=5)

        self.stop_btn = ctk.CTkButton(
            left,
            text="RECEIVER DURDUR",
            command=self.stop_receiver
        )
        self.stop_btn.pack(fill="x", padx=16, pady=5)

        self.auto_switch = ctk.CTkSwitch(
            left,
            text="USB → Wi-Fi otomatik geçiş"
        )
        self.auto_switch.select()
        self.auto_switch.pack(padx=16, pady=(10, 6), anchor="w")

        self.turbo_switch = ctk.CTkSwitch(
            left,
            text="USB Turbo / düşük gecikme"
        )
        self.turbo_switch.select()
        self.turbo_switch.pack(padx=16, pady=6, anchor="w")

        ctk.CTkLabel(
            left,
            text="KAMERA ZOOM",
            font=("Roboto", 13, "bold")
        ).pack(pady=(16, 4))

        self.zoom_text = ctk.CTkLabel(
            left,
            text="Zoom: 1.00x / 1.00x",
            font=("Consolas", 12, "bold")
        )
        self.zoom_text.pack(pady=3)

        self.zoom_slider = ctk.CTkSlider(
            left,
            from_=1.0,
            to=2.0,
            number_of_steps=100,
            command=self.on_zoom_slider
        )
        self.zoom_slider.set(1.0)
        self.zoom_slider.pack(fill="x", padx=18, pady=6)

        zoom_btns = ctk.CTkFrame(left, fg_color="transparent")
        zoom_btns.pack(fill="x", padx=16, pady=4)

        ctk.CTkButton(
            zoom_btns,
            text="−",
            width=70,
            command=lambda: self.change_zoom(-0.25)
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            zoom_btns,
            text="1x",
            width=70,
            command=lambda: self.set_zoom(1.0)
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            zoom_btns,
            text="+",
            width=70,
            command=lambda: self.change_zoom(0.25)
        ).pack(side="left", padx=4)

        ctk.CTkLabel(
            left,
            text="KAYIT",
            font=("Roboto", 13, "bold")
        ).pack(pady=(16, 4))

        recdir_default = str(Path.home() / "Videos" / "EBS_Recordings")
        self.record_dir_entry = self.row(left, "Kayıt", recdir_default)

        ctk.CTkButton(
            left,
            text="KAYIT KLASÖRÜ SEÇ",
            command=self.choose_record_dir
        ).pack(fill="x", padx=16, pady=5)

        self.audio_combo = ctk.CTkComboBox(
            left,
            values=["Ses cihazı taranmadı"]
        )
        self.audio_combo.pack(fill="x", padx=16, pady=5)

        ctk.CTkButton(
            left,
            text="SES CİHAZLARINI TARA",
            command=self.scan_audio_devices
        ).pack(fill="x", padx=16, pady=5)

        rec_btns = ctk.CTkFrame(left, fg_color="transparent")
        rec_btns.pack(fill="x", padx=16, pady=5)

        ctk.CTkButton(
            rec_btns,
            text="SESSİZ KAYIT",
            command=lambda: self.start_recording(False),
            width=160
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            rec_btns,
            text="SESLİ KAYIT",
            command=lambda: self.start_recording(True),
            width=160
        ).pack(side="left", padx=3)

        self.record_stop_btn = ctk.CTkButton(
            left,
            text="KAYDI DURDUR",
            command=self.stop_recording
        )
        self.record_stop_btn.pack(fill="x", padx=16, pady=5)

        self.record_status = ctk.CTkLabel(
            left,
            text="Kayıt: Kapalı",
            font=("Consolas", 11, "bold")
        )
        self.record_status.pack(pady=4)

        ctk.CTkLabel(
            left,
            text="ÇALIŞMA MODU",
            font=("Roboto", 13, "bold")
        ).pack(pady=(16, 4))

        self.virtual_only_switch = ctk.CTkSwitch(
            left,
            text="SADECE VIRTUAL CAMERA",
            command=self.toggle_virtual_only_mode
        )
        self.virtual_only_switch.pack(
            padx=16,
            pady=(4, 8),
            anchor="w"
        )

        self.mode_label = ctk.CTkLabel(
            left,
            text="Mod: TAM ÖZELLİK",
            font=("Consolas", 11, "bold")
        )
        self.mode_label.pack(
            padx=16,
            pady=(0, 6),
            anchor="w"
        )

        ctk.CTkLabel(
            left,
            text="SANAL KAMERA",
            font=("Roboto", 13, "bold")
        ).pack(pady=(10, 4))

        self.vcam_switch = ctk.CTkSwitch(
            left,
            text="Virtual Camera çıkışı",
            command=self.toggle_virtual_cam
        )
        self.vcam_switch.pack(padx=16, pady=6, anchor="w")

        self.backend_label = ctk.CTkLabel(
            left,
            text="VirtualCam: kontrol edilmedi",
            wraplength=340,
            justify="left",
            font=("Consolas", 11)
        )
        self.backend_label.pack(padx=16, pady=4, anchor="w")

        self.log_box = ctk.CTkTextbox(
            left,
            height=220,
            font=("Consolas", 11)
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=12)

        self.preview_label = ctk.CTkLabel(
            right,
            text="Kamera görüntüsü bekleniyor...",
            font=("Roboto", 18)
        )
        self.preview_label.pack(fill="both", expand=True, padx=12, pady=12)

        self.log("EBS Camera Receiver PRO hazır.\n")
        self.log(f"FFmpeg varsayılan: {self.ffmpeg_path}\n")
        self.check_virtualcam()

    def row(self, parent, label, value):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(
            frame,
            text=label,
            width=82,
            anchor="w"
        ).pack(side="left")

        entry = ctk.CTkEntry(frame)
        entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def log(self, text):
        self.after(0, lambda: self._log(text))

    def _log(self, text):
        self.log_box.insert("end", text)
        self.log_box.see("end")

    def set_status(self, text):
        self.after(
            0,
            lambda: self.status_label.configure(
                text=f"Durum: {text}"
            )
        )

    def set_transport(self, mode, host=""):
        self.active_transport = mode

        text = f"Bağlantı: {mode}"
        if host:
            text += f" ({host})"

        self.after(
            0,
            lambda: self.transport_label.configure(text=text)
        )

    # ============================================================
    # ADB / WI-FI
    # ============================================================
    def adb_devices(self):
        adb = self.adb_entry.get().strip()

        if not os.path.isfile(adb):
            return False, ""

        try:
            p = subprocess.run(
                [adb, "devices"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=4
            )

            return "\tdevice" in p.stdout, p.stdout

        except Exception:
            return False, ""

    def learn_wifi_ip(self):
        adb = self.adb_entry.get().strip()

        try:
            p = subprocess.run(
                [
                    adb,
                    "shell",
                    "ip",
                    "-f",
                    "inet",
                    "addr",
                    "show",
                    "wlan0"
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=4
            )

            match = re.search(
                r"inet\s+(\d+\.\d+\.\d+\.\d+)/",
                p.stdout
            )

            if not match:
                p = subprocess.run(
                    [adb, "shell", "ip", "route"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    timeout=4
                )

                match = re.search(
                    r"\bsrc\s+(\d+\.\d+\.\d+\.\d+)",
                    p.stdout
                )

            if match:
                self.cached_wifi_ip = match.group(1)

                self.after(
                    0,
                    lambda: self.wifi_label.configure(
                        text=f"Telefon Wi-Fi IP: {self.cached_wifi_ip}"
                    )
                )

                self.log(
                    f"[WIFI] Telefon IP: {self.cached_wifi_ip}\n"
                )

        except Exception as exc:
            self.log(f"[WIFI] IP öğrenme hatası: {exc}\n")

        return self.cached_wifi_ip

    def configure_adb_forward(self):
        adb = self.adb_entry.get().strip()
        video_port = self.video_port_entry.get().strip()
        control_port = self.control_port_entry.get().strip()

        try:
            subprocess.run(
                [adb, "forward", "--remove-all"],
                capture_output=True,
                text=True,
                timeout=4
            )

            for port in (video_port, control_port):
                subprocess.run(
                    [adb, "forward", f"tcp:{port}", f"tcp:{port}"],
                    capture_output=True,
                    text=True,
                    timeout=4
                )

            p = subprocess.run(
                [adb, "forward", "--list"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=4
            )

            ok = (
                f"tcp:{video_port}" in p.stdout and
                f"tcp:{control_port}" in p.stdout
            )

            if ok:
                self.log(
                    "[USB] Video + kontrol portları hazır.\n"
                )

            return ok

        except Exception as exc:
            self.log(f"[USB] Forward hatası: {exc}\n")
            return False

    def prepare_connection(self):
        threading.Thread(
            target=self._prepare_connection_worker,
            daemon=True
        ).start()

    def _prepare_connection_worker(self):
        connected, output = self.adb_devices()

        self.log("\n> adb devices\n")
        self.log(output)

        if not connected:
            self.log(
                "[HATA] İlk hazırlıkta telefon USB/ADB ile bağlı olmalı.\n"
            )
            return

        self.learn_wifi_ip()

        if self.configure_adb_forward():
            self.set_transport("USB", "127.0.0.1")
            self.set_status("USB hazır")

    def choose_transport(self):
        usb, _ = self.adb_devices()

        if usb:
            self.learn_wifi_ip()

            if self.configure_adb_forward():
                return "127.0.0.1", "USB"

        if self.auto_switch.get() and self.cached_wifi_ip:
            return self.cached_wifi_ip, "WIFI"

        return "", "YOK"

    # ============================================================
    # CONTROL CHANNEL: orientation + zoom
    # ============================================================
    def start_control_channel(self, host):
        self.stop_control_channel()
        self.control_stop.clear()

        threading.Thread(
            target=self.control_loop,
            args=(host,),
            daemon=True
        ).start()

    def control_loop(self, host):
        try:
            port = int(self.control_port_entry.get())

            sock = socket.create_connection(
                (host, port),
                timeout=4
            )

            sock.settimeout(1.2)

            with self.control_lock:
                self.control_socket = sock

            fileobj = sock.makefile(
                "r",
                encoding="utf-8",
                errors="ignore"
            )

            self.log(
                f"[CONTROL] Bağlandı: {host}:{port}\n"
            )

            self.send_control("GET_STATE")

            while not self.control_stop.is_set():
                try:
                    line = fileobj.readline()

                    if not line:
                        break

                    self.parse_control_state(line.strip())

                except socket.timeout:
                    try:
                        self.send_control("GET_STATE")
                    except Exception:
                        break

        except Exception as exc:
            self.log(f"[CONTROL] Bağlantı yok: {exc}\n")

        finally:
            with self.control_lock:
                try:
                    if self.control_socket:
                        self.control_socket.close()
                except Exception:
                    pass

                self.control_socket = None

    def stop_control_channel(self):
        self.control_stop.set()

        with self.control_lock:
            try:
                if self.control_socket:
                    self.control_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass

            try:
                if self.control_socket:
                    self.control_socket.close()
            except Exception:
                pass

            self.control_socket = None

    def send_control(self, command):
        with self.control_lock:
            if not self.control_socket:
                return False

            self.control_socket.sendall(
                (command.strip() + "\n").encode("utf-8")
            )

            return True

    def parse_control_state(self, line):
        if not line.startswith("STATE "):
            return

        values = {}

        for token in line[6:].split():
            if "=" in token:
                key, value = token.split("=", 1)
                values[key] = value

        orientation = values.get(
            "orientation",
            self.phone_orientation
        )

        self.phone_orientation = orientation.upper()

        try:
            self.zoom_value = float(
                values.get("zoom", self.zoom_value)
            )
        except Exception:
            pass

        try:
            self.max_zoom = max(
                1.0,
                float(values.get("maxZoom", self.max_zoom))
            )
        except Exception:
            pass

        orientation_tr = (
            "DİKEY"
            if self.phone_orientation == "PORTRAIT"
            else "YATAY"
        )

        def update_ui():
            self.orientation_label.configure(
                text=f"Kamera yönü: {orientation_tr}"
            )

            self.zoom_text.configure(
                text=(
                    f"Zoom: {self.zoom_value:.2f}x / "
                    f"{self.max_zoom:.2f}x"
                )
            )

            self.zoom_slider.configure(
                from_=1.0,
                to=max(1.01, self.max_zoom)
            )

            self.zoom_slider.set(
                min(self.zoom_value, self.max_zoom)
            )

        self.after(0, update_ui)

    def on_zoom_slider(self, value):
        if self.virtual_only_mode:
            return

        self.zoom_value = float(value)

        self.zoom_text.configure(
            text=(
                f"Zoom: {self.zoom_value:.2f}x / "
                f"{self.max_zoom:.2f}x"
            )
        )

        self.send_control(
            f"ZOOM {self.zoom_value:.2f}"
        )

    def set_zoom(self, value):
        if self.virtual_only_mode:
            return

        value = max(
            1.0,
            min(float(value), self.max_zoom)
        )

        self.zoom_value = value
        self.zoom_slider.set(value)

        self.zoom_text.configure(
            text=(
                f"Zoom: {value:.2f}x / "
                f"{self.max_zoom:.2f}x"
            )
        )

        self.send_control(
            f"ZOOM {value:.2f}"
        )

    def change_zoom(self, delta):
        self.set_zoom(
            self.zoom_value + delta
        )

    # ============================================================
    # Receiver supervisor
    # ============================================================
    def start_receiver(self):
        if self.supervisor_running:
            return

        if (
            self.virtual_only_mode and
            not self.virtual_cam_enabled
        ):
            self.vcam_switch.select()
            self.enable_virtual_cam()

            if not self.virtual_cam_enabled:
                messagebox.showerror(
                    APP_NAME,
                    "Sadece Virtual Camera modu için sanal kamera backend'i açılamadı."
                )
                return

        if Image is None or np is None:
            messagebox.showerror(
                APP_NAME,
                "Pillow veya NumPy eksik."
            )
            return

        ffmpeg = self.ffmpeg_entry.get().strip()

        if not os.path.isfile(ffmpeg):
            messagebox.showerror(
                APP_NAME,
                f"FFmpeg bulunamadı:\n{ffmpeg}"
            )
            return

        self.manual_stop = False
        self.supervisor_running = True

        threading.Thread(
            target=self.supervisor_loop,
            daemon=True
        ).start()

    def supervisor_loop(self):
        self.log(
            "\n[AUTO] Bağlantı yöneticisi başlatıldı.\n"
        )

        while not self.manual_stop:
            host, mode = self.choose_transport()

            if not host:
                self.set_transport("BEKLENİYOR")
                self.set_status("Telefon bekleniyor")
                time.sleep(1.5)
                continue

            self.set_transport(mode, host)
            self.start_control_channel(host)

            self.log(
                f"[AUTO] {mode}: {host}:"
                f"{self.video_port_entry.get()}\n"
            )

            self.run_decoder_blocking(host)
            self.stop_control_channel()

            if self.manual_stop:
                break

            self.log(
                "[AUTO] Akış koptu; alternatif bağlantı aranıyor...\n"
            )

            self.set_status("Yeniden bağlanıyor")

            # USB yeniden bağlantısı Wi-Fi'den daha hızlı denenir.
            time.sleep(
                0.15
                if self.active_transport == "USB"
                else 0.60
            )

        self.supervisor_running = False
        self.set_transport("DURDU")
        self.set_status("Durduruldu")

    def run_decoder_blocking(self, host):
        try:
            width = int(self.width_entry.get())
            height = int(self.height_entry.get())
            fps = int(self.fps_entry.get())
            port = int(self.video_port_entry.get())
        except ValueError:
            self.log("[HATA] Video ayarları geçersiz.\n")
            self.manual_stop = True
            return

        ffmpeg = self.ffmpeg_entry.get().strip()

        # ========================================================
        # LEGACY FAST CORE
        # Kullanıcının eski 1080p'de çok akıcı çalışan Receiver'ındaki
        # FFmpeg parametreleri ve pipe buffer birebir korunur.
        # ========================================================
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "warning",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-probesize", "32",
            "-analyzeduration", "0",
            "-f", "h264",
            "-i", f"tcp://{host}:{port}?timeout=4000000",
            "-an",
            "-pix_fmt", "rgb24",
            "-f", "rawvideo",
            "pipe:1"
        ]

        self.log("[FFMPEG] LEGACY FAST 1080p çekirdeği başlatılıyor.\n")

        try:
            self.decoder_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**7,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                )
            )
        except Exception as exc:
            self.log(f"[FFMPEG HATASI] {exc}\n")
            return

        self.running_stream = True
        frame_size = width * height * 3
        decoder_started_at = time.perf_counter()
        first_frame_logged = False
        perf_frame_count = 0
        perf_started_at = time.perf_counter()
        last_status_update = 0.0

        threading.Thread(
            target=self.stderr_loop,
            args=(self.decoder_process,),
            daemon=True
        ).start()

        got_frame = False

        try:
            while (
                not self.manual_stop and
                self.decoder_process and
                self.decoder_process.poll() is None
            ):
                raw = self.read_exact(
                    self.decoder_process.stdout,
                    frame_size
                )

                if raw is None:
                    break

                raw_frame = np.frombuffer(
                    raw,
                    dtype=np.uint8
                ).reshape(
                    (height, width, 3)
                ).copy()

                got_frame = True
                perf_frame_count += 1

                if not first_frame_logged:
                    first_frame_logged = True
                    startup_ms = (
                        time.perf_counter() - decoder_started_at
                    ) * 1000.0
                    self.log(
                        f"[LATENCY] İlk görüntü {startup_ms:.0f} ms içinde geldi.\n"
                    )

                # Her 2 saniyede gerçek decode FPS ölç.
                perf_now = time.perf_counter()
                perf_elapsed = perf_now - perf_started_at

                if perf_elapsed >= 2.0:
                    measured_fps = perf_frame_count / perf_elapsed
                    self.log(
                        f"[PERF] Gerçek decode FPS: {measured_fps:.1f}\n"
                    )
                    perf_frame_count = 0
                    perf_started_at = perf_now

                # Virtual-only modunda preview kuyruğuna hiç dokunma.
                if not self.virtual_only_mode:
                    preview_frame = self.make_preview_frame(
                        raw_frame
                    )

                    try:
                        while self.frame_queue.qsize() >= 1:
                            self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass

                    try:
                        self.frame_queue.put_nowait(
                            preview_frame
                        )
                    except queue.Full:
                        pass

                # Eski hızlı yolda landscape görüntü aynı RGB frame'dir.
                # Yalnızca virtual camera veya kayıt gerektiğinde output hazırlanır.
                output_frame = None

                if self.virtual_cam_enabled or self.recording:
                    output_frame = self.make_output_frame(
                        raw_frame,
                        width,
                        height
                    )

                if (
                    self.virtual_cam_enabled and
                    self.virtual_cam is not None and
                    output_frame is not None
                ):
                    try:
                        self.virtual_cam.send(
                            output_frame
                        )
                    except Exception as exc:
                        self.log(
                            f"[VCAM] Gönderme hatası: {exc}\n"
                        )

                if (
                    self.recording and
                    output_frame is not None
                ):
                    try:
                        if self.record_queue.full():
                            self.record_queue.get_nowait()

                        self.record_queue.put_nowait(
                            output_frame.copy()
                        )
                    except Exception:
                        pass

                # Tk GUI'yi 30 kez/sn güncellemek yerine 4 kez/sn.
                if perf_now - last_status_update >= 0.25:
                    last_status_update = perf_now

                    orientation_tr = (
                        "DİKEY"
                        if self.phone_orientation == "PORTRAIT"
                        else "YATAY"
                    )

                    if not self.virtual_only_mode:
                        self.set_status(
                            f"Canlı • {self.active_transport} • "
                            f"{orientation_tr} • "
                            f"Zoom {self.zoom_value:.2f}x"
                        )
                    else:
                        self.set_status(
                            f"Virtual Camera • {self.active_transport}"
                        )

        finally:
            self.running_stream = False

            p = self.decoder_process
            self.decoder_process = None

            if p:
                try:
                    p.terminate()
                except Exception:
                    pass

                try:
                    p.wait(timeout=1)
                except Exception:
                    try:
                        p.kill()
                    except Exception:
                        pass

            if not got_frame:
                self.log(
                    f"[AUTO] {host} adresinden görüntü alınamadı.\n"
                )

    def make_preview_frame(self, frame):
        if self.phone_orientation == "PORTRAIT":
            return np.rot90(
                frame,
                k=3
            ).copy()

        return frame

    def make_output_frame(self, frame, width, height):
        """
        Virtual camera ve kayıt için boyut sabit kalır.
        Telefon dikeyse görüntü döndürülür ve 16:9 canvas içine letterbox edilir.
        """
        if self.phone_orientation != "PORTRAIT":
            return frame

        rotated = np.rot90(
            frame,
            k=3
        ).copy()

        rh, rw = rotated.shape[:2]

        scale = min(
            width / rw,
            height / rh
        )

        new_w = max(
            1,
            int(rw * scale)
        )
        new_h = max(
            1,
            int(rh * scale)
        )

        pil = Image.fromarray(rotated)
        pil = pil.resize(
            (new_w, new_h),
            Image.Resampling.BILINEAR
        )

        canvas = np.zeros(
            (height, width, 3),
            dtype=np.uint8
        )

        x = (width - new_w) // 2
        y = (height - new_h) // 2

        canvas[
            y:y + new_h,
            x:x + new_w
        ] = np.asarray(pil)

        return canvas

    @staticmethod
    def read_exact(pipe, size):
        if pipe is None:
            return None

        data = bytearray()

        while len(data) < size:
            chunk = pipe.read(
                size - len(data)
            )

            if not chunk:
                return None

            data.extend(chunk)

        return bytes(data)

    def stderr_loop(self, proc):
        if not proc.stderr:
            return

        while (
            not self.manual_stop and
            proc.poll() is None
        ):
            line = proc.stderr.readline()

            if not line:
                break

            text = line.decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if text:
                # Ham H.264'te frame-rate tahmin uyarısı decode hatası değildir.
                # UI logunu kirletmemesi için yalnızca bu benign uyarıyı gizle.
                if "not enough frames to estimate rate" in text:
                    continue

                self.log(
                    "[FFMPEG] " + text + "\n"
                )

    # ============================================================
    # Preview
    # ============================================================
    def ui_frame_loop(self):
        if self.virtual_only_mode:
            # Önizleme çizimi yok; CPU/GPU ve Tk image allocation yapılmaz.
            self.after(
                100,
                self.ui_frame_loop
            )
            return

        try:
            frame = self.frame_queue.get_nowait()

            preview = Image.fromarray(frame)
            preview.thumbnail((900, 720))

            image = ctk.CTkImage(
                light_image=preview,
                dark_image=preview,
                size=preview.size
            )

            self.current_photo = image

            self.preview_label.configure(
                image=image,
                text=""
            )

        except queue.Empty:
            pass
        except Exception as exc:
            self.log(
                f"[PREVIEW HATASI] {exc}\n"
            )

        self.after(
            20,
            self.ui_frame_loop
        )

    # ============================================================
    # Recording
    # ============================================================
    def choose_record_dir(self):
        if self.feature_blocked_in_virtual_only("Kayıt klasörü"):
            return

        path = filedialog.askdirectory()

        if path:
            self.record_dir_entry.delete(
                0,
                "end"
            )

            self.record_dir_entry.insert(
                0,
                path
            )

    def scan_audio_devices(self):
        if self.feature_blocked_in_virtual_only("Ses cihazı tarama"):
            return

        threading.Thread(
            target=self._scan_audio_worker,
            daemon=True
        ).start()

    def _scan_audio_worker(self):
        ffmpeg = self.ffmpeg_entry.get().strip()

        if not os.path.isfile(ffmpeg):
            self.log("[AUDIO] FFmpeg bulunamadı.\n")
            return

        command = [
            ffmpeg,
            "-hide_banner",
            "-list_devices",
            "true",
            "-f",
            "dshow",
            "-i",
            "dummy"
        ]

        try:
            p = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=12
            )

            text = (
                (p.stdout or "") +
                "\n" +
                (p.stderr or "")
            )

            devices = re.findall(
                r'"([^"]+)"\s+\(audio\)',
                text,
                flags=re.IGNORECASE
            )

            unique = []

            for device in devices:
                if device not in unique:
                    unique.append(device)

            if unique:
                self.after(
                    0,
                    lambda: self.audio_combo.configure(
                        values=unique
                    )
                )

                self.after(
                    0,
                    lambda: self.audio_combo.set(
                        unique[0]
                    )
                )

                self.log(
                    "[AUDIO] Ses cihazları: " +
                    ", ".join(unique) +
                    "\n"
                )
            else:
                self.log(
                    "[AUDIO] DirectShow mikrofon bulunamadı.\n"
                )

        except Exception as exc:
            self.log(
                f"[AUDIO] Tarama hatası: {exc}\n"
            )

    def start_recording(self, with_audio):
        if self.feature_blocked_in_virtual_only("Video kayıt"):
            return

        if self.recording:
            messagebox.showinfo(
                APP_NAME,
                "Zaten kayıt yapılıyor."
            )
            return

        if not self.running_stream:
            messagebox.showwarning(
                APP_NAME,
                "Önce kamera akışını başlat."
            )
            return

        ffmpeg = self.ffmpeg_entry.get().strip()

        if not os.path.isfile(ffmpeg):
            messagebox.showerror(
                APP_NAME,
                f"FFmpeg bulunamadı:\n{ffmpeg}"
            )
            return

        try:
            width = int(self.width_entry.get())
            height = int(self.height_entry.get())
            fps = int(self.fps_entry.get())
        except ValueError:
            return

        record_dir = Path(
            self.record_dir_entry.get().strip()
        )

        record_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        stamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        suffix = (
            "sesli"
            if with_audio
            else "sessiz"
        )

        output_file = record_dir / (
            f"EBS_{stamp}_{suffix}.mp4"
        )

        command = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{width}x{height}",
            "-r",
            str(fps),
            "-i",
            "pipe:0"
        ]

        if with_audio:
            device = self.audio_combo.get().strip()

            if (
                not device or
                device == "Ses cihazı taranmadı"
            ):
                messagebox.showwarning(
                    APP_NAME,
                    "Önce SES CİHAZLARINI TARA ve mikrofon seç."
                )
                return

            command += [
                "-f",
                "dshow",
                "-i",
                f'audio={device}',
                "-c:a",
                "aac",
                "-b:a",
                "160k"
            ]
        else:
            command += ["-an"]

        command += [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p"
        ]

        if with_audio:
            command += ["-shortest"]

        command += [str(output_file)]

        try:
            self.record_process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                )
            )

            self.recording = True
            self.recording_audio = with_audio
            self.record_file = str(output_file)

            self.record_thread = threading.Thread(
                target=self.record_writer_loop,
                daemon=True
            )

            self.record_thread.start()

            self.after(
                0,
                lambda: self.record_status.configure(
                    text=(
                        "Kayıt: SESLİ"
                        if with_audio
                        else "Kayıt: SESSİZ"
                    )
                )
            )

            self.log(
                f"[REC] Kayıt başladı: {output_file}\n"
            )

        except Exception as exc:
            self.recording = False
            self.record_process = None

            self.log(
                f"[REC HATASI] {exc}\n"
            )

    def record_writer_loop(self):
        while self.recording:
            try:
                frame = self.record_queue.get(
                    timeout=0.5
                )
            except queue.Empty:
                continue

            p = self.record_process

            if (
                p is None or
                p.stdin is None or
                p.poll() is not None
            ):
                break

            try:
                p.stdin.write(
                    frame.tobytes()
                )
            except Exception:
                break

    def stop_recording(self):
        if not self.recording:
            return

        self.recording = False

        p = self.record_process
        self.record_process = None

        if p:
            try:
                if p.stdin:
                    p.stdin.close()
            except Exception:
                pass

            try:
                p.wait(timeout=8)
            except Exception:
                try:
                    p.terminate()
                except Exception:
                    pass

        while not self.record_queue.empty():
            try:
                self.record_queue.get_nowait()
            except queue.Empty:
                break

        self.after(
            0,
            lambda: self.record_status.configure(
                text="Kayıt: Kapalı"
            )
        )

        self.log(
            f"[REC] Kayıt tamamlandı: {self.record_file}\n"
        )

    # ============================================================
    # PERFORMANCE / VIRTUAL-ONLY MODE
    # ============================================================
    def toggle_virtual_only_mode(self):
        self.virtual_only_mode = bool(
            self.virtual_only_switch.get()
        )

        if self.virtual_only_mode:
            self.mode_label.configure(
                text="Mod: SADECE VIRTUAL CAMERA"
            )

            # Kayıt açıksa kapat.
            if self.recording:
                self.stop_recording()

            # Virtual Camera otomatik açılır.
            if not self.virtual_cam_enabled:
                self.vcam_switch.select()
                self.enable_virtual_cam()

            self.preview_label.configure(
                image=None,
                text=(
                    "SADECE VIRTUAL CAMERA MODU\n\n"
                    "Önizleme kapalı • Kayıt kapalı • Zoom kontrolü kapalı\n"
                    "Minimum PC yükü"
                )
            )
            self.current_photo = None

            # Beklemiş preview framelerini boşalt.
            try:
                while True:
                    self.frame_queue.get_nowait()
            except queue.Empty:
                pass

            self.log(
                "[PERF] Sadece Virtual Camera modu aktif.\n"
                "[PERF] Preview, kayıt ve gereksiz frame kopyaları kapatıldı.\n"
            )

        else:
            self.mode_label.configure(
                text="Mod: TAM ÖZELLİK"
            )

            self.preview_label.configure(
                image=None,
                text="Kamera görüntüsü bekleniyor..."
            )

            self.log(
                "[PERF] Tam özellik modu aktif.\n"
            )

    def feature_blocked_in_virtual_only(self, feature_name):
        if not self.virtual_only_mode:
            return False

        self.log(
            f"[PERF] {feature_name}, Sadece Virtual Camera modunda kapalı.\n"
        )
        return True

    # ============================================================
    # Virtual Camera
    # ============================================================
    def check_virtualcam(self):
        if pyvirtualcam is None:
            self.backend_label.configure(
                text="VirtualCam: pyvirtualcam kurulu değil"
            )
        else:
            self.backend_label.configure(
                text="VirtualCam: pyvirtualcam hazır"
            )

    def toggle_virtual_cam(self):
        if self.vcam_switch.get():
            self.enable_virtual_cam()
        else:
            self.disable_virtual_cam()

    def enable_virtual_cam(self):
        if pyvirtualcam is None:
            self.log(
                "[VCAM] pyvirtualcam kurulu değil.\n"
            )
            self.vcam_switch.deselect()
            return

        try:
            width = int(self.width_entry.get())
            height = int(self.height_entry.get())
            fps = int(self.fps_entry.get())

            self.virtual_cam = pyvirtualcam.Camera(
                width=width,
                height=height,
                fps=fps,
                fmt=pyvirtualcam.PixelFormat.RGB
            )

            self.virtual_cam_enabled = True

            self.backend_label.configure(
                text=f"VirtualCam: {self.virtual_cam.device}"
            )

            self.log(
                f"[VCAM] Aktif: {self.virtual_cam.device}\n"
            )

        except Exception as exc:
            self.virtual_cam_enabled = False
            self.virtual_cam = None
            self.vcam_switch.deselect()

            self.log(
                f"[VCAM HATASI] {exc}\n"
            )

    def disable_virtual_cam(self):
        self.virtual_cam_enabled = False

        if self.virtual_cam is not None:
            try:
                self.virtual_cam.close()
            except Exception:
                pass

        self.virtual_cam = None

    # ============================================================
    # Stop
    # ============================================================
    def stop_receiver(self):
        self.manual_stop = True
        self.running_stream = False

        self.stop_control_channel()
        self.stop_recording()

        p = self.decoder_process
        self.decoder_process = None

        if p:
            try:
                p.terminate()
            except Exception:
                pass

            try:
                p.wait(timeout=1)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

        self.disable_virtual_cam()
        self.set_status("Durduruldu")
        self.log("[STOP] Receiver durduruldu.\n")

    def on_close(self):
        self.stop_receiver()
        self.destroy()


if __name__ == "__main__":
    app = EBSReceiver()
    app.mainloop()
