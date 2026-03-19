# Haber Özetleri (SwiftUI)

Bu klasör, `UI/react` içindeki arayüzün SwiftUI ile Xcode üzerinde çalışan ikizini içerir. Arayüz; kahraman blok, görünüm seçici, kaynak paneli, haber kartları, tema değiştirici ve sonsuz kaydırma davranışlarını birebir kopyalar.

## Başlangıç

1. `UI/xcode/HaberOzetleri/HaberOzetleri.xcodeproj` dosyasını Xcode ile açın.
2. Gerekirse `Signing & Capabilities` sekmesinden kendi takımınızı seçin.
3. `.env` gerekmiyor; API adresini değiştirmek için `HaberOzetleri/Info.plist` altındaki `API_BASE_URL` değerini güncellemeniz yeterli.
4. `Run` ederek uygulamayı iPhone simülatöründe veya cihazda çalıştırabilirsiniz.

## Özellikler

- `NewsViewModel` React sürümündeki `fetchSources` ve `fetchEntries` akışını birebir uygular, görünür kartları 5'erli gruplarla artırır.
- `ViewToggle` grid/liste düzenleri arasında geçiş yapar; kartların kısıtları CSS karşılıklarıyla aynı tutulmuştur.
- `ThemeToggleButton` tercihleri `AppStorage("news-ui-theme")` üzerinden saklayarak koyu/açık tema arasında geçiş sağlar.
- `SourcePanelView` karttaki `SourceSelector` bileşenine denk gelir; aynı durum metinlerini ve durum renklerini taşır.

## Dizim

```
UI/xcode/
└── HaberOzetleri/
    ├── HaberOzetleri.xcodeproj
    ├── HaberOzetleri/
    │   ├── HaberOzetleriApp.swift
    │   ├── ContentView.swift
    │   ├── Views/
    │   │   ├── NewsCardView.swift
    │   │   ├── NewsFeedView.swift
    │   │   ├── SourcePanelView.swift
    │   │   ├── StyledBackground.swift
    │   │   └── ThemeToggleButton.swift
    │   ├── ViewModel/NewsViewModel.swift
    │   ├── Support/ThemePreference.swift
    │   ├── Info.plist
    │   └── Assets.xcassets / Preview Content
    └── README.md
```
