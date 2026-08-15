# 📱 EBS Huawei Webcam

<div align="center">

**Huawei / Android telefonunuzu USB veya Wi-Fi üzerinden düşük gecikmeli bir PC web kamerasına dönüştürün.**

`Android APK` • `Python Receiver` • `ADB` • `FFmpeg` • `Virtual Camera`

**Developer:** Ebubekir Bastama  
**License:** Apache License 2.0

</div>

---

## 📷 Proje Hakkında

**EBS Huawei Webcam**, uyumlu Huawei/Android telefon kamerasını Windows bilgisayarda yüksek kaliteli kamera kaynağı olarak kullanmak için geliştirilmiş bir istemci + alıcı çözümüdür.

Telefon tarafındaki Android uygulaması görüntüyü aktarır. PC tarafındaki **EBS Camera Receiver PRO** ise H.264 akışını FFmpeg ile çözer; canlı önizleme, USB/Wi-Fi bağlantısı, yön algılama, zoom, video kaydı ve sanal kamera çıkışı sağlar.

Varsayılan profil **1920×1080 / 30 FPS**'tir.

## ✨ Öne Çıkan Özellikler

- 📱 Huawei / Android telefonu PC web kamerası olarak kullanma
- 🔌 USB üzerinden ADB port forwarding
- 📶 USB kesildiğinde otomatik Wi-Fi bağlantısına geçiş
- ⚡ Düşük gecikmeli H.264 + FFmpeg görüntü aktarımı
- 🖥️ Modern CustomTkinter arayüzü
- 🎥 1920×1080 / 30 FPS varsayılan profil
- 🔄 Dikey/yatay telefon yönünü otomatik işleme
- 🔍 Uzaktan kamera zoom kontrolü
- 🎬 Sesli veya sessiz MP4 kayıt
- 🎙️ Windows DirectShow ses cihazı tarama
- 📹 `pyvirtualcam` Virtual Camera çıkışı
- 🚀 Minimum PC yükü için **Sadece Virtual Camera** modu
- 🔁 Akış koptuğunda otomatik yeniden bağlanma
- 📊 Gerçek decode FPS ve başlangıç gecikmesi logları

## 📁 Proje Dosyaları

```text
EBS-Huawei-Webcam/
├── EBS_Huawei_Webcam_Receiver.py
├── EBS-Huawei-Webcam-v3.0.apk
├── README.md
└── LICENSE
```

## 🧩 Gereksinimler

- Windows 10 / Windows 11
- Python 3.10+ önerilir
- Android Platform Tools / ADB
- FFmpeg
- USB hata ayıklaması açık Huawei/Android telefon

Python bağımlılıkları:

```bash
pip install customtkinter pillow numpy pyvirtualcam
```

> `pyvirtualcam` sanal kamera özelliği için kullanılır.

## ⚙️ Varsayılan Yollar

```text
ADB:     C:\adb\adb.exe
FFmpeg:  C:\ffmpeg.exe
```

ADB veya FFmpeg başka bir konumdaysa Receiver arayüzündeki ilgili alanlardan yolu değiştirebilirsiniz.

## 📲 Android APK Kurulumu

1. `EBS-Huawei-Webcam-v3.0.apk` dosyasını telefona aktarın.
2. Android/Huawei cihazınızda gerektiğinde **Bilinmeyen uygulamaları yükleme** iznini açın.
3. APK'yı kurun.
4. Uygulamayı çalıştırıp kamera için gerekli izinleri verin.
5. USB kullanacaksanız **Geliştirici Seçenekleri > USB hata ayıklama** özelliğini etkinleştirin.

## 🖥️ PC Receiver Kurulumu ve Kullanımı

Receiver'ı çalıştırın:

```bash
python EBS_Huawei_Webcam_Receiver.py
```

Ardından:

1. Telefonu USB ile PC'ye bağlayın.
2. Telefonda çıkan ADB/RSA yetkilendirmesini onaylayın.
3. **1. BAĞLANTIYI HAZIRLA** düğmesine basın.
4. Receiver telefonun Wi-Fi IP adresini öğrenir ve gerekli portları hazırlar.
5. **2. AUTO RECEIVER BAŞLAT** düğmesine basın.
6. Kamera akışı Receiver'a aktarılır.

## 🔌 USB ve Wi-Fi

USB bağlı olduğunda Receiver ADB üzerinden video ve kontrol portlarını PC'ye yönlendirir.

```text
Video Port:   27183
Kontrol Port: 27184
```

**USB → Wi-Fi otomatik geçiş** açıkken Receiver telefonun Wi-Fi IP'sini önceden öğrenir. USB bağlantısı kesildiğinde uygun durumda Wi-Fi üzerinden yeniden bağlanmayı dener.

> Wi-Fi kullanımında PC ve telefon aynı yerel ağda olmalıdır.

## 🔍 Zoom

Receiver telefon uygulamasının bildirdiği maksimum zoom değerine göre kontrol sağlar.

- `−` zoom azaltır.
- `1x` normal görünüme döndürür.
- `+` zoom artırır.
- Slider hassas zoom kontrolü sağlar.

## 🔄 Dikey / Yatay Görüntü

Telefon yön bilgisi kontrol kanalından Receiver'a iletilir.

- **Landscape:** görüntü doğrudan işlenir.
- **Portrait:** görüntü otomatik döndürülür.
- Virtual Camera ve kayıt sırasında dikey görüntü oranı korunarak 16:9 alana yerleştirilir.

## 🎬 Video Kayıt

### Sessiz kayıt

**SESSİZ KAYIT** ile yalnızca kamera görüntüsü MP4 olarak kaydedilir.

### Sesli kayıt

1. **SES CİHAZLARINI TARA** seçeneğine basın.
2. Mikrofonu seçin.
3. **SESLİ KAYIT** seçeneğine basın.

Varsayılan kayıt klasörü:

```text
%USERPROFILE%\Videos\EBS_Recordings
```

## 📹 Virtual Camera

`pyvirtualcam` ve uyumlu bir backend mevcutsa **Virtual Camera çıkışı** etkinleştirilebilir. Böylece telefon görüntüsü OBS Studio, Discord, Google Meet, Zoom, Microsoft Teams ve kamera seçimini destekleyen diğer programlarda kullanılabilir.

## 🚀 Sadece Virtual Camera Modu

Performans odaklı **SADECE VIRTUAL CAMERA** modunda:

- PC önizlemesi kapatılır,
- kayıt kapatılır,
- zoom kontrolü kapatılır,
- gereksiz frame kopyaları azaltılır,
- Virtual Camera otomatik etkinleştirilir.

Bu mod, görüntüyü yalnızca OBS/Meet/Zoom/Discord gibi başka bir uygulamaya aktarırken PC yükünü azaltmak için tasarlanmıştır.

## 🛠️ Sorun Giderme

### Telefon görünmüyor

```bash
C:\adb\adb.exe devices
```

Telefon `device` olarak görünmelidir. `unauthorized` görünüyorsa telefon ekranındaki ADB yetkilendirmesini kabul edin.

### FFmpeg bulunamıyor

Receiver içindeki **FFmpeg** alanına gerçek `ffmpeg.exe` yolunu girin. Örneğin:

```text
C:\ffmpeg\bin\ffmpeg.exe
```

### Görüntü gelmiyor

- Android uygulamasının açık olduğunu kontrol edin.
- Kamera iznini kontrol edin.
- ADB bağlantısını kontrol edin.
- Video portlarının eşleştiğinden emin olun.
- Wi-Fi modunda güvenlik duvarını kontrol edin.

### Virtual Camera çalışmıyor

```bash
pip install -U pyvirtualcam
```

Sisteminizde `pyvirtualcam` tarafından desteklenen bir sanal kamera backend'i bulunması gerekir.

## 🧠 Teknik Mimari

```text
Huawei / Android Telefon
        │
        │ H.264 + Control
        │ USB / Wi-Fi
        ▼
EBS Camera Receiver PRO
        │
        ├── ADB Port Forward
        ├── TCP Video Channel
        ├── TCP Control Channel
        ├── FFmpeg Decoder
        ├── NumPy / Pillow
        │
        ├────────► MP4 Recording
        │
        └────────► Virtual Camera
```

## 🔐 Güvenlik

Wi-Fi modu yerel TCP bağlantıları kullanır. Uygulamayı güvenmediğiniz veya herkese açık ağlarda kullanmamanız önerilir.

## 👨‍💻 Geliştirici

**Ebubekir Bastama**

## 📄 Lisans

Bu proje **Apache License 2.0** ile lisanslanmıştır.

Copyright © 2026 **Ebubekir Bastama**

Ayrıntılar için [`LICENSE`](LICENSE) dosyasına bakın.

---

<div align="center">

### EBS Huawei Webcam

**Telefon kameranızı güçlü ve esnek bir PC kamera kaynağına dönüştürün.**

Developed by **Ebubekir Bastama**

</div>
