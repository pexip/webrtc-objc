// swift-tools-version:5.3
import PackageDescription

let package = Package(
    name: "WebRTC",
    platforms: [
    	.iOS(.v13),
        .macOS(.v10_15)
    ],
    products: [
        .library(
            name: "WebRTC",
            targets: ["WebRTC"]
        ),
    ],
    dependencies: [],
    targets: [
        .binaryTarget(
            name: "WebRTC",
            url: "https://github.com/pexip/webrtc-objc/releases/download/105.0.0/WebRTC-universal_dsyms.zip",
            checksum: "921c2bc805f04fdb22b2cc97f67e4bf33c538845d0097e620e635194dd68d9c3"
        ),
    ]
)
